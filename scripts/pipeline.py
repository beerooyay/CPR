#!/usr/bin/env python3
"""
REAL CPR-NFL DATA PROCESSING PIPELINE
Uses actual Ingram, Alvarado, and Zion algorithms
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import logging
import json

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.cpr import CPREngine
from src.niv import NIVEngine
from src.database import Database, LocalDatabase
from src.utils import make_sleeper_request
from src.models import Player, PlayerStats, Team, LeagueAnalysis, Position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _map_position(pos_str: str) -> Position:
    if not pos_str: return Position.FLEX
    pos_upper = pos_str.upper()
    if pos_upper in Position.__members__:
        return Position[pos_upper]
    # Handle defensive positions
    if pos_upper in ["DL", "DE", "DT", "LB", "OLB", "ILB", "DB", "CB", "S"]:
        return Position.IDP
    if pos_upper == "DST":
        return Position.DEF
    return Position.FLEX # Fallback

class RealCPRPipeline:
    """REAL CPR-NFL data processing pipeline based on the official guide"""

    def __init__(self, league_id: str, use_local_db: bool = False):
        self.league_id = league_id
        self.cpr_engine = CPREngine({}, league_id)
        self.niv_engine = NIVEngine({}, league_id)
        self.db = LocalDatabase() if use_local_db else Database()
        logger.info(f"REAL CPR Pipeline initialized for league: {league_id}")

    def fetch_data(self) -> dict:
        """Fetch all required data from Sleeper API according to the guide"""
        logger.info("Fetching all league data...")
        players_db = make_sleeper_request("players/nfl")
        historical_stats = {str(year): make_sleeper_request(f"stats/nfl/regular/{year}") for year in range(2019, 2026)}
        league_info = make_sleeper_request(f"league/{self.league_id}")
        rosters = make_sleeper_request(f"league/{self.league_id}/rosters")
        users = make_sleeper_request(f"league/{self.league_id}/users")
        return {
            "players_db": players_db,
            "historical_stats": historical_stats,
            "league_info": league_info,
            "rosters": rosters,
            "users": users
        }

    def process_data(self, raw_data: dict) -> dict:
        """Process raw data into structured Player and Team objects"""
        players = {}
        for player_id, player_data in raw_data['players_db'].items():
            stats = {}
            for year, year_stats in raw_data['historical_stats'].items():
                if player_id in year_stats:
                    player_year_stats = year_stats[player_id]
                    stats[int(year)] = PlayerStats(
                        season=int(year),
                        games_played=player_year_stats.get('gp', 0),
                        passing_yards=player_year_stats.get('pass_yd', 0),
                        passing_tds=player_year_stats.get('pass_td', 0),
                        passing_ints=player_year_stats.get('pass_int', 0),
                        rushing_yards=player_year_stats.get('rush_yd', 0),
                        rushing_tds=player_year_stats.get('rush_td', 0),
                        receptions=player_year_stats.get('rec', 0),
                        receiving_yards=player_year_stats.get('rec_yd', 0),
                        receiving_tds=player_year_stats.get('rec_td', 0),
                        targets=player_year_stats.get('rec_tgt', 0),
                        fumbles=player_year_stats.get('fum_lost', 0),
                        fantasy_points=player_year_stats.get('pts_ppr', 0.0)
                    )
            players[player_id] = Player(
                player_id=player_id,
                name=player_data.get('full_name', f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()),
                position=_map_position(player_data.get('position')),
                team=player_data.get('team', 'FA'),
                stats=stats
            )

        teams = []
        user_lookup = {user['user_id']: user for user in raw_data['users']}
        for roster in raw_data['rosters']:
            user_info = user_lookup.get(roster['owner_id'], {})
            teams.append(Team(
                team_id=roster['roster_id'],
                team_name=user_info.get('metadata', {}).get('team_name', user_info.get('display_name', f"Team {roster['roster_id']}")),
                owner_name=user_info.get('display_name', 'Unknown'),
                roster=roster.get('players', []),
                starters=roster.get('starters', []),
                wins=roster.get('settings', {}).get('wins', 0),
                losses=roster.get('settings', {}).get('losses', 0),
                ties=roster.get('settings', {}).get('ties', 0),
                fpts=roster.get('settings', {}).get('fpts', 0),
                fpts_against=roster.get('settings', {}).get('fpts_against', 0)
            ))

        return {"players": players, "teams": teams, "league_info": raw_data['league_info']}

    def calculate_cpr(self, processed_data: dict) -> dict:
        """Calculate CPR rankings using REAL algorithms"""
        return self.cpr_engine.calculate_league_cpr(processed_data['teams'], processed_data['players'])

    def calculate_niv(self, processed_data: dict) -> dict:
        """Calculate NIV rankings using REAL algorithms"""
        return self.niv_engine.calculate_league_niv(processed_data['teams'], processed_data['players'])
    
    def save_results(self, cpr_results: dict, niv_results: dict, league_data: dict) -> bool:
        """Save results to database"""
        logger.info("Saving CPR and NIV results to database...")
        
        try:
            # Save CPR rankings
            cpr_success = self.db.save_cpr_rankings(self.league_id, cpr_results['rankings'])
            
            # Save NIV rankings
            niv_success = self.db.save_niv_data(self.league_id, niv_results['rankings'])
            
            if cpr_success:
                logger.info("CPR rankings saved to database.")
            else:
                logger.warning("Failed to save REAL CPR rankings")
                
            if niv_success:
                logger.info("NIV rankings saved to database.")
            else:
                logger.warning("Failed to save REAL NIV rankings")
            
            return cpr_success and niv_success
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return False
    
    def generate_report(self, cpr_results: dict, processed_data: dict) -> str:
        """Generate human-readable report with REAL algorithm insights"""
        logger.info("Generating CPR report...")
        
        try:
            rankings = cpr_results['rankings']
            league_info = processed_data['league_info']
            
            report = f"""
# REAL CPR-NFL Analysis Report
**League**: {league_info.name}
**Season**: {league_info.season}, Week {league_info.current_week}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Algorithm**: {cpr_results.get('algorithm_version', 'REAL_CPR_v1.0')}

## League Overview
- **Teams**: {len(rankings)}
- **League Health**: {cpr_results['league_health']:.1%}
- **Gini Coefficient**: {cpr_results['gini_coefficient']:.3f}

## REAL CPR Rankings (Top 5)

*Using revolutionary algorithms: Ingram (HHI), Alvarado (Shapley/ADP), Zion (4D Tensor)*
"""
            
            for i, team in enumerate(rankings[:5], 1):
                report += f"""
**{i}. {team['team_name']}** - CPR: {team['cpr']:.3f}
   - Record: {team['wins']}-{team['losses']} | Tier: {team['cpr_tier']}
   - SLI: {team['sli']:.3f} | BSI: {team['bsi']:.3f} | SMI: {team['smi']:.3f}
   - **Ingram**: {team['ingram']:.3f} (positional balance)
   - **Alvarado**: {team['alvarado']:.3f} (draft value efficiency)  
   - **Zion**: {team['zion']:.3f} (4D strength of schedule)
"""
            
            # Add algorithm insights
            if cpr_results.get('insights'):
                report += "\n## REAL Algorithm Insights\n"
                for insight in cpr_results['insights']:
                    report += f"- {insight}\n"
            
            # Add algorithm explanation
            report += f"\n## Algorithm Breakdown\n"
            report += self.cpr_engine.get_algorithm_explanation()
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return f"Report generation failed: {e}"
    
    def run_pipeline(self) -> dict:
        """Run complete REAL CPR pipeline"""
        logger.info("Starting REAL CPR-NFL pipeline...")
        logger.info("Revolutionary algorithms: Ingram, Alvarado, Zion")
        
        try:
            # Step 1: Fetch data with Legion integration
            raw_data = self.fetch_data()
            processed_data = self.process_data(raw_data)
            
            # Step 2: Calculate REAL CPR
            cpr_results = self.calculate_cpr(processed_data)
            
            # Step 3: Calculate REAL NIV
            niv_results = self.calculate_niv(processed_data)
            
            # Step 4: Save results (pass raw objects, not serialized data)
            save_success = self.save_results(cpr_results, niv_results, processed_data)
            
            # Step 4: Generate report
            report = self.generate_report(cpr_results, processed_data)
            
            # Step 5: Save report locally
            report_path = Path(__file__).parent.parent / "data" / f"real_cpr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w') as f:
                f.write(report)
            
            logger.info("CPR Pipeline completed successfully.")
            logger.info(f"Report saved to: {report_path}")
            
            return {
                'success': True,
                'cpr_results': cpr_results,
                'niv_results': niv_results,
                'league_data': processed_data,
                'report': report,
                'report_path': str(report_path),
                'database_save': save_success,
                'algorithm_version': 'REAL_CPR_v1.0'
            }
            
        except Exception as e:
            logger.error(f"REAL CPR Pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'algorithm_version': 'REAL_CPR_v1.0'
            }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='REAL CPR-NFL Data Pipeline')
    parser.add_argument('--league-id', default='1267325171853701120', 
                       help='Sleeper league ID')
    parser.add_argument('--local-db', action='store_true',
                       help='Use local database instead of Firebase')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create REAL CPR pipeline
    pipeline = RealCPRPipeline(args.league_id, args.local_db)
    
    # Run pipeline
    results = pipeline.run_pipeline()
    
    if results['success']:
        print("\n" + "="*60)
        print("REAL CPR-NFL PIPELINE COMPLETE")
        print("="*60)
        print(f"League: {results['league_data']['league_info']['name']}")
        print(f"Teams analyzed: {len(results['cpr_results']['rankings'])}")
        print(f"League health: {results['cpr_results']['league_health']:.1%}")
        print(f"Algorithm: {results['algorithm_version']}")
        print(f"Report: {results['report_path']}")
        print("="*60)
        
        # Show top 3 teams with REAL algorithm breakdown
        print("\nTOP 3 REAL CPR RANKINGS:")
        for i, team in enumerate(results['cpr_results']['rankings'][:3], 1):
            print(f"{i}. {team.team_name} - CPR: {team.cpr:.3f} ({team.wins}-{team.losses})")
            print(f"   Ingram: {team.ingram:.3f} | Alvarado: {team.alvarado:.3f} | Zion: {team.zion:.3f}")
        
        print("\nREVOLUTIONARY ALGORITHMS USED:")
        print("• Ingram Index: HHI-based positional balance")
        print("• Alvarado Index: Shapley Value / ADP efficiency")  
        print("• Zion Tensor: 4D Strength of Schedule")
        
        sys.exit(0)
    else:
        print(f"\nREAL CPR Pipeline failed: {results['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
