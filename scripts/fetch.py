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
from models import LeagueInfo, Team, Player, PlayerStats, Matchup, Transaction, LeagueAnalysis

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
        logger.info(f"NFL Starting data fetch for league {self.league_id}")
        
        try:
            # Get league info
            logger.info("LIST Fetching league info...")
            league_info = self.api.get_league_info()
            
            # Get teams/rosters
            logger.info(" Fetching teams and rosters...")
            teams = self.api.get_rosters()
            
            # Get players for all rostered IDs (deduped)
            logger.info(" Fetching player data...")
            all_player_ids = []
            for team in teams:
                try:
                    all_player_ids.extend(team.roster)
                except Exception:
                    continue
            all_player_ids = list(set(all_player_ids))
            players = self.api.get_players(all_player_ids)
            
            # Get player stats
            logger.info("DATA Fetching player stats...")
            player_stats = self.api.get_player_stats(league_info.season)
            
            # Get matchups
            logger.info("️ Fetching matchups...")
            if week is None:
                week = league_info.current_week
            matchups = self.api.get_matchups(week)
            
            # Get transactions
            logger.info(" Fetching transactions...")
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
            
            logger.info("PASS Data fetch completed successfully!")
            return data
            
        except Exception as e:
            logger.error(f"FAIL Error during data fetch: {e}")
            raise
    
    async def save_to_database(self, data: dict):
        """Save fetched data to database (league, teams, players)"""
        logger.info("SAVE Saving data to database...")
        
        try:
            league_info = data.get("league_info")
            teams = data.get("teams", [])
            players_dict = data.get("players", {})
            matchups = data.get("matchups", [])
            transactions = data.get("transactions", [])

            # Database.save_league_data expects LeagueAnalysis
            analysis = LeagueAnalysis(
                league_info=league_info,
                cpr_rankings=[],
                niv_rankings=[],
                teams=teams,
                players=players_dict,
                matchups=matchups,
                transactions=transactions,
            )
            ok = self.database.save_league_data(self.league_id, analysis)
            if not ok:
                raise RuntimeError("save_league_data returned False")

            logger.info("PASS Data saved to database successfully!")
            
        except Exception as e:
            logger.error(f"FAIL Error saving to database: {e}")
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
        logger.info(f"SAVE Data saved to {args.output}")
    
    # Print summary
    print("\nDATA FETCH SUMMARY")
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
