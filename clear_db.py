import os
import psycopg2
from dotenv import load_dotenv

# Force loading from the local .env file
load_dotenv(override=True)
db_url = os.getenv("DATABASE_URL")

def clear_test_data():
    if not db_url:
        print("❌ Error: DATABASE_URL not found in .env file.")
        return

    # Tables must be cleared in reverse order of dependencies
    tables_to_clear = [
        "turnstartinghands",
        "finaldeckcomposition",
        "gameevents",
        "gamekingdomcards",
        "gameplayers",
        "games"
    ]

    try:
        print("🔌 Connecting to database to clear old game data...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Disable triggers temporarily if needed, or clear in strict constraint order
        for table in tables_to_clear:
            cursor.execute(f"DELETE FROM {table} WHERE game_id LIKE 'G-%';")
            print(f"🧹 Cleared rows matching 'G-%' from table: {table}")

        conn.commit()
        print("\n✅ Database clean! You are ready to insert the fresh, chronological game data.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Failed to clear database: {e}")

if __name__ == "__main__":
    clear_test_data()