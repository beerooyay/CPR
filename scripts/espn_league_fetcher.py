#!/usr/bin/env python3
"""ESPN Fantasy Basketball Data Fetcher - Streamlined"""
import argparse
import json
from datetime import datetime

try:
    from espn_api.basketball import League
except ImportError:
    print("\n espn-api not installed! Run: pip install espn-api\n")
    exit(1)

def get_league_info(league_id, year=2025):
    """fetch ESPN public league data"""
    print(f"\n🏀 connecting to ESPN league {league_id} ({year})...")
    
    try:
        # Force public access - no cookies
        league = League(league_id=league_id, year=year, espn_s2=None, swid=None)
        print(f"✅ {league.settings.name}\n")
        
        league_data = {
            'league_info': {
                'name': league.settings.name,
                'league_id': league_id,
                'season_year': year,
                'current_week': league.current_week,
                'num_teams': len(league.teams)
            },
            'teams': [],
            'players': []  # aggregate all players for CPR
        }
        
        print("📊 fetching teams...\n")
        for i, team in enumerate(league.standings(), 1):
            owner = getattr(team, 'owner', None) or (team.owners[0] if hasattr(team, 'owners') and team.owners else 'Unknown')
            team_id = team.team_name.lower().replace(' ', '_')
            
            team_info = {
                'rank': i,
                'team_name': team.team_name,
                'team_id': team_id,
                'owner': owner,
                'wins': team.wins,
                'losses': team.losses,
                'roster': []
            }

            for player in team.roster:
                # proper field mapping for CPR
                stats = player.stats.get(0, {}) if hasattr(player, 'stats') else {}
                avg_stats = stats.get('avg', {}) if isinstance(stats, dict) else {}
                
                player_data = {
                    'player_name': player.name,
                    'team': team.team_name,
                    'team_id': team_id,
                    'nba_team': player.proTeam,  # map proTeam -> nba_team
                    'player_info': f"{player.position}/{player.injuryStatus or 'HEALTHY'}",
                    'injured': player.injured,
                    'injuryStatus': player.injuryStatus,
                    # estimate stats if available
                    'PTS': avg_stats.get('PTS', player.total_points / max(player.stats[0].get('GP', 1), 1) if hasattr(player, 'stats') and player.stats else 0),
                    'REB': avg_stats.get('REB', 0),
                    'AST': avg_stats.get('AST', 0),
                    'STL': avg_stats.get('STL', 0),
                    'BLK': avg_stats.get('BLK', 0),
                    'TO': avg_stats.get('TO', 0),
                    'TPM': avg_stats.get('3PM', 0),
                    'FGM': avg_stats.get('FGM', 0),
                    'FGA': avg_stats.get('FGA', 0),
                    'FTM': avg_stats.get('FTM', 0),
                    'FTA': avg_stats.get('FTA', 0)
                }
                team_info['roster'].append(player_data)
                league_data['players'].append(player_data)

            league_data['teams'].append(team_info)
            print(f"  {i}. {team.team_name}: {team.wins}-{team.losses} ({len(team_info['roster'])} players)")
        
        return league_data
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        if "private" in str(e).lower() or "401" in str(e):
            print("⚠️  this appears to be a PRIVATE league")
            print("make sure your league is set to PUBLIC visibility")
        raise


def save_to_csv(data, output_path='data/raw/current_stats.csv'):
    """save player data to CSV for CPR engine"""
    import csv
    from pathlib import Path
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='') as f:
        if data['players']:
            writer = csv.DictWriter(f, fieldnames=data['players'][0].keys())
            writer.writeheader()
            writer.writerows(data['players'])
    print(f"\n💾 saved {len(data['players'])} players to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='fetch ESPN fantasy basketball league data')
    parser.add_argument('--league_id', type=int, required=True, help='ESPN league ID')
    parser.add_argument('--year', type=int, default=2025, help='season year')
    parser.add_argument('--output', type=str, default='data/raw/current_stats.csv', help='output CSV')
    parser.add_argument('--json', action='store_true', help='also save JSON')
    
    args = parser.parse_args()
    
    league_data = get_league_info(
        league_id=args.league_id,
        year=args.year
    )
    
    save_to_csv(league_data, args.output)
    if args.json:
        with open('espn_league_data.json', 'w') as f:
            json.dump(league_data, f, indent=2)
    
    print(f"\n✨ ready for CPR engine!\n")


if __name__ == '__main__':
    main()
