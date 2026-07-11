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

# ==========================================
# READ TOOLS (Analytics)
# ==========================================

@mcp.tool()
def get_player_stats(player_id: str) -> str:
    """Retrieves the win/loss record and average score for a specific player."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT 
            COUNT(*) as games_played,
            COUNT(CASE WHEN placement = 1 THEN 1 END) as wins,
            AVG(score) as avg_score
        FROM GamePlayers
        WHERE player_id = %s;
    """
    
    cur.execute(query, (player_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row or row['games_played'] == 0:
        return f"No data found for player {player_id}."
        
    win_rate = (row['wins'] / row['games_played']) * 100
    return (f"Player {player_id} Stats:\n"
            f"- Games Played: {row['games_played']}\n"
            f"- Wins: {row['wins']} ({win_rate:.1f}% Win Rate)\n"
            f"- Avg Score: {row['avg_score']:.1f} VP")

@mcp.tool()
def get_turn_log(game_id: str, turn_number: int) -> str:
    """Retrieves the exact sequence of events for all players on a specific turn."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT player_id, action_type, card_id, quantity
        FROM GameEvents
        WHERE game_id = %s AND turn_number = %s;
    """
    
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
# WRITE TOOLS (Data Entry)
# ==========================================

@mcp.tool()
def create_new_game(game_id: str, expansion_set: str, notes: str) -> str:
    """Creates a new game record in the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = "INSERT INTO Games (game_id, expansion_set, notes) VALUES (%s, %s, %s);"
    
    try:
        cur.execute(query, (game_id, expansion_set, notes))
        conn.commit()
        return f"Successfully created game {game_id}."
    except Exception as e:
        conn.rollback()
        return f"Failed to create game: {e}"
    finally:
        cur.close()
        conn.close()

@mcp.tool()
def log_game_event(game_id: str, player_id: str, turn_number: int, action_type: str, card_id: str, quantity: int) -> str:
    """Logs a specific action (PLAY, BUY, CLEANUP, etc.) to the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        INSERT INTO GameEvents (game_id, player_id, turn_number, action_type, card_id, quantity) 
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    
    try:
        cur.execute(query, (game_id, player_id, turn_number, action_type, card_id, quantity))
        conn.commit()
        return f"Successfully logged: Player {player_id} did {action_type} on Turn {turn_number}."
    except Exception as e:
        conn.rollback()
        return f"Failed to log event: {e}"
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    mcp.run(transport="stdio")