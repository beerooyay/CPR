#!/usr/bin/env python3
"""
Daily NBA Stats Update
Fetches latest stats from Sportradar and updates database
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sportradar_fetcher import fetch_daily_stats, SportradarAPI
from db_utils import save_player_metrics

def main():
 print("=" * 70)
 print("CPR v2.0 - Daily Stats Update")
 print(f"Date: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")
 print("=" * 70)
 
 # Fetch daily stats from Sportradar
 output_path = Path(__file__).parent.parent / "data" / "raw" / f"daily_stats_{datetime.now().strftime('%Y%m%d')}.json"
 
 player_stats = fetch_daily_stats(output_path)
 
 if not player_stats:
 print("\n No stats fetched (no games today or API error)")
 return
 
 print(f"\n Fetched stats for {len(player_stats)} players")
 
 # TODO: Update database with new stats
 # For now, just save to file
 
 print("\n" + "=" * 70)
 print(" Daily update complete")
 print("=" * 70)

if __name__ == "__main__":
 main()
