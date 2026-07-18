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
    if player_identifier.upper().startswith("P_") or player_identifier.upper().startswith("P0"):
        return player_identifier.upper()
    
    cur.execute("SELECT player_id FROM player_aliases WHERE LOWER(alias) = LOWER(%s);", (player_identifier,))
    row = cur.fetchone()
    if row:
        return row[0]
        
    cur.execute("SELECT player_id FROM players WHERE LOWER(first_name) = LOWER(%s) LIMIT 1;", (player_identifier,))
    row = cur.fetchone()
    return row[0] if row else player_identifier

def resolve_card_id(cur, card_identifier: str) -> str:
    """Strictly resolves to a card_id existing in the cards table."""
    cur.execute("""
        SELECT card_id FROM cards 
        WHERE LOWER(card_id) = LOWER(%s) OR LOWER(name) = LOWER(%s) 
        LIMIT 1;
    """, (card_identifier, card_identifier))
    row = cur.fetchone()
    
    if not row:
        raise ValueError(f"Card '{card_identifier}' is not registered in the database.")
    
    return row[0]

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
def log_complete_turn(game_id: str, player_identifier: str, turn_number: int, 
                      starting_hand: dict[str, int], played_cards: dict[str, int], 
                      buys: dict[str, int], mid_turn_draws: list[str] = None) -> str:
    """
    Orchestrates logging an entire active turn sequence for a player.
    Logs starting hand, explicit plays, intermediate card DRAWS from actions, buys, 
    and automatically calculates unplayed cards as CLEANUP events.
    
    Strictly orders inserts: Action PLAYS -> DRAWs -> Treasure PLAYS -> BUYS -> CLEANUP.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        actual_player_id = resolve_player_id(cur, player_identifier)
        
        # 1. Log the starting hand state
        for card_name, quantity in starting_hand.items():
            actual_card_id = resolve_card_id(cur, card_name)
            cur.execute("""
                INSERT INTO turnstartinghands (game_id, player_id, turn_number, card_id, quantity) 
                VALUES (%s, %s, %s, %s, %s);
            """, (game_id, actual_player_id, turn_number, actual_card_id, quantity))

        # Core Fix: Separate treasures from explicit action input payloads
        treasures_to_ignore = {"Copper", "Silver", "Gold"}
        filtered_played_cards = {k: v for k, v in played_cards.items() if k not in treasures_to_ignore}

        # 2. FIRST: Log explicit action card plays
        for card_name, quantity in filtered_played_cards.items():
            if quantity <= 0: continue
            actual_card_id = resolve_card_id(cur, card_name)
            cur.execute("""
                INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) 
                VALUES (%s, %s, %s, 'PLAY', %s, %s);
            """, (game_id, actual_player_id, turn_number, actual_card_id, quantity))

        # 3. SECOND: Log immediate mid-turn action card DRAWS chronologically right after actions
        leftovers = starting_hand.copy()
        if mid_turn_draws:
            for card_name in mid_turn_draws:
                actual_card_id = resolve_card_id(cur, card_name)
                cur.execute("""
                    INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) 
                    VALUES (%s, %s, %s, 'DRAW', %s, %s);
                """, (game_id, actual_player_id, turn_number, actual_card_id, 1))
                
                # Add newly drawn cards into hand inventory so math tracks their subsequent play or cleanup
                if card_name in leftovers:
                    leftovers[card_name] += 1
                else:
                    leftovers[card_name] = 1

        # Deduct used action cards from hand inventory tracking
        for card_name, played_qty in filtered_played_cards.items():
            if card_name in leftovers:
                leftovers[card_name] -= played_qty

        # Math prep: Look up total purchase cost from the DB schema
        total_coins_needed = 0
        for card_name, buy_qty in buys.items():
            actual_buy_card_id = resolve_card_id(cur, card_name)
            cur.execute("SELECT cost_coin FROM cards WHERE card_id = %s;", (actual_buy_card_id,))
            cost_row = cur.fetchone()
            card_cost = cost_row['cost_coin'] if cost_row and cost_row['cost_coin'] is not None else 0
            total_coins_needed += card_cost * buy_qty

        # Math prep: Offset cost by virtual coins generated from played action cards
        virtual_coins = 0
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='cards' AND column_name='plus_coin';
        """)
        has_plus_coin = cur.fetchone() is not None

        if has_plus_coin:
            for card_name, play_qty in filtered_played_cards.items():
                if play_qty <= 0: continue
                actual_play_id = resolve_card_id(cur, card_name)
                cur.execute("SELECT plus_coin FROM cards WHERE card_id = %s;", (actual_play_id,))
                coin_row = cur.fetchone()
                if coin_row and coin_row['plus_coin']:
                    virtual_coins += coin_row['plus_coin'] * play_qty

        total_coins_needed = max(0, total_coins_needed - virtual_coins)

        # 4. THIRD: Process and log physical Treasures needed to fund the balance
        treasure_values = {"Gold": 3, "Silver": 2, "Copper": 1}
        for t_card in ["Gold", "Silver", "Copper"]:
            if total_coins_needed <= 0: break
            if t_card in leftovers and leftovers[t_card] > 0:
                val = treasure_values[t_card]
                available = leftovers[t_card]
                
                needed = (total_coins_needed + val - 1) // val
                used = min(available, needed)
                
                if used > 0:
                    actual_t_id = resolve_card_id(cur, t_card)
                    cur.execute("""
                        INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) 
                        VALUES (%s, %s, %s, 'PLAY', %s, %s);
                    """, (game_id, actual_player_id, turn_number, actual_t_id, used))
                    
                    leftovers[t_card] -= used
                    total_coins_needed -= (used * val)

        # 5. FOURTH: Log purchases (BUY)
        for card_name, quantity in buys.items():
            if quantity <= 0: continue
            actual_card_id = resolve_card_id(cur, card_name)
            cur.execute("""
                INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) 
                VALUES (%s, %s, %s, 'BUY', %s, %s);
            """, (game_id, actual_player_id, turn_number, actual_card_id, quantity))

        # 6. FIFTH: Explicitly log whatever remains untouched as CLEANUP
        for card_name, remaining_qty in leftovers.items():
            if remaining_qty > 0:
                actual_card_id = resolve_card_id(cur, card_name)
                cur.execute("""
                    INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) 
                    VALUES (%s, %s, %s, 'CLEANUP', %s, %s);
                """, (game_id, actual_player_id, turn_number, actual_card_id, remaining_qty))

        conn.commit()
        return f"Successfully logged full Turn {turn_number} for {actual_player_id}."
        
    except Exception as e:
        conn.rollback()
        return f"Failed to log complete turn: {e}"
    finally:
        cur.close()
        conn.close()

@mcp.tool()
def log_game_event(game_id: str, player_identifier: str, turn_number: int, action_type: str, card_identifier: str, quantity: int) -> str:
    """Logs an individual discrete game action (e.g. out-of-turn DISCARD events)."""
    conn = get_db_connection()
    cur = conn.cursor()
    actual_player_id = resolve_player_id(cur, player_identifier)
    try:
        actual_card_id = resolve_card_id(cur, card_identifier)
        normalized_action = action_type.strip().upper()
        
        cur.execute("INSERT INTO gameevents (game_id, player_id, turn_number, action_type, card_id, quantity) VALUES (%s, %s, %s, %s, %s, %s);", 
                    (game_id, actual_player_id, turn_number, normalized_action, actual_card_id, quantity))
        conn.commit()
        return f"Successfully logged {normalized_action} for {actual_player_id}."
    except Exception as e:
        conn.rollback()
        return f"Failed to log event: {e}"
    finally:
        cur.close()
        conn.close()

@mcp.tool()
def start_smart_game(player_names: list[str], expansion_set: str = "Base", notes: str = "") -> str:
    """Automatically starts a new game. Looks up players by alias or name, registers them if they don't exist."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT game_id FROM games WHERE game_id LIKE 'G-%%' ORDER BY CAST(SUBSTRING(game_id FROM 3) AS INTEGER) DESC LIMIT 1;")
            row = cur.fetchone()
            new_game_id = f"G-{int(row[0].split('-')[1]) + 1}" if row else "G-100"
            cur.execute("INSERT INTO games (game_id, expansion_set, notes) VALUES (%s, %s, %s);", (new_game_id, expansion_set, notes))

            for name in player_names:
                player_id = resolve_player_id(cur, name)
                if player_id == name:
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
def set_kingdom_cards(game_id: str, kingdom_cards: list[str]) -> str:
    """Logs the 10 Kingdom cards using strict card_id validation."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for card_name in kingdom_cards:
                valid_id = resolve_card_id(cur, card_name)
                cur.execute("INSERT INTO gamekingdomcards (game_id, card_id) VALUES (%s, %s);", (game_id, valid_id))
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
                actual_card_id = resolve_card_id(cur, card_name)
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

if __name__ == "__main__":
    mcp.run(transport="stdio")