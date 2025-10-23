#!/usr/bin/env python3
"""Full CPR Update - Calculate and save all metrics"""
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cpr_engine import CPREngine
from src.firestore_saver import save_player_data, save_cpr_data, save_league_metrics

def setup_logging():
    """Set up structured logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main(stats_path=None, season_year=None):
    setup_logging()

    if not stats_path:
        stats_path = Path(__file__).parent.parent / 'data' / 'raw' / 'current_stats.csv'
    if not season_year:
        season_year = datetime.now().year
    
    logging.info(f"📊 Running CPR calculations for {season_year} using data from {stats_path}...")
    
    try:
        engine = CPREngine(str(stats_path))
        results = engine.run()
        logging.info("  -> CPR engine calculations complete.")
    except Exception as e:
        logging.error(f"❌ CPR engine failed during execution: {e}")
        raise

    if not results or 'players' not in results or 'cpr_rankings' not in results or 'league_metrics' not in results:
        logging.error("❌ CPR engine did not return the expected data structure. Halting.")
        return

    logging.info(f"  -> Engine produced data for {len(results['players'])} players and {len(results['cpr_rankings'])} teams.")

    logging.info("🔥 Saving all results to Firestore...")
    try:
        save_player_data(results['players'], season=season_year)
        save_cpr_data(results['cpr_rankings'], season=season_year)
        save_league_metrics(results['league_metrics'], season=season_year)
        logging.info("  -> All data successfully saved to Firestore.")
    except Exception as e:
        logging.error(f"❌ Firestore save failed: {e}")
        raise

    logging.info("✅ CPR update complete!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the full CPR update and save to Firestore.')
    parser.add_argument('--stats', type=str, help='Path to the stats CSV file.')
    parser.add_argument('--year', type=int, default=datetime.now().year, help='The season year to process.')
    args = parser.parse_args()
    main(stats_path=args.stats, season_year=args.year)
