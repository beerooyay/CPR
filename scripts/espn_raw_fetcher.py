#!/usr/bin/env python3
"""Raw ESPN API fetcher - bypass broken espn-api library"""
import requests
import json
import csv
from pathlib import Path

def fetch_league_raw(league_id, year=2025):
    """Fetch league data using raw ESPN API calls"""
    print(f"\n🏀 fetching ESPN league {league_id} ({year}) via raw API...")
    
    # ESPN Fantasy API endpoint
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{year}/segments/0/leagues/{league_id}"
    
    params = {
        'view': ['mTeam', 'mRoster', 'mMatchup', 'mSettings']
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ {data.get('settings', {}).get('name', 'Unknown League')}")
        
        # Extract teams and players
        teams = []
        all_players = []
        
        for team in data.get('teams', []):
            team_name = team.get('name', f"Team {team.get('id', 'Unknown')}")
            team_id = team_name.lower().replace(' ', '_')
            
            roster = []
            for entry in team.get('roster', {}).get('entries', []):
                player = entry.get('playerPoolEntry', {}).get('player', {})
                
                # Get player stats
                stats = {}
                for stat_source in player.get('stats', []):
                    if stat_source.get('seasonId') == year:
                        stats = stat_source.get('stats', {})
                        break
                
                player_data = {
                    'player_name': player.get('fullName', 'Unknown'),
                    'team': team_name,
                    'team_id': team_id,
                    'nba_team': player.get('proTeam', ''),
                    'position': '/'.join(player.get('eligibleSlots', [])),
                    'injured': player.get('injured', False),
                    'injuryStatus': player.get('injuryStatus', 'HEALTHY'),
                    
                    # Stats (ESPN uses different IDs)
                    'PTS': stats.get('0', 0),  # Points
                    'REB': stats.get('6', 0),  # Rebounds  
                    'AST': stats.get('3', 0),  # Assists
                    'STL': stats.get('2', 0),  # Steals
                    'BLK': stats.get('1', 0),  # Blocks
                    'TO': stats.get('11', 0),  # Turnovers
                    'FGM': stats.get('13', 0), # Field Goals Made
                    'FGA': stats.get('14', 0), # Field Goals Attempted
                    'FTM': stats.get('15', 0), # Free Throws Made
                    'FTA': stats.get('16', 0), # Free Throws Attempted
                    'TPM': stats.get('17', 0), # 3-Pointers Made
                }
                
                roster.append(player_data)
                all_players.append(player_data)
            
            teams.append({
                'team_name': team_name,
                'team_id': team_id,
                'roster': roster
            })
        
        return {
            'league_info': {
                'name': data.get('settings', {}).get('name', 'Unknown League'),
                'league_id': league_id,
                'season_year': year,
                'num_teams': len(teams)
            },
            'teams': teams,
            'players': all_players
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def save_to_csv(data, output_path='data/raw/current_stats.csv'):
    """Save player data to CSV"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    if data and data['players']:
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data['players'][0].keys())
            writer.writeheader()
            writer.writerows(data['players'])
        print(f"💾 saved {len(data['players'])} players to: {output_path}")
        return True
    return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch ESPN league via raw API')
    parser.add_argument('--league_id', type=int, required=True)
    parser.add_argument('--year', type=int, default=2025)
    parser.add_argument('--output', type=str, default='data/raw/current_stats.csv')
    
    args = parser.parse_args()
    
    data = fetch_league_raw(args.league_id, args.year)
    if data:
        save_to_csv(data, args.output)
        print(f"\n✨ ready for CPR engine!")
    else:
        print(f"\n❌ failed to fetch league data")
        exit(1)
