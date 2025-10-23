#!/usr/bin/env python3
"""Master CPR Pipeline - ESPN to Firestore in one command"""
import sys
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """Set up structured logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def run_pipeline():
    """Run complete ESPN -> CPR -> Firestore pipeline with logging."""
    setup_logging()
    logging.info("🚀 CPR MASTER PIPELINE STARTING...")
    
    script_dir = Path(__file__).parent

    # Step 1: Fetch ESPN data
    logging.info("📡 STEP 1: Fetching ESPN data...")
    # Step 1: Fetch ESPN data
    logging.info("📡 STEP 1: Fetching ESPN data...")
    fetch_process = subprocess.run([
        sys.executable, str(script_dir / 'espn_league_fetcher.py'),
        '--league_id', '2058537017' # blaize's FBA league
    ])
    if fetch_process.returncode != 0:
        logging.error("❌ ESPN fetch failed. Halting pipeline.")
        return False
    logging.info("  -> ESPN fetch successful.")

    # Step 2: Run CPR calculation and save to Firestore
    logging.info("🧮 STEP 2: Running CPR calculation and saving to Firestore...")
    cpr_process = subprocess.run([
        sys.executable, str(script_dir / 'full_cpr_update.py')
    ])
    if cpr_process.returncode != 0:
        logging.error("❌ CPR calculation failed. Halting pipeline.")
        return False
    logging.info("  -> CPR calculation and save successful.")

    logging.info("✅ PIPELINE COMPLETE! Data is now in Firestore.")
    return True

if __name__ == '__main__':
    run_pipeline()
