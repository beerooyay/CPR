#!/usr/bin/env python3
"""Full CPR Update - Calculate and save all metrics"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cpr_engine import CPREngine
from src.firestore_saver import save_all_players_from_cpr

def main(stats_path=None, season_year=None):
    # dynamic paths and season
    if not stats_path:
        stats_path = Path(__file__).parent.parent / 'data' / 'raw' / 'current_stats.csv'
    if not season_year:
        season_year = datetime.now().year
    
    print(f"\n📊 running CPR for {season_year}...")
    engine = CPREngine(str(stats_path))
    results = engine.run()

    if not results:
        print("❌ no results from CPR engine")
        return
    
    print(f"✅ {len(results['players'])} players, {len(results['teams'])} teams")

    # display top 3 teams
    print("\n🏆 top 3:")
    for team in results['teams'][:3]:
        name = team.get('team') or team.get('team_key', '')
        print(f"{team.get('rank', 0)}. {name}: CPR={team.get('CPR', 0):.3f}")

    # save player data
    print(f"\n💾 saving to database...")
    saved = save_all_players_from_cpr({
        'players': engine.players,
        'teams': results['teams']
    }, season_year=season_year)
    print(f"✅ saved {saved} players")

    # team and league metrics saved automatically by firestore_saver
    league = results.get('league', {})
    print(f"✅ gini: {league.get('gini', 0):.3f}, lhi: {league.get('lhi', 0):.1%}")
    
    print(f"\n✨ cpr update complete!\n")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--stats', type=str, help='path to stats CSV')
    parser.add_argument('--year', type=int, default=2025, help='season year')
    args = parser.parse_args()
    main(args.stats, args.year)
