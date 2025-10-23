"""
Database Schema Update
Adds lineup_synergy table for future Shapley value implementation
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "cpr_data.db"

def create_lineup_synergy_table():
    """
    Create lineup_synergy table to store teammate chemistry data
    
    This table will eventually store Shapley values and synergy metrics
    for players who are real-life teammates
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lineup_synergy (
        lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER,
        team_id INTEGER,
        smi_partner_1_id INTEGER,
        smi_partner_2_id INTEGER,
        minutes_together REAL,
        on_court_net_niv REAL,
        synergy_score REAL,
        FOREIGN KEY (season_id) REFERENCES seasons(season_id),
        FOREIGN KEY (team_id) REFERENCES teams(team_id),
        FOREIGN KEY (smi_partner_1_id) REFERENCES players(player_id),
        FOREIGN KEY (smi_partner_2_id) REFERENCES players(player_id)
    )
    """)
    
    conn.commit()
    conn.close()
    
    print("lineup_synergy table created successfully")

def update_player_metrics_table():
    """
    Add fantasy_points column to player_metrics table
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        ALTER TABLE player_metrics
        ADD COLUMN fantasy_points REAL
        """)
        conn.commit()
        print("Added fantasy_points column to player_metrics")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("fantasy_points column already exists")
        else:
            raise
    
    conn.close()

def verify_schema():
    """Verify all tables exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = cursor.execute("""
    SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
    """).fetchall()
    
    conn.close()
    
    print("\nCurrent database tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    return [t[0] for t in tables]

def run_all_updates():
    """Run all schema updates"""
    print("=" * 70)
    print("DATABASE SCHEMA UPDATE")
    print("=" * 70)
    
    print("\n1. Creating lineup_synergy table...")
    create_lineup_synergy_table()
    
    print("\n2. Updating player_metrics table...")
    update_player_metrics_table()
    
    print("\n3. Verifying schema...")
    tables = verify_schema()
    
    required_tables = ['lineup_synergy', 'league_scoring', 'player_metrics']
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        print(f"\nWARNING: Missing tables: {missing}")
    else:
        print("\nAll required tables present")
    
    print("\n" + "=" * 70)
    print("SCHEMA UPDATE COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_all_updates()
