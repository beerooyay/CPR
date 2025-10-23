#!/usr/bin/env python3
"""
Import ESPN Fantasy League Data into CPR Database
"""
import json
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.db_utils import get_db_path

def import_espn_data(json_path='fba_league_data.json', season_id=1):
    """Import ESPN league data into database"""

    print(f"\n🏀 Importing ESPN data from {json_path}...\n")

    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)

    league_info = data['league_info']
    teams_data = data['teams']

    print(f"📊 League: {league_info['name']}")
    print(f"📅 Season: {league_info['season']}")
    print(f"🏆 Teams: {len(teams_data)}\n")

    # Connect to database
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Clear existing data for this season
    print("🗑️  Clearing old data...")
    cursor.execute("DELETE FROM rosters WHERE season_id = ?", (season_id,))
    cursor.execute("DELETE FROM player_stats WHERE season_id = ?", (season_id,))

    # Import each team
    for team in teams_data:
        team_name = team['team_name'].upper()
        print(f"\n  → {team_name} ({len(team['roster'])} players)")

        for player_data in team['roster']:
            player_name = player_data['name']
            position = player_data['position']
            pro_team = player_data['proTeam']
            injured = player_data['injured']
            injury_status = player_data['injuryStatus']
            total_points = player_data.get('total_points', 0)

            # Insert/update player (player_id is auto-increment)
            cursor.execute("""
                INSERT OR IGNORE INTO players (player_name, nba_team, position)
                VALUES (?, ?, ?)
            """, (player_name, pro_team, position))

            # Get player_id
            cursor.execute("SELECT player_id FROM players WHERE player_name = ?", (player_name,))
            player_id = cursor.fetchone()[0]

            # Insert player_stats with placeholder stats (ESPN doesn't provide detailed stats in this API)
            cursor.execute("""
                INSERT OR REPLACE INTO player_stats (
                    player_id, player_name, season_id, team, position,
                    pts, reb, ast, stl, blk, tov, fg_pct, ft_pct, fg3m,
                    games_played
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id, player_name, season_id, team_name, position,
                total_points / 10 if total_points else 0,  # Rough estimate
                0, 0, 0, 0, 0, 0.45, 0.75, 0, 1
            ))

            # Insert into rosters table
            cursor.execute("""
                INSERT OR REPLACE INTO rosters (
                    team_id, player_id, season_id, position, is_starter
                ) VALUES (?, ?, ?, ?, ?)
            """, (team_name.lower().replace(' ', '_'), player_id, season_id, position, 1))

            # Insert player_health
            health_factor = 1.0 if injury_status == 'ACTIVE' else (0.85 if 'DAY_TO_DAY' in injury_status else 0.5)
            cursor.execute("""
                INSERT OR REPLACE INTO player_health (
                    player_id, season_id, injury_status, availability_factor
                ) VALUES (?, ?, ?, ?)
            """, (player_id, season_id, injury_status, health_factor))

            print(f"    ✓ {player_name} ({position}, {pro_team}) - {injury_status}")

    conn.commit()
    conn.close()

    print(f"\n✅ Import complete! {len(teams_data)} teams imported.\n")
    print("🔄 Next step: Run CPR calculations with:")
    print("   python3 scripts/run_cpr.py\n")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import ESPN fantasy data into CPR database')
    parser.add_argument('--json', type=str, default='fba_league_data.json', help='JSON file path')
    parser.add_argument('--season', type=int, default=1, help='Season ID')

    args = parser.parse_args()
    import_espn_data(args.json, args.season)
