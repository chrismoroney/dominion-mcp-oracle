import os
import psycopg2
from dotenv import load_dotenv

# Load your DATABASE_URL from the .env file
load_dotenv(override=True)
db_url = os.getenv("DATABASE_URL")

def test_connection():
    if not db_url:
        print("❌ Error: DATABASE_URL not found in .env file.")
        return

    try:
        print("🔌 Connecting to the Dominion Oracle...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Explicitly using the lowercase table names we found!
        cursor.execute("""
            SELECT g.game_id, p.first_name, g.winning_score 
            FROM games g
            JOIN players p ON g.winner_id = p.player_id
            WHERE g.game_id = 'G-001';
        """)
        
        result = cursor.fetchone()
        
        if result:
            print("✅ Connection Successful!")
            print(f"🏆 Query Result: The winner of Game {result[0][4]} was {result[1]} with {result[2]} VP.")
        else:
            print("⚠️ Connected, but Game G-001 wasn't found in the database.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()