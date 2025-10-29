#!/usr/bin/env python3
"""
REAL CPR CALCULATION SCRIPT
Uses actual Ingram, Alvarado, and Zion algorithms
"""

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
from models import LeagueInfo, Team, Player, PlayerStats, CPRMetrics
from team_extraction import LegionTeamExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealCalculationEngine:
    """REAL calculation coordinator for CPR using revolutionary algorithms"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.api = SleeperAPI(league_id)
        self.database = Database()
        
        # Initialize REAL CPR engine
        self.cpr_engine = CPREngine({
            'cpr_weights': {
                'sli': 0.30,      # Strength of Lineup Index
                'bsi': 0.20,      # Bench Strength Index  
                'smi': 0.15,      # Schedule Momentum Index
                'ingram': 0.15,   # Ingram Index (HHI positional balance)
                'alvarado': 0.10, # Alvarado Index (Shapley/ADP value efficiency)
                'zion': 0.10      # Zion Tensor (4D SoS)
            },
            'bench_multiplier': 0.3,
            'current_season': 2025
        }, league_id)
        
        # Initialize Legion team extractor
        self.team_extractor = LegionTeamExtractor(league_id)
        
        logger.info("AI REAL Calculation Engine initialized with revolutionary algorithms")
        
    async def calculate_cpr_rankings(self, week: int = None) -> list[CPRMetrics]:
        """Calculate REAL CPR rankings for all teams"""
        logger.info(" Calculating REAL CPR rankings...")
        logger.info("ALGO Using: Ingram (HHI), Alvarado (Shapley/ADP), Zion (4D Tensor)")
        
        try:
            # Get league data
            league_info = self.api.get_league_info()
            teams = self.api.get_rosters()
            
            # Enhance teams with Legion names
            legion_teams = self.team_extractor.get_teams()
            for team in teams:
                legion_team = next((lt for lt in legion_teams if lt['roster_id'] == int(team.team_id)), None)
                if legion_team:
                    team.team_name = legion_team['team_name']
            
            # Collect all rostered player IDs
            all_player_ids = []
            for t in teams:
                all_player_ids.extend(getattr(t, 'roster', []) or [])
            all_player_ids = list(set(all_player_ids))
            
            players = self.api.get_players(all_player_ids)
            player_stats = self.api.get_player_stats(league_info.season)

            # Attach season stats to players
            for pid, p in players.items():
                stats_obj = player_stats.get(pid)
                if stats_obj:
                    p.stats[league_info.season] = stats_obj
            
            # Calculate REAL CPR for each team
            logger.info("AI Running REAL CPR calculations...")
            cpr_results = self.cpr_engine.calculate_league_cpr(teams, players)
            
            # Convert to CPRMetrics objects
            cpr_rankings = []
            for team_data in cpr_results['rankings']:
                metrics = CPRMetrics(
                    team_id=team_data['team_id'],
                    team_name=team_data['team_name'],
                    cpr=team_data['cpr'],
                    sli=team_data['sli'],
                    bsi=team_data['bsi'],
                    smi=team_data['smi'],
                    ingram=team_data['ingram'],
                    alvarado=team_data['alvarado'],
                    zion=team_data['zion'],
                    rank=team_data['rank'],
                    wins=team_data['wins'],
                    losses=team_data['losses']
                )
                cpr_rankings.append(metrics)
            
            logger.info(f"PASS REAL CPR rankings calculated for {len(cpr_rankings)} teams")
            logger.info(f"   League health: {cpr_results['league_health']:.1%}")
            
            return cpr_rankings
            
        except Exception as e:
            logger.error(f"FAIL Error calculating REAL CPR rankings: {e}")
            raise
    
    async def calculate_all_metrics(self, week: int = None) -> dict:
        """Calculate REAL CPR metrics"""
        logger.info("START Starting REAL CPR calculation...")
        
        # Calculate REAL CPR rankings
        cpr_rankings = await self.calculate_cpr_rankings(week)
        
        results = {
            "cpr_rankings": cpr_rankings,
            "calculated_at": datetime.now().isoformat(),
            "week": week or "current",
            "algorithm_version": "REAL_CPR_v1.0",
            "algorithms_used": {
                "ingram": "HHI-based positional balance",
                "alvarado": "Shapley Value / ADP efficiency",
                "zion": "4D Strength of Schedule tensor"
            }
        }
        
        logger.info("PASS REAL CPR calculations completed!")
        return results
    
    async def save_to_database(self, results: dict):
        """Save REAL calculation results to database"""
        logger.info("SAVE Saving REAL CPR calculations to database...")
        
        try:
            # Save CPR rankings (latest)
            if "cpr_rankings" in results:
                # Convert CPRMetrics to dict format for database
                rankings_data = []
                for metrics in results["cpr_rankings"]:
                    rankings_data.append({
                        'team_id': metrics.team_id,
                        'team_name': metrics.team_name,
                        'cpr': metrics.cpr,
                        'rank': metrics.rank,
                        'wins': metrics.wins,
                        'losses': metrics.losses,
                        'sli': metrics.sli,
                        'bsi': metrics.bsi,
                        'smi': metrics.smi,
                        'ingram': metrics.ingram,
                        'alvarado': metrics.alvarado,
                        'zion': metrics.zion,
                        'cpr_tier': metrics.cpr_tier
                    })
                
                self.database.save_cpr_rankings(
                    self.league_id,
                    rankings_data
                )
            
            logger.info("PASS REAL CPR calculations saved to database!")
            
        except Exception as e:
            logger.error(f"FAIL Error saving REAL calculations: {e}")
            raise

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculate REAL CPR-NFL metrics")
    parser.add_argument("--league-id", default="1267325171853701120", 
                       help="League ID to calculate for")
    parser.add_argument("--week", type=int, help="Specific week to calculate")
    parser.add_argument("--save", action="store_true", 
                       help="Save results to database")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize REAL calculator
    calculator = RealCalculationEngine(args.league_id)
    
    # Calculate REAL CPR metrics
    results = await calculator.calculate_all_metrics(args.week)
    
    # Save to database if requested
    if args.save:
        await calculator.save_to_database(results)
    
    # Save to file if requested
    if args.output:
        # Convert CPRMetrics objects to dict for JSON serialization
        json_results = {
            "cpr_rankings": [
                {
                    'team_id': m.team_id,
                    'team_name': m.team_name,
                    'cpr': m.cpr,
                    'rank': m.rank,
                    'wins': m.wins,
                    'losses': m.losses,
                    'sli': m.sli,
                    'bsi': m.bsi,
                    'smi': m.smi,
                    'ingram': m.ingram,
                    'alvarado': m.alvarado,
                    'zion': m.zion,
                    'cpr_tier': m.cpr_tier
                }
                for m in results['cpr_rankings']
            ],
            "calculated_at": results['calculated_at'],
            "week": results['week'],
            "algorithm_version": results['algorithm_version'],
            "algorithms_used": results['algorithms_used']
        }
        
        with open(args.output, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        logger.info(f"SAVE Results saved to {args.output}")
    
    # Print summary
    print("\n" + "="*50)
    print("DATA REAL CPR CALCULATION SUMMARY")
    print("="*50)
    print(f"Week: {results['week']}")
    print(f"Calculated At: {results['calculated_at']}")
    print(f"Algorithm: {results['algorithm_version']}")
    print(f"Teams: {len(results['cpr_rankings'])}")
    
    print("\n TOP 5 REAL CPR RANKINGS")
    print("-" * 50)
    for i, team in enumerate(results['cpr_rankings'][:5], 1):
        print(f"{i}. {team.team_name}: {team.cpr:.3f} ({team.wins}-{team.losses})")
        print(f"   Ingram: {team.ingram:.3f} | Alvarado: {team.alvarado:.3f} | Zion: {team.zion:.3f}")
    
    print("\nAI REVOLUTIONARY ALGORITHMS USED:")
    for algo, desc in results['algorithms_used'].items():
        print(f"• {algo.title()}: {desc}")

if __name__ == "__main__":
    asyncio.run(main())
