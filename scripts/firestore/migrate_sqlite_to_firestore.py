#!/usr/bin/env python3
"""
One-time migration script to move data from the local SQLite database to Firestore.
"""
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURATION ---
# Use the EXACT, ABSOLUTE paths to the files.
SERVICE_ACCOUNT_KEY_PATH = "/Users/beerooyay/Desktop/CPR/api/cpr-app-54c15-firebase-adminsdk-fbsvc-942285c749.json"
DB_PATH = "/Users/beerooyay/Desktop/CPR/data/cpr_data.db"

def migrate_data():
    """Migrates all data from SQLite to Firestore."""
    print("\n🔥 Starting SQLite to Firestore migration...")

    # Initialize Firebase Admin
    print(f"🔑 Using service account key: {SERVICE_ACCOUNT_KEY_PATH}")
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    db = firestore.client()

    # Connect to SQLite
    print(f"💾 Using database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("✅ Connected to both databases.")

    # --- MIGRATE SEASONS ---
    print("\n migrating seasons...")
    cursor.execute("SELECT * FROM seasons")
    for row in cursor.fetchall():
        season_id = f"season_{row['season_year']}"
        db.collection("seasons").document(season_id).set(dict(row))
        print(f"  ✓ {season_id}")

    # --- MIGRATE TEAMS ---
    print("\n migrating teams...")
    cursor.execute("SELECT * FROM teams")
    for row in cursor.fetchall():
        team_doc_id = row['team_name'].lower().replace(' ', '-')
        season_id = f"season_{row['season_id']}" # Assuming season_id in teams table is the year
        db.collection("seasons").document(season_id).collection("teams").document(team_doc_id).set(dict(row))
        print(f"  ✓ {team_doc_id} for {season_id}")

    # --- MIGRATE PLAYERS ---
    print("\n migrating players...")
    cursor.execute("SELECT * FROM players")
    for row in cursor.fetchall():
        player_id = str(row['player_id'])
        db.collection("players").document(player_id).set(dict(row))

    print("  ✓ Migrated all players.")

    # --- MIGRATE PLAYER STATS & METRICS ---
    print("\n migrating player stats and metrics...")
    cursor.execute("SELECT * FROM player_stats")
    for row in cursor.fetchall():
        player_id = str(row['player_id'])
        season_id = f"season_{row['season_id']}"
        db.collection("seasons").document(season_id).collection("players").document(player_id).collection("stats").document(str(row['season_id'])).set(dict(row), merge=True)

    cursor.execute("SELECT * FROM player_metrics")
    for row in cursor.fetchall():
        player_id = str(row['player_id'])
        season_id = f"season_{row['season_id']}"
        db.collection("cpr_metrics").document(season_id).collection("player_metrics").document(player_id).set(dict(row))

    print("  ✓ Migrated all player stats and metrics.")

    # --- MIGRATE TEAM METRICS ---
    print("\n migrating team metrics...")
    cursor.execute("SELECT * FROM team_metrics")
    for row in cursor.fetchall():
        team_id = str(row['team_id'])
        season_id = f"season_{row['season_id']}"
        db.collection("cpr_metrics").document(season_id).collection("team_metrics").document(team_id).set(dict(row))
    print("  ✓ Migrated all team metrics.")

    conn.close()
    print("\n\n✅ Migration complete!")

if __name__ == "__main__":
    migrate_data()
