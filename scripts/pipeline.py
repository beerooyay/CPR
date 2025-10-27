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
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api import SleeperAPI
from cpr import CPREngine
from database import Database, LocalDatabase
from models import LeagueAnalysis
from team_extraction import LegionTeamExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealCPRPipeline:
    """REAL CPR data processing pipeline using revolutionary algorithms"""
    
    def __init__(self, league_id: str, use_local_db: bool = False):
        self.league_id = league_id
        self.api = SleeperAPI(league_id)
        
        # Initialize database
        if use_local_db:
            self.db = LocalDatabase(str(Path(__file__).parent.parent / "data"))
        else:
            self.db = Database()
        
        # Initialize REAL CPR engine with proper config
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
        
        logger.info(f"🚀 REAL CPR Pipeline initialized for league {league_id}")
        logger.info(f"Database: {'Local' if use_local_db else 'Firebase'}")
        logger.info("🧠 Using REVOLUTIONARY algorithms: Ingram (HHI), Alvarado (Shapley/ADP), Zion (4D Tensor)")
    
    def fetch_data(self) -> dict:
        """Fetch all data from Sleeper API with Legion team integration"""
        logger.info("📡 Fetching data from Sleeper API...")
        
        try:
            # Get base data from API
            data = self.api.fetch_all_data()
            
            # Enhance with Legion team data
            logger.info("🏈 Enhancing with Legion team data...")
            legion_teams = self.team_extractor.get_teams()
            
            # Update team names with real Legion names
            for team in data['teams']:
                legion_team = next((lt for lt in legion_teams if lt['roster_id'] == int(team.team_id)), None)
                if legion_team:
                    team.team_name = legion_team['team_name']
                    logger.debug(f"✅ Updated team name: {team.team_name}")
            
            logger.info(f"✅ Fetched data for {len(data['teams'])} teams and {len(data['players'])} players")
            logger.info(f"✅ Enhanced with Legion team names: {len([t for t in legion_teams if t['has_custom_name']])} custom names")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch data: {e}")
            raise
    
    def calculate_cpr(self, teams: list, players: dict) -> dict:
        """Calculate CPR rankings using REAL algorithms"""
        logger.info("🧠 Calculating REAL CPR rankings...")
        logger.info("🔬 Using: Ingram (HHI), Alvarado (Shapley/ADP), Zion (4D Tensor)")
        
        try:
            cpr_results = self.cpr_engine.calculate_league_cpr(teams, players)
            
            logger.info(f"✅ REAL CPR calculated for {len(cpr_results['rankings'])} teams")
            logger.info(f"   League health: {cpr_results['league_health']:.1%}")
            logger.info(f"   Algorithm version: {cpr_results.get('algorithm_version', 'Unknown')}")
            
            return cpr_results
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate REAL CPR: {e}")
            raise
    
    def save_results(self, cpr_results: dict, league_data: dict) -> bool:
        """Save results to database"""
        logger.info("💾 Saving REAL CPR results to database...")
        
        try:
            # Save CPR rankings
            success = self.db.save_cpr_rankings(self.league_id, cpr_results['rankings'])
            
            if success:
                logger.info("✅ REAL CPR rankings saved to database")
            else:
                logger.warning("⚠️ Failed to save REAL CPR rankings")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")
            return False
    
    def generate_report(self, cpr_results: dict, league_data: dict) -> str:
        """Generate human-readable report with REAL algorithm insights"""
        logger.info("📄 Generating REAL CPR report...")
        
        try:
            rankings = cpr_results['rankings']
            league_info = league_data['league_info']
            
            report = f"""
# 🏈 REAL CPR-NFL Analysis Report
**League**: {league_info.name}
**Season**: {league_info.season}, Week {league_info.current_week}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Algorithm**: {cpr_results.get('algorithm_version', 'REAL_CPR_v1.0')}

## 📊 League Overview
- **Teams**: {len(rankings)}
- **League Health**: {cpr_results['league_health']:.1%}
- **Gini Coefficient**: {cpr_results['gini_coefficient']:.3f}

## 🏆 REAL CPR Rankings (Top 5)

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
                report += "\n## 🧠 REAL Algorithm Insights\n"
                for insight in cpr_results['insights']:
                    report += f"- {insight}\n"
            
            # Add algorithm explanation
            report += f"\n## 🔬 Algorithm Breakdown\n"
            report += self.cpr_engine.get_algorithm_explanation()
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")
            return f"Report generation failed: {e}"
    
    def run_pipeline(self) -> dict:
        """Run complete REAL CPR pipeline"""
        logger.info("🚀 Starting REAL CPR-NFL pipeline...")
        logger.info("🧠 Revolutionary algorithms: Ingram, Alvarado, Zion")
        
        try:
            # Step 1: Fetch data with Legion integration
            league_data = self.fetch_data()
            
            # Step 2: Calculate REAL CPR
            cpr_results = self.calculate_cpr(
                league_data['teams'], 
                league_data['players']
            )
            
            # Step 3: Save results
            save_success = self.save_results(cpr_results, league_data)
            
            # Step 4: Generate report
            report = self.generate_report(cpr_results, league_data)
            
            # Step 5: Save report locally
            report_path = Path(__file__).parent.parent / "data" / f"real_cpr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w') as f:
                f.write(report)
            
            logger.info(f"✅ REAL CPR Pipeline completed successfully!")
            logger.info(f"📄 Report saved to: {report_path}")
            
            return {
                'success': True,
                'cpr_results': cpr_results,
                'league_data': league_data,
                'report': report,
                'report_path': str(report_path),
                'database_save': save_success,
                'algorithm_version': 'REAL_CPR_v1.0'
            }
            
        except Exception as e:
            logger.error(f"❌ REAL CPR Pipeline failed: {e}")
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
        print("🏈 REAL CPR-NFL PIPELINE COMPLETED SUCCESSFULLY! 🏈")
        print("="*60)
        print(f"League: {results['league_data']['league_info'].name}")
        print(f"Teams analyzed: {len(results['cpr_results']['rankings'])}")
        print(f"League health: {results['cpr_results']['league_health']:.1%}")
        print(f"Algorithm: {results['algorithm_version']}")
        print(f"Report: {results['report_path']}")
        print("="*60)
        
        # Show top 3 teams with REAL algorithm breakdown
        print("\n🏆 TOP 3 REAL CPR RANKINGS:")
        for i, team in enumerate(results['cpr_results']['rankings'][:3], 1):
            print(f"{i}. {team['team_name']} - CPR: {team['cpr']:.3f} ({team['wins']}-{team['losses']})")
            print(f"   Ingram: {team['ingram']:.3f} | Alvarado: {team['alvarado']:.3f} | Zion: {team['zion']:.3f}")
        
        print("\n🧠 REVOLUTIONARY ALGORITHMS USED:")
        print("• Ingram Index: HHI-based positional balance")
        print("• Alvarado Index: Shapley Value / ADP efficiency")  
        print("• Zion Tensor: 4D Strength of Schedule")
        
        sys.exit(0)
    else:
        print(f"\n❌ REAL CPR Pipeline failed: {results['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
