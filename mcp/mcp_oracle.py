from fastmcp import FastMCP
import psycopg2
from psycopg2.extras import DictCursor
import os

# Initialize FastMCP Server
mcp = FastMCP("Dominion Oracle")

# Securely grab your Neon connection string from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

def resolve_player_id(cur, player_identifier: str) -> str:
    """Helper to resolve identifiers (Name, Alias, or ID) using the player_aliases table."""
    # 1. Check for explicit IDs
    if player_identifier.upper().startswith("P_") or player_identifier.upper().startswith("P0"):
        return player_identifier.upper()
    
    # 2. Check the alias table first
    cur.execute("SELECT player_id FROM player_aliases WHERE LOWER(alias) = LOWER(%s);", (player_identifier,))
    row = cur.fetchone()
    if row:
        return row[0]
        
    # 3. Fallback to first_name
    cur.execute("SELECT player_id FROM players WHERE LOWER(first_name) = LOWER(%s) LIMIT 1;", (player_identifier,))
    row = cur.fetchone()
    return row[0] if row else player_identifier

# ==========================================
# READ TOOLS (Analytics)
# ==========================================

@mcp.tool()
def get_player_stats(player_identifier: str) -> str:
    """Retrieves win/loss record for a specific player (can use name, alias, or ID)."""
    conn = get_db_connection()
    cur = conn.cursor()
    actual_player_id = resolve_player_id(cur, player_identifier)
    
    query = "SELECT COUNT(*) as games_played, COUNT(CASE WHEN placement = 1 THEN 1 END) as wins, AVG(score) as avg_score FROM gameplayers WHERE player_id = %s;"
    cur.execute(query, (actual_player_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row or row['games_played'] == 0:
        return f"No data found for player {actual_player_id}."
        
    win_rate = (row['wins'] / row['games_played']) * 100
    return f"Player {actual_player_id} Stats:\n- Games Played: {row['games_played']}\n- Wins: {row['wins']} ({win_rate:.1f}% Win Rate)\n- Avg Score: {row['avg_score']:.1f} VP"

@mcp.tool()
def get_turn_log(game_id: str, turn_number: int) -> str:
    """Retrieves the exact sequence of events for all players on a specific turn."""
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT player_id, action_type, card_id, quantity FROM gameevents WHERE game_id = %s AND turn_number = %s;"
    cur.execute(query, (game_id, turn_number))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        return f"No events found for {game_id} on Turn {turn_number}."
        
    log_output = f"--- Activity for {game_id}, Turn {turn_number} ---\n"
    current_player = None
    for row in rows:
        if row['player_id'] != current_player:
            current_player = row['player_id']
            log_output += f"\nPlayer {current_player}:\n"
        card_name = row['card_id'] if row['card_id'] else "Nothing"
        log_output += f"  - {row['action_type']}: {row['quantity']}x {card_name}\n"
    return log_output

# ==========================================
# WRITE TOOLS (Data Entry & Setup)
# ==========================================

@mcp.tool()
def start_smart_game(player_names: list[str], expansion_set: str = "Base", notes: str = "") -> str:
    """Automatically starts a new game. Looks up players by alias or name, registers them if they don't exist."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Get next Game ID
            cur.execute("SELECT game_id FROM games WHERE game_id LIKE 'G-%%' ORDER BY CAST(SUBSTRING(game_id FROM 3) AS INTEGER) DESC LIMIT 1;")
            row = cur.fetchone()
            new_game_id = f"G-{int(row[0].split('-')[1]) + 1}" if row else "G-100"

            # 2. Create Game
            cur.execute("INSERT INTO games (game_id, expansion_set, notes) VALUES (%s, %s, %s);", (new_game_id, expansion_set, notes))

            # 3. Resolve Players
            for name in player_names:
                player_id = resolve_player_id(cur, name)
                if player_id == name: # If not resolved, create new
                    player_id = f"P_{name.upper().replace(' ', '_')}"
                    cur.execute("INSERT INTO players (player_id, first_name) VALUES (%s, %s);", (player_id, name))
                
                cur.execute("INSERT INTO gameplayers (game_id, player_id) VALUES (%s, %s);", (new_game_id, player_id))
        conn.commit()
        return f"Successfully started game {new_game_id}."
    except Exception as e:
        return f"Error: {e}"
    finally:
        if conn: conn.close()

@mcp.tool()
def log_game_event(game_id: str, player_identifier: str, turn_number: int, action_type: str, card_identifier: str, quantity: int) -> str:
    """Logs a specific action to the database using the card resolver."""
    conn = get_db_connection()
    cur = conn.cursor()
    actual_player_id = resolve_player_id(cur, player_identifier)
    actual_card_id = resolve_card_id(cur, card_identifier) # Added resolver
    try:
        cur.execute("INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) VALUES (%s, %s, %s, %s, %s, %s);", 
                    (game_id, actual_player_id, turn_number, action_type, actual_card_id, quantity))
        conn.commit()
        return f"Successfully logged action for {actual_player_id}."
    finally:
        cur.close()
        conn.close()

@mcp.tool()
def set_kingdom_cards(game_id: str, kingdom_cards: list[str]) -> str:
    """Logs the 10 Kingdom cards using strict card_id validation."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for card_name in kingdom_cards:
                # This will now throw an error if the card isn't registered
                valid_id = resolve_card_id(cur, card_name)
                cur.execute("""
                    INSERT INTO gamekingdomcards (game_id, card_id) 
                    VALUES (%s, %s);
                """, (game_id, valid_id))
        conn.commit()
        return f"Successfully logged {len(kingdom_cards)} kingdom cards for {game_id}."
    except Exception as e:
        return f"Error: {e}"
    finally:
        if conn: conn.close()

@mcp.tool()
def log_starting_hand(game_id: str, player_identifier: str, turn_number: int, hand: dict) -> str:
    """Logs the hand using the card resolver for every card in the dict."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            actual_player_id = resolve_player_id(cur, player_identifier)
            for card_name, quantity in hand.items():
                actual_card_id = resolve_card_id(cur, card_name) # Added resolver
                cur.execute("INSERT INTO turnstartinghands (game_id, player_id, turn_number, card_id, quantity) VALUES (%s, %s, %s, %s, %s);", 
                            (game_id, actual_player_id, turn_number, actual_card_id, quantity))
        conn.commit()
        return f"Successfully logged starting hand for {actual_player_id}."
    finally:
        conn.close()

@mcp.tool()
def register_cards(card_names: list[str], expansion_set: str) -> str:
    """Registers new cards into the master cards table."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for name in card_names:
                cur.execute("INSERT INTO cards (card_id, name, expansion) VALUES (%s, %s, %s) ON CONFLICT (card_id) DO NOTHING;", (name, name, expansion_set))
        conn.commit()
        return f"Successfully registered {len(card_names)} cards."
    except Exception as e:
        return f"Error: {e}"
    finally:
        if conn: conn.close()

def resolve_card_id(cur, card_identifier: str) -> str:
    """Strictly resolves to a card_id existing in the cards table."""
    cur.execute("""
        SELECT card_id FROM cards 
        WHERE LOWER(card_id) = LOWER(%s) OR LOWER(name) = LOWER(%s) 
        LIMIT 1;
    """, (card_identifier, card_identifier))
    row = cur.fetchone()
    
    if not row:
        # Instead of returning the raw identifier, raise an error 
        # so the MCP tool halts before corrupting the database.
        raise ValueError(f"Card '{card_identifier}' is not registered in the database.")
    
    return row[0]
if __name__ == "__main__":
    mcp.run(transport="stdio")