#!/usr/bin/env python3
"""ESPN Fantasy Basketball Data Fetcher - Streamlined"""
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
import os

try:
    from espn_api.basketball import League
except ImportError:
    print("\n espn-api not installed! Run: pip install espn-api\n")
    exit(1)

def get_league_data(league_id, year=2025):
    """Fetch and structure all data for a given ESPN league."""
    print(f"\n🏀 Connecting to ESPN league {league_id} ({year})...")

    # Fetch secrets from environment variables for secure authentication
    espn_s2 = os.environ.get('ESPN_S2')
    swid = os.environ.get('SWID')

    if not espn_s2 or not swid:
        print("\n⚠️  WARNING: ESPN_S2 and SWID environment variables not set.")
        print("   Attempting to connect as a public league. This may fail for private leagues.")

    try:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    except AttributeError as e:
        if "'NoneType' object has no attribute 'get'" in str(e):
            print("\n❌ CRITICAL ERROR: The ESPN league is likely set to private.")
            print("   The automated pipeline requires the league to be public.")
            print("   Please change your league's visibility to public in the ESPN settings.")
            return None
        else:
            # Re-raise other unexpected AttributeErrors
            raise e
    except Exception as e:
        print(f"\n❌ An unexpected error occurred while trying to connect to the league: {e}")
        return None

    if not league:
        return None

    print("📊 Fetching teams and players...\n")
    all_players = []
    for team in league.teams:
        for player in team.roster:
            stats = player.stats.get('0', {}).get('avg', {}) if player.stats.get('0') else {}
            player_data = {
                'player_name': player.name,
                'team': team.team_name,
                'nba_team': player.proTeam,
                'player_info': f"{player.position}/{player.injuryStatus or 'HEALTHY'}",
                'salary': player.total_salary if hasattr(player, 'total_salary') else 0,
                'PTS': stats.get('PTS', 0),
                'REB': stats.get('REB', 0),
                'AST': stats.get('AST', 0),
                'STL': stats.get('STL', 0),
                'BLK': stats.get('BLK', 0),
                'TO': stats.get('TO', 0),
                'TPM': stats.get('3PM', 0),
                'FGM': stats.get('FGM', 0),
                'FGA': stats.get('FGA', 0),
                'FTM': stats.get('FTM', 0),
                'FTA': stats.get('FTA', 0),
            }
            all_players.append(player_data)
    
    print(f"  -> Found {len(league.teams)} teams and {len(all_players)} players.")
    return all_players

def save_to_csv(players, output_path='data/raw/current_stats.csv'):
    """Save player data to CSV for the CPR engine."""
    if not players:
        print("No player data to save.")
        return

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=players[0].keys())
        writer.writeheader()
        writer.writerows(players)
    print(f"\n💾 Saved {len(players)} players to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Fetch ESPN fantasy basketball league data.')
    parser.add_argument('--league_id', type=str, required=True, help='ESPN league ID.')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='Season year.')
    parser.add_argument('--output', type=str, default='data/raw/current_stats.csv', help='Output CSV file path.')
    args = parser.parse_args()

    player_data = get_league_data(league_id=args.league_id, year=args.year)

    if player_data:
        save_to_csv(player_data, args.output)
        print("\n✨ Fetch complete! Ready for CPR engine.\n")
    else:
        print("\n❌ Fetch failed. No data to save.")
        exit(1)

if __name__ == '__main__':
    main()
