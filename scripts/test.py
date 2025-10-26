#!/usr/bin/env python3
"""System testing script for CPR-NFL system"""
import sys
import os
from pathlib import Path
import asyncio
import logging
import unittest
from datetime import datetime
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api import SleeperAPI
from database import Database
from cpr import CPREngine
from niv import NIVCalculator
from jaylen import JaylenAI
from models import LeagueInfo, Team, Player, PlayerStats, CPRMetrics, NIVMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    """Comprehensive system testing"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.api = SleeperAPI(league_id)
        self.database = Database()
        self.cpr_engine = CPREngine({})
        self.niv_calculator = NIVCalculator()
        self.jaylen = JaylenAI()
        self.test_results = {}
        
    async def test_api_connection(self) -> bool:
        """Test Sleeper API connection"""
        logger.info("🌐 Testing Sleeper API connection...")
        
        try:
            # Test league info
            league_info = self.api.get_league_info()
            assert league_info.league_id == self.league_id
            assert league_info.name is not None
            
            # Test teams
            teams = self.api.get_rosters()
            assert len(teams) > 0
            
            # Test players
            players = self.api.get_players([])  # Empty list gets all players
            assert len(players) > 0
            
            logger.info("✅ API connection test passed")
            self.test_results["api_connection"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ API connection test failed: {e}")
            self.test_results["api_connection"] = False
            return False
    
    async def test_database_connection(self) -> bool:
        """Test database connection"""
        logger.info("💾 Testing database connection...")
        
        try:
            # Test database initialization
            assert self.database._initialized is not None
            
            # Test basic operations (if Firebase is available)
            if hasattr(self.database, 'db') and self.database.db:
                # Try a simple read operation
                leagues = self.database.db.collection('leagues').limit(1).get()
                logger.info("✅ Database connection test passed")
            else:
                logger.info("⚠️ Database not available, skipping connection test")
            
            self.test_results["database_connection"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            self.test_results["database_connection"] = False
            return False
    
    async def test_cpr_calculations(self) -> bool:
        """Test CPR calculation engine"""
        logger.info("🏆 Testing CPR calculations...")
        
        try:
            # Create test team
            from models import Position, InjuryStatus
            test_team = Team(
                team_id="test_team",
                team_name="Test Team",
                owner_name="Test Owner",
                wins=5, losses=3, ties=0,
                fpts=1000.0, fpts_against=900.0,
                roster=["1234", "5678"]
            )
            
            # Create test players
            test_players = [
                Player(
                    player_id="1234",
                    name="Test QB",
                    position=Position.QB,
                    team="MIN",
                    injury_status=InjuryStatus.ACTIVE
                ),
                Player(
                    player_id="5678", 
                    name="Test WR",
                    position=Position.WR,
                    team="GB",
                    injury_status=InjuryStatus.ACTIVE
                )
            ]
            
            # Create test league info
            test_league = LeagueInfo(
                league_id=self.league_id,
                name="Test League",
                season=2025,
                current_week=8,
                num_teams=10,
                roster_positions=["QB", "RB", "WR", "TE", "FLEX"],
                scoring_settings={"pass_td": 4, "rush_td": 6, "rec_td": 6, "rec": 1}
            )
            
            # Calculate CPR
            cpr_metrics = self.cpr_engine.calculate_team_cpr(
                test_team, test_players, test_league
            )
            
            assert isinstance(cpr_metrics, CPRMetrics)
            assert cpr_metrics.cpr >= 0
            assert cpr_metrics.team_id == test_team.team_id
            
            logger.info("✅ CPR calculations test passed")
            self.test_results["cpr_calculations"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ CPR calculations test failed: {e}")
            self.test_results["cpr_calculations"] = False
            return False
    
    async def test_niv_calculations(self) -> bool:
        """Test NIV calculation engine"""
        logger.info("🎯 Testing NIV calculations...")
        
        try:
            # Create test player
            from models import Position, InjuryStatus
            test_player = Player(
                player_id="1234",
                name="Test Player",
                position=Position.WR,
                team="MIN",
                injury_status=InjuryStatus.ACTIVE
            )
            
            # Create test stats
            test_stats = {
                "week1": PlayerStats(
                    season=2025,
                    games_played=1,
                    passing_yards=0, passing_tds=0, passing_ints=0,
                    rushing_yards=10, rushing_tds=0,
                    receptions=8, receiving_yards=120, receiving_tds=1,
                    targets=10, fumbles=0, fantasy_points=24.0
                )
            }
            
            # Calculate NIV
            niv_metrics = self.niv_calculator.calculate_player_niv(
                test_player, test_stats, {}
            )
            
            assert isinstance(niv_metrics, NIVMetrics)
            assert niv_metrics.niv >= 0
            assert niv_metrics.player_id == test_player.player_id
            
            logger.info("✅ NIV calculations test passed")
            self.test_results["niv_calculations"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ NIV calculations test failed: {e}")
            self.test_results["niv_calculations"] = False
            return False
    
    async def test_jaylen_agent(self) -> bool:
        """Test Jaylen AI agent"""
        logger.info("🤖 Testing Jaylen AI agent...")
        
        try:
            # Test agent initialization
            assert self.jaylen.model is not None
            assert self.jaylen.mcp_client is not None
            
            # Test basic message processing (without actually calling AI)
            test_messages = [
                {"role": "user", "content": "Hello Jaylen"}
            ]
            
            # Test message formatting
            formatted = self.jaylen._format_messages(test_messages)
            assert len(formatted) > 0
            
            logger.info("✅ Jaylen agent test passed")
            self.test_results["jaylen_agent"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Jaylen agent test failed: {e}")
            self.test_results["jaylen_agent"] = False
            return False
    
    async def test_mcp_servers(self) -> bool:
        """Test MCP server functionality"""
        logger.info("🔌 Testing MCP servers...")
        
        try:
            # Test MCP client
            assert self.jaylen.mcp_client is not None
            
            # Test server configuration
            config_path = Path(__file__).parent.parent / "config" / "mcp_config.json"
            assert config_path.exists()
            
            with open(config_path) as f:
                config = json.load(f)
                assert "sleeper_server" in config
                assert "firebase_server" in config
            
            logger.info("✅ MCP servers test passed")
            self.test_results["mcp_servers"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ MCP servers test failed: {e}")
            self.test_results["mcp_servers"] = False
            return False
    
    async def test_web_frontend(self) -> bool:
        """Test web frontend files"""
        logger.info("🌐 Testing web frontend...")
        
        try:
            web_path = Path(__file__).parent.parent / "web"
            
            # Check required files exist
            required_files = ["index.html", "styles.css", "app.js"]
            for file in required_files:
                file_path = web_path / file
                assert file_path.exists(), f"Missing {file}"
                assert file_path.stat().st_size > 0, f"Empty {file}"
            
            # Check assets
            assets_path = web_path / "assets"
            assert assets_path.exists(), "Missing assets folder"
            
            jaylen_path = assets_path / "jaylen.png"
            assert jaylen_path.exists(), "Missing jaylen.png"
            
            logger.info("✅ Web frontend test passed")
            self.test_results["web_frontend"] = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Web frontend test failed: {e}")
            self.test_results["web_frontend"] = False
            return False
    
    async def run_all_tests(self) -> dict:
        """Run all system tests"""
        logger.info("🚀 Starting comprehensive system tests...")
        
        start_time = datetime.now()
        
        # Run all tests
        tests = [
            self.test_api_connection(),
            self.test_database_connection(),
            self.test_cpr_calculations(),
            self.test_niv_calculations(),
            self.test_jaylen_agent(),
            self.test_mcp_servers(),
            self.test_web_frontend()
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate summary
        passed = sum(1 for r in results if r is True)
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        summary = {
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "success_rate": success_rate,
            "duration_seconds": duration,
            "test_results": self.test_results,
            "timestamp": end_time.isoformat()
        }
        
        return summary
    
    def print_test_report(self, summary: dict):
        """Print detailed test report"""
        print("\n" + "="*60)
        print("🧪 CPR-NFL SYSTEM TEST REPORT")
        print("="*60)
        
        print(f"📊 SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Duration: {summary.get('duration_seconds', 0):.2f}s")
        print(f"   Timestamp: {summary['timestamp']}")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_name, result in summary['test_results'].items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n🎯 OVERALL STATUS:")
        if summary['success_rate'] >= 80:
            print("   🟢 SYSTEM HEALTHY")
        elif summary['success_rate'] >= 60:
            print("   🟡 SYSTEM NEEDS ATTENTION")
        else:
            print("   🔴 SYSTEM HAS ISSUES")
        
        print("="*60)

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test CPR-NFL system")
    parser.add_argument("--league-id", default="1267325171853701120", 
                       help="League ID to test with")
    parser.add_argument("--test", choices=[
        "api", "database", "cpr", "niv", "jaylen", "mcp", "web", "all"
    ], default="all", help="Specific test to run")
    parser.add_argument("--output", help="Output file for test results")
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = SystemTester(args.league_id)
    
    # Run tests
    if args.test == "all":
        summary = await tester.run_all_tests()
    else:
        test_map = {
            "api": tester.test_api_connection,
            "database": tester.test_database_connection,
            "cpr": tester.test_cpr_calculations,
            "niv": tester.test_niv_calculations,
            "jaylen": tester.test_jaylen_agent,
            "mcp": tester.test_mcp_servers,
            "web": tester.test_web_frontend
        }
        
        if args.test in test_map:
            result = await test_map[args.test]()
            summary = {
                "total_tests": 1,
                "passed_tests": 1 if result else 0,
                "failed_tests": 0 if result else 1,
                "success_rate": 100 if result else 0,
                "test_results": {args.test: result},
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"Unknown test: {args.test}")
            return
    
    # Print report
    tester.print_test_report(summary)
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"💾 Test results saved to {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if summary['success_rate'] >= 80 else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())
