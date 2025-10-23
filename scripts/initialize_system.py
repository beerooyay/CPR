"""
System Initialization Script
Runs all three commands to complete CPR v2.0 setup
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scoring_system import initialize_scoring_system
from db_schema_update import run_all_updates

def main():
    print("=" * 70)
    print("CPR v2.0 - SYSTEM INITIALIZATION")
    print("=" * 70)
    
    print("\n" + "=" * 70)
    print("COMMAND 1: SCORING SYSTEM ACTIVATION")
    print("=" * 70)
    initialize_scoring_system()
    
    print("\n" + "=" * 70)
    print("COMMAND 3: DATABASE SCHEMA UPDATE")
    print("=" * 70)
    run_all_updates()
    
    print("\n" + "=" * 70)
    print("INITIALIZATION COMPLETE")
    print("=" * 70)
    
    print("\nNext steps:")
    print("  1. Run historical data harvest:")
    print("     python src/historical_fetcher.py --all")
    print("")
    print("  2. This will:")
    print("     - Fetch 5 years of NBA data (2020-2025)")
    print("     - Calculate CPR for each season")
    print("     - Save to database with fantasy points")
    print("")
    print("  3. Query historical data:")
    print("     python src/db_saver.py")

if __name__ == "__main__":
    main()
