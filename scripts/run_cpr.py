#!/usr/bin/env python3
"""
Run CPR v2.0 calculation
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cpr_engine import CPREngine
from db_utils import save_team_metrics, save_league_metrics
from db_saver import save_all_players_from_cpr

def main():
    parser = argparse.ArgumentParser(description="Run CPR v2.0 calculation")
    parser.add_argument("--stats", default="../data/raw/current_stats.csv", help="Path to stats CSV")
    parser.add_argument("--save-to-db", action="store_true", help="Save results to database")
    parser.add_argument("--season", type=int, default=2025, help="Season year")
    parser.add_argument("--week", type=int, help="Week number (optional)")
    args = parser.parse_args()
    
    print("=" * 70)
    print("CPR v2.0 - Commissioner's Power Rankings")
    print("=" * 70)
    
    # Run CPR
    engine = CPREngine(args.stats)
    results = engine.run()
    
    # Print results
    print("\nRANKINGS:")
    print("-" * 70)
    for team in results["teams"]:
        print(f"{team['rank']:2d}. {team['team']:<30} CPR: {team['CPR']:>7.3f}")
    
    print("\nLEAGUE METRICS:")
    print("-" * 70)
    print(f"Gini Coefficient: {results['league']['gini']:.3f}")
    print(f"League Health Index: {results['league']['lhi']:.3f}")
    
    # Save to database if requested
    if args.save_to_db:
        print("\nSaving to database...")
        
        # Save ALL PLAYER DATA (raw stats + calculated metrics)
        try:
            save_all_players_from_cpr(results, args.season)
        except Exception as e:
            print(f"Warning: Could not save player data: {e}")
        
        # Save team metrics
        for team in results["teams"]:
            try:
                save_team_metrics(
                    team['team'],
                    args.season,
                    team,
                    week=args.week,
                    model_version="CPR v2.0"
                )
            except Exception as e:
                print(f"Warning: Could not save {team['team']}: {e}")
        
        # Save league metrics
        try:
            save_league_metrics(
                args.season,
                results['league'],
                week=args.week,
                model_version="CPR v2.0"
            )
        except Exception as e:
            print(f"Warning: Could not save league metrics: {e}")
        
        print("Saved to database")
    
    print("\n" + "=" * 70)
    print("CPR calculation complete")
    print("=" * 70)

if __name__ == "__main__":
    main()
