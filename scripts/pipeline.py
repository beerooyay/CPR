#!/usr/bin/env python3
"""CPR-NFL Data Processing Pipeline"""
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CPRNFLPipeline:
    """Main data processing pipeline for CPR-NFL system"""
    
    def __init__(self, league_id: str, use_local_db: bool = False):
        self.league_id = league_id
        self.api = SleeperAPI(league_id)
        
        # Initialize database
        if use_local_db:
            self.db = LocalDatabase(str(Path(__file__).parent.parent / "data"))
        else:
            self.db = Database()
        
        # Initialize CPR engine with default config
        self.cpr_engine = CPREngine({
            'cpr_weights': {
                'sli': 0.30,      # Strength of Lineup Index
                'bsi': 0.20,      # Bench Strength Index  
                'smi': 0.15,      # Schedule Momentum Index
                'ingram': 0.15,   # Ingram Index (injury/availability)
                'alvarado': 0.10, # Alvarado Index (performance consistency)
                'zion': 0.10      # Zion Index (explosive plays)
            },
            'bench_multiplier': 0.3
        })
        
        logger.info(f"Pipeline initialized for league {league_id}")
        logger.info(f"Database: {'Local' if use_local_db else 'Firebase'}")
    
    def fetch_data(self) -> dict:
        """Fetch all data from Sleeper API"""
        logger.info("Fetching data from Sleeper API...")
        
        try:
            data = self.api.fetch_all_data()
            logger.info(f"✅ Fetched data for {len(data['teams'])} teams and {len(data['players'])} players")
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch data: {e}")
            raise
    
    def calculate_cpr(self, teams: list, players: dict) -> dict:
        """Calculate CPR rankings"""
        logger.info("Calculating CPR rankings...")
        
        try:
            cpr_results = self.cpr_engine.calculate_league_cpr(teams, players)
            logger.info(f"✅ CPR calculated for {len(cpr_results['rankings'])} teams")
            logger.info(f"   League health: {cpr_results['league_health']:.1%}")
            return cpr_results
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate CPR: {e}")
            raise
    
    def save_results(self, cpr_results: dict, league_data: dict) -> bool:
        """Save results to database"""
        logger.info("Saving results to database...")
        
        try:
            # Save CPR rankings
            success = self.db.save_cpr_rankings(self.league_id, cpr_results['rankings'])
            
            if success:
                logger.info("✅ CPR rankings saved to database")
            else:
                logger.warning("⚠️ Failed to save CPR rankings")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")
            return False
    
    def generate_report(self, cpr_results: dict, league_data: dict) -> str:
        """Generate human-readable report"""
        logger.info("Generating report...")
        
        try:
            rankings = cpr_results['rankings']
            league_info = league_data['league_info']
            
            report = f"""
# CPR-NFL Analysis Report
**League**: {league_info.name}
**Season**: {league_info.season}, Week {league_info.current_week}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## League Overview
- **Teams**: {len(rankings)}
- **League Health**: {cpr_results['league_health']:.1%}
- **Gini Coefficient**: {cpr_results['gini_coefficient']:.3f}

## CPR Rankings (Top 5)
"""
            
            for i, team in enumerate(rankings[:5], 1):
                report += f"""
{i}. **{team['team_name']}** - CPR: {team['cpr']:.3f}
   - Record: {team['wins']}-{team['losses']}
   - SLI: {team['sli']:.3f} | BSI: {team['bsi']:.3f} | SMI: {team['smi']:.3f}
   - Ingram: {team['ingram']:.3f} | Alvarado: {team['alvarado']:.3f} | Zion: {team['zion']:.3f}
   - Tier: {team['cpr_tier']}
"""
            
            if cpr_results.get('insights'):
                report += "\n## Key Insights\n"
                for insight in cpr_results['insights']:
                    report += f"- {insight}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Failed to generate report: {e}")
            return f"Report generation failed: {e}"
    
    def run_pipeline(self) -> dict:
        """Run complete pipeline"""
        logger.info("🚀 Starting CPR-NFL pipeline...")
        
        try:
            # Step 1: Fetch data
            league_data = self.fetch_data()
            
            # Step 2: Calculate CPR
            cpr_results = self.calculate_cpr(
                league_data['teams'], 
                league_data['players']
            )
            
            # Step 3: Save results
            save_success = self.save_results(cpr_results, league_data)
            
            # Step 4: Generate report
            report = self.generate_report(cpr_results, league_data)
            
            # Step 5: Save report locally
            report_path = Path(__file__).parent.parent / "data" / f"cpr_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, 'w') as f:
                f.write(report)
            
            logger.info(f"✅ Pipeline completed successfully!")
            logger.info(f"📄 Report saved to: {report_path}")
            
            return {
                'success': True,
                'cpr_results': cpr_results,
                'league_data': league_data,
                'report': report,
                'report_path': str(report_path),
                'database_save': save_success
            }
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CPR-NFL Data Pipeline')
    parser.add_argument('--league-id', default='1267325171853701120', 
                       help='Sleeper league ID')
    parser.add_argument('--local-db', action='store_true',
                       help='Use local database instead of Firebase')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create pipeline
    pipeline = CPRNFLPipeline(args.league_id, args.local_db)
    
    # Run pipeline
    results = pipeline.run_pipeline()
    
    if results['success']:
        print("\n" + "="*50)
        print("🏈 CPR-NFL PIPELINE COMPLETED SUCCESSFULLY! 🏈")
        print("="*50)
        print(f"League: {results['league_data']['league_info'].name}")
        print(f"Teams analyzed: {len(results['cpr_results']['rankings'])}")
        print(f"League health: {results['cpr_results']['league_health']:.1%}")
        print(f"Report: {results['report_path']}")
        print("="*50)
        
        # Show top 3 teams
        print("\n🏆 TOP 3 CPR RANKINGS:")
        for i, team in enumerate(results['cpr_results']['rankings'][:3], 1):
            print(f"{i}. {team['team_name']} - CPR: {team['cpr']:.3f} ({team['wins']}-{team['losses']})")
        
        sys.exit(0)
    else:
        print(f"\n❌ Pipeline failed: {results['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
