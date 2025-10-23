#!/usr/bin/env python3
"""Master CPR Pipeline - ESPN to Firestore in one command"""
import sys
import subprocess
from pathlib import Path

def run_pipeline():
    """Run complete ESPN -> CPR -> Firestore pipeline"""
    print("🚀 CPR MASTER PIPELINE")
    print("=" * 50)
    
    # Step 1: Fetch ESPN data
    print("\n📡 Step 1: Fetching ESPN data...")
    result = subprocess.run([
        sys.executable, 'scripts/espn_league_fetcher.py', 
        '--league_id', '2058537017'  # blaize's FBA league
    ], cwd=Path(__file__).parent)
    
    if result.returncode != 0:
        print("❌ ESPN fetch failed")
        return False
    
    # Step 2: Run CPR calculation and save to Firestore
    print("\n🧮 Step 2: Running CPR calculation...")
    result = subprocess.run([
        sys.executable, 'scripts/full_cpr_update.py'
    ], cwd=Path(__file__).parent)
    
    if result.returncode != 0:
        print("❌ CPR calculation failed")
        return False
    
    print("\n✅ Pipeline complete! Data is now in Firestore.")
    print("\n🌐 Start web server:")
    print("   python api/firestore_server.py")
    print("\n📱 Open web app:")
    print("   open web/index.html")
    
    return True

if __name__ == '__main__':
    run_pipeline()
