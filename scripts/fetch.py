#!/usr/bin/env python3
"""Data fetching script for CPR-NFL system"""
import sys
import os
from pathlib import Path
import asyncio
import logging
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api import SleeperAPI
from database import Database
from models import LeagueInfo, Team, Player, PlayerStats, Matchup, Transaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataFetcher:
    """Data fetching coordinator"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.api = SleeperAPI(league_id)
        self.database = Database()
        
    async def fetch_all_data(self, week: int = None) -> dict:
        """Fetch all data for the league"""
        logger.info(f"🏈 Starting data fetch for league {self.league_id}")
        
        try:
            # Get league info
            logger.info("📋 Fetching league info...")
            league_info = self.api.get_league_info()
            
            # Get teams/rosters
            logger.info("👥 Fetching teams and rosters...")
            teams = self.api.get_rosters()
            
            # Get players
            logger.info("🏃 Fetching player data...")
            players = self.api.get_players()
            
            # Get player stats
            logger.info("📊 Fetching player stats...")
            player_stats = self.api.get_player_stats(league_info.season)
            
            # Get matchups
            logger.info("⚔️ Fetching matchups...")
            if week is None:
                week = league_info.current_week
            matchups = self.api.get_matchups(week)
            
            # Get transactions
            logger.info("💰 Fetching transactions...")
            transactions = self.api.get_transactions(week)
            
            data = {
                "league_info": league_info,
                "teams": teams,
                "players": players,
                "player_stats": player_stats,
                "matchups": matchups,
                "transactions": transactions,
                "fetched_at": datetime.now().isoformat()
            }
            
            logger.info("✅ Data fetch completed successfully!")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error during data fetch: {e}")
            raise
    
    async def save_to_database(self, data: dict):
        """Save fetched data to database"""
        logger.info("💾 Saving data to database...")
        
        try:
            # Save league info
            if "league_info" in data:
                self.database.save_league_info(data["league_info"])
            
            # Save teams
            if "teams" in data:
                self.database.save_teams(data["teams"])
            
            # Save players
            if "players" in data:
                self.database.save_players(data["players"])
            
            # Save player stats
            if "player_stats" in data:
                self.database.save_player_stats(data["player_stats"])
            
            # Save matchups
            if "matchups" in data:
                self.database.save_matchups(data["matchups"])
            
            # Save transactions
            if "transactions" in data:
                self.database.save_transactions(data["transactions"])
            
            logger.info("✅ Data saved to database successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error saving to database: {e}")
            raise
    
    async def fetch_and_save(self, week: int = None):
        """Fetch data and save to database"""
        data = await self.fetch_all_data(week)
        await self.save_to_database(data)
        return data

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch CPR-NFL data")
    parser.add_argument("--league-id", default="1267325171853701120", 
                       help="League ID to fetch data for")
    parser.add_argument("--week", type=int, help="Specific week to fetch")
    parser.add_argument("--save", action="store_true", 
                       help="Save data to database")
    parser.add_argument("--output", help="Output file for JSON data")
    
    args = parser.parse_args()
    
    # Initialize fetcher
    fetcher = DataFetcher(args.league_id)
    
    # Fetch data
    data = await fetcher.fetch_all_data(args.week)
    
    # Save to database if requested
    if args.save:
        await fetcher.save_to_database(data)
    
    # Save to file if requested
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"💾 Data saved to {args.output}")
    
    # Print summary
    print("\n📊 FETCH SUMMARY")
    print("=" * 40)
    print(f"League: {data['league_info'].name}")
    print(f"Season: {data['league_info'].season}")
    print(f"Current Week: {data['league_info'].current_week}")
    print(f"Teams: {len(data['teams'])}")
    print(f"Players: {len(data['players'])}")
    print(f"Player Stats: {len(data['player_stats'])}")
    print(f"Matchups: {len(data['matchups'])}")
    print(f"Transactions: {len(data['transactions'])}")
    print(f"Fetched At: {data['fetched_at']}")

if __name__ == "__main__":
    asyncio.run(main())
