#!/usr/bin/env python3
"""Calculation script for CPR-NFL system"""
import sys
import os
from pathlib import Path
import asyncio
import logging
from datetime import datetime
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api import SleeperAPI
from database import Database
from cpr import CPREngine
from niv import NIVCalculator
from models import LeagueInfo, Team, Player, PlayerStats, CPRMetrics, NIVMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CalculationEngine:
    """Calculation coordinator for CPR and NIV"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.api = SleeperAPI(league_id)
        self.database = Database()
        self.cpr_engine = CPREngine()
        self.niv_calculator = NIVCalculator()
        
    async def calculate_cpr_rankings(self, week: int = None) -> list[CPRMetrics]:
        """Calculate CPR rankings for all teams"""
        logger.info("🏆 Calculating CPR rankings...")
        
        try:
            # Get league data
            league_info = self.api.get_league_info()
            teams = self.api.get_rosters()
            players = self.api.get_players()
            player_stats = self.api.get_player_stats(league_info.season)
            
            # Calculate CPR for each team
            cpr_rankings = []
            
            for team in teams:
                logger.info(f"📊 Calculating CPR for {team.team_name}...")
                
                # Get team roster players
                roster_players = []
                for player_id in team.roster:
                    if player_id in players:
                        player = players[player_id]
                        # Add player stats
                        player_stats_data = player_stats.get(player_id, {})
                        player.stats = player_stats_data
                        roster_players.append(player)
                
                # Calculate CPR metrics
                cpr_metrics = self.cpr_engine.calculate_team_cpr(
                    team, roster_players, league_info
                )
                cpr_rankings.append(cpr_metrics)
            
            # Sort by CPR score
            cpr_rankings.sort(key=lambda x: x.cpr, reverse=True)
            
            # Assign ranks
            for i, metrics in enumerate(cpr_rankings, 1):
                metrics.rank = i
            
            logger.info(f"✅ CPR rankings calculated for {len(cpr_rankings)} teams")
            return cpr_rankings
            
        except Exception as e:
            logger.error(f"❌ Error calculating CPR rankings: {e}")
            raise
    
    async def calculate_niv_rankings(self, week: int = None) -> list[NIVMetrics]:
        """Calculate NIV rankings for all players"""
        logger.info("🎯 Calculating NIV rankings...")
        
        try:
            # Get league data
            league_info = self.api.get_league_info()
            teams = self.api.get_rosters()
            players = self.api.get_players()
            player_stats = self.api.get_player_stats(league_info.season)
            
            # Calculate NIV for each player
            niv_rankings = []
            
            for player_id, player in players.items():
                # Only calculate for relevant players (on rosters)
                is_relevant = any(player_id in team.roster for team in teams)
                if not is_relevant:
                    continue
                
                try:
                    logger.info(f"📊 Calculating NIV for {player.name}...")
                    
                    # Get player stats
                    stats = player_stats.get(player_id)
                    if not stats:
                        continue
                    
                    # Calculate NIV metrics
                    niv_metrics = self.niv_calculator.calculate_player_niv(
                        player, {"current": stats}, {}
                    )
                    niv_rankings.append(niv_metrics)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not calculate NIV for {player.name}: {e}")
                    continue
            
            # Sort by NIV score
            niv_rankings.sort(key=lambda x: x.niv, reverse=True)
            
            # Assign ranks
            for i, metrics in enumerate(niv_rankings, 1):
                metrics.rank = i
            
            logger.info(f"✅ NIV rankings calculated for {len(niv_rankings)} players")
            return niv_rankings
            
        except Exception as e:
            logger.error(f"❌ Error calculating NIV rankings: {e}")
            raise
    
    async def calculate_all_metrics(self, week: int = None) -> dict:
        """Calculate both CPR and NIV metrics"""
        logger.info("🚀 Starting full calculation...")
        
        # Calculate CPR rankings
        cpr_rankings = await self.calculate_cpr_rankings(week)
        
        # Calculate NIV rankings
        niv_rankings = await self.calculate_niv_rankings(week)
        
        results = {
            "cpr_rankings": cpr_rankings,
            "niv_rankings": niv_rankings,
            "calculated_at": datetime.now().isoformat(),
            "week": week or "current"
        }
        
        logger.info("✅ All calculations completed!")
        return results
    
    async def save_to_database(self, results: dict):
        """Save calculation results to database"""
        logger.info("💾 Saving calculations to database...")
        
        try:
            # Save CPR rankings
            if "cpr_rankings" in results:
                self.database.save_cpr_rankings(
                    self.league_id, 
                    results["week"], 
                    results["cpr_rankings"]
                )
            
            # Save NIV rankings
            if "niv_rankings" in results:
                self.database.save_niv_data(
                    self.league_id,
                    results["week"],
                    results["niv_rankings"]
                )
            
            logger.info("✅ Calculations saved to database!")
            
        except Exception as e:
            logger.error(f"❌ Error saving calculations: {e}")
            raise

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculate CPR-NFL metrics")
    parser.add_argument("--league-id", default="1267325171853701120", 
                       help="League ID to calculate for")
    parser.add_argument("--week", type=int, help="Specific week to calculate")
    parser.add_argument("--cpr-only", action="store_true", 
                       help="Only calculate CPR rankings")
    parser.add_argument("--niv-only", action="store_true", 
                       help="Only calculate NIV rankings")
    parser.add_argument("--save", action="store_true", 
                       help="Save results to database")
    parser.add_argument("--output", help="Output file for JSON results")
    
    args = parser.parse_args()
    
    # Initialize calculator
    calculator = CalculationEngine(args.league_id)
    
    # Calculate based on options
    if args.cpr_only:
        results = {
            "cpr_rankings": await calculator.calculate_cpr_rankings(args.week),
            "calculated_at": datetime.now().isoformat(),
            "week": args.week or "current"
        }
    elif args.niv_only:
        results = {
            "niv_rankings": await calculator.calculate_niv_rankings(args.week),
            "calculated_at": datetime.now().isoformat(),
            "week": args.week or "current"
        }
    else:
        results = await calculator.calculate_all_metrics(args.week)
    
    # Save to database if requested
    if args.save:
        await calculator.save_to_database(results)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"💾 Results saved to {args.output}")
    
    # Print summary
    print("\n📊 CALCULATION SUMMARY")
    print("=" * 40)
    print(f"Week: {results['week']}")
    print(f"Calculated At: {results['calculated_at']}")
    
    if "cpr_rankings" in results:
        print(f"CPR Rankings: {len(results['cpr_rankings'])} teams")
        print("\n🏆 TOP 5 CPR RANKINGS")
        for i, team in enumerate(results['cpr_rankings'][:5], 1):
            print(f"{i}. {team.team_name}: {team.cpr:.3f}")
    
    if "niv_rankings" in results:
        print(f"NIV Rankings: {len(results['niv_rankings'])} players")
        print("\n🎯 TOP 5 NIV RANKINGS")
        for i, player in enumerate(results['niv_rankings'][:5], 1):
            print(f"{i}. {player.name} ({player.position.value}): {player.niv:.3f}")

if __name__ == "__main__":
    asyncio.run(main())
