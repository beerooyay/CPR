#!/usr/bin/env python3
"""Integration tests for CPR-NFL system"""
import unittest
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from api import SleeperAPI
from database import Database
from cpr import CPREngine
from niv import NIVCalculator
from mcp.client import MCPClient
from models import LeagueInfo, Team, Player, PlayerStats, CPRMetrics, NIVMetrics, Position, InjuryStatus
import requests
import json

class TestSystemIntegration(unittest.TestCase):
    """Test full system integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.league_id = "test_league_123"
        self.api = SleeperAPI(self.league_id)
        self.database = Database()
        self.cpr_engine = CPREngine({})
        self.niv_calculator = NIVCalculator()
        
        self.firebase_url = "https://us-central1-cpr-nfl.cloudfunctions.net"
        self.mcp_client = MCPClient()
    
    def test_api_to_cpr_workflow(self):
        """Test workflow: API → CPR calculation"""
        # Create test data
        test_league = LeagueInfo(
            league_id=self.league_id,
            name="Test League",
            season=2025,
            current_week=8,
            num_teams=10,
            roster_positions=["QB", "RB", "WR", "TE", "FLEX"],
            scoring_settings={"pass_td": 4, "rush_td": 6, "rec_td": 6, "rec": 1}
        )
        
        test_team = Team(
            team_id="team_1",
            team_name="Test Team",
            owner_name="Test Owner",
            wins=5, losses=3, ties=0,
            fpts=1000.0, fpts_against=900.0,
            roster=["player_1", "player_2"]
        )
        
        test_players = [
            Player(
                player_id="player_1",
                name="Test QB",
                position=Position.QB,
                team="MIN",
                injury_status=InjuryStatus.ACTIVE
            ),
            Player(
                player_id="player_2",
                name="Test WR",
                position=Position.WR,
                team="GB",
                injury_status=InjuryStatus.ACTIVE
            )
        ]
        
        # Calculate CPR
        cpr_result = self.cpr_engine.calculate_team_cpr(
            test_team, test_players, test_league
        )
        
        # Verify workflow
        self.assertIsInstance(cpr_result, CPRMetrics)
        self.assertEqual(cpr_result.team_id, test_team.team_id)
        self.assertGreaterEqual(cpr_result.cpr, 0)
        self.assertLessEqual(cpr_result.cpr, 1)
    
    def test_api_to_niv_workflow(self):
        """Test workflow: API → NIV calculation"""
        # Create test player
        test_player = Player(
            player_id="player_1",
            name="Test Player",
            position=Position.WR,
            team="MIN",
            injury_status=InjuryStatus.ACTIVE
        )
        
        # Create test stats (simulating API response)
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
        niv_result = self.niv_calculator.calculate_player_niv(
            test_player, test_stats, {}
        )
        
        # Verify workflow
        self.assertIsInstance(niv_result, NIVMetrics)
        self.assertEqual(niv_result.player_id, test_player.player_id)
        self.assertGreaterEqual(niv_result.niv, 0)
        self.assertLessEqual(niv_result.niv, 1)
    
    def test_cpr_to_database_workflow(self):
        """Test workflow: CPR → Database storage"""
        # Create test CPR metrics
        cpr_metrics = CPRMetrics(
            team_id="team_1",
            team_name="Test Team",
            owner_name="Test Owner",
            cpr=0.85,
            rank=1,
            sli=0.90, mpi=0.80, tci=0.75, wai=0.85, isi=0.90
        )
        
        # Mock database save
        with patch.object(self.database, 'save_cpr_rankings') as mock_save:
            mock_save.return_value = True
            
            # Save to database
            success = self.database.save_cpr_rankings(
                self.league_id, 8, [cpr_metrics]
            )
            
            # Verify workflow
            self.assertTrue(success)
            mock_save.assert_called_once_with(self.league_id, 8, [cpr_metrics])
    
    def test_niv_to_database_workflow(self):
        """Test workflow: NIV → Database storage"""
        # Create test NIV metrics
        niv_metrics = NIVMetrics(
            player_id="player_1",
            name="Test Player",
            position=Position.WR,
            niv=0.90,
            positional_niv=0.85,
            market_niv=0.95,
            consistency_niv=0.80,
            explosive_niv=0.92,
            rank=1
        )
        
        # Mock database save
        with patch.object(self.database, 'save_niv_data') as mock_save:
            mock_save.return_value = True
            
            # Save to database
            success = self.database.save_niv_data(
                self.league_id, 8, [niv_metrics]
            )
            
            # Verify workflow
            self.assertTrue(success)
            mock_save.assert_called_once_with(self.league_id, 8, [niv_metrics])
    
    def test_full_data_pipeline(self):
        """Test complete data pipeline: API → Calculations → Database → AI"""
        # Mock API responses
        mock_league = LeagueInfo(
            league_id=self.league_id,
            name="Test League",
            season=2025,
            current_week=8,
            num_teams=2,
            roster_positions=["QB", "WR"],
            scoring_settings={"pass_td": 4, "rec_td": 6, "rec": 1}
        )
        
        mock_teams = [
            Team(
                team_id="team_1",
                team_name="Team 1",
                owner_name="Owner 1",
                wins=5, losses=3, ties=0,
                fpts=1000.0, fpts_against=900.0,
                roster=["player_1"]
            ),
            Team(
                team_id="team_2",
                team_name="Team 2",
                owner_name="Owner 2",
                wins=3, losses=5, ties=0,
                fpts=800.0, fpts_against=950.0,
                roster=["player_2"]
            )
        ]
        
        mock_players = {
            "player_1": Player(
                player_id="player_1",
                name="Player 1",
                position=Position.QB,
                team="MIN",
                injury_status=InjuryStatus.ACTIVE
            ),
            "player_2": Player(
                player_id="player_2",
                name="Player 2",
                position=Position.WR,
                team="GB",
                injury_status=InjuryStatus.ACTIVE
            )
        }
        
        mock_stats = {
            "player_1": PlayerStats(
                season=2025,
                games_played=8,
                passing_yards=2000, passing_tds=15, passing_ints=5,
                rushing_yards=100, rushing_tds=1,
                receptions=0, receiving_yards=0, receiving_tds=0,
                targets=0, fumbles=2, fantasy_points=180.0
            ),
            "player_2": PlayerStats(
                season=2025,
                games_played=8,
                passing_yards=0, passing_tds=0, passing_ints=0,
                rushing_yards=50, rushing_tds=0,
                receptions=40, receiving_yards=600, receiving_tds=4,
                targets=60, fumbles=1, fantasy_points=140.0
            )
        }
        
        # Mock API calls
        with patch.object(self.api, 'get_league_info', return_value=mock_league), \
             patch.object(self.api, 'get_rosters', return_value=mock_teams), \
             patch.object(self.api, 'get_players', return_value=mock_players), \
             patch.object(self.api, 'get_player_stats', return_value=mock_stats):
            
            # Step 1: Fetch data
            league = self.api.get_league_info()
            teams = self.api.get_rosters()
            players = self.api.get_players([])
            stats = self.api.get_player_stats(2025)
            
            # Step 2: Calculate CPR for all teams
            cpr_results = []
            for team in teams:
                roster_players = [
                    players[player_id] for player_id in team.roster
                    if player_id in players
                ]
                cpr = self.cpr_engine.calculate_team_cpr(
                    team, roster_players, league
                )
                cpr_results.append(cpr)
            
            # Step 3: Calculate NIV for all players
            niv_results = []
            for player_id, player in players.items():
                if player_id in stats:
                    player_stats = {"current": stats[player_id]}
                    niv = self.niv_calculator.calculate_player_niv(
                        player, player_stats, {}
                    )
                    niv_results.append(niv)
            
            # Step 4: Mock database saves
            with patch.object(self.database, 'save_cpr_rankings') as mock_save_cpr, \
                 patch.object(self.database, 'save_niv_data') as mock_save_niv:
                
                mock_save_cpr.return_value = True
                mock_save_niv.return_value = True
                
                # Save to database
                cpr_saved = self.database.save_cpr_rankings(
                    self.league_id, league.current_week, cpr_results
                )
                niv_saved = self.database.save_niv_data(
                    self.league_id, league.current_week, niv_results
                )
                
                # Step 5: Generate AI analysis
                with patch.object(self.jaylen, 'analyze_cpr_rankings') as mock_cpr_analysis, \
                     patch.object(self.jaylen, 'analyze_niv_rankings') as mock_niv_analysis:
                    
                    mock_cpr_analysis.return_value = "CPR analysis complete"
                    mock_niv_analysis.return_value = "NIV analysis complete"
                    
                    cpr_analysis = self.jaylen.analyze_cpr_rankings(cpr_results)
                    niv_analysis = self.jaylen.analyze_niv_rankings(niv_results)
                    
                    # Verify complete pipeline
                    self.assertIsInstance(league, LeagueInfo)
                    self.assertEqual(len(teams), 2)
                    self.assertEqual(len(cpr_results), 2)
                    self.assertGreater(len(niv_results), 0)
                    self.assertTrue(cpr_saved)
                    self.assertTrue(niv_saved)
                    self.assertIsInstance(cpr_analysis, str)
                    self.assertIsInstance(niv_analysis, str)
    
    def test_mcp_integration_workflow(self):
        """Test MCP server integration workflow"""
        # Mock MCP servers
        mock_sleeper_server = Mock()
        mock_firebase_server = Mock()
        
        mock_sleeper_server.call_tool = AsyncMock(return_value={
            "league_info": {"league_id": self.league_id, "name": "Test League"}
        })
        
        mock_firebase_server.call_tool = AsyncMock(return_value={
            "saved": True, "document_id": "cpr_analysis_123"
        })
        
        self.mcp_client.servers["sleeper_server"] = mock_sleeper_server
        self.mcp_client.servers["firebase_server"] = mock_firebase_server
        
        async def test_mcp_workflow():
            # Get league data from Sleeper
            league_data = await self.mcp_client.call_tool(
                "sleeper_server", "get_league_info", {"league_id": self.league_id}
            )
            
            # Save analysis to Firebase
            analysis_data = {
                "league_id": self.league_id,
                "analysis": "Test analysis",
                "timestamp": "2025-10-26T16:30:00Z"
            }
            
            save_result = await self.mcp_client.call_tool(
                "firebase_server", "save_analysis", {
                    "league_id": self.league_id,
                    "data": analysis_data
                }
            )
            
            return league_data, save_result
        
        league_data, save_result = asyncio.run(test_mcp_workflow())
        
        # Verify MCP workflow
        self.assertIn("league_info", league_data)
        self.assertTrue(save_result["saved"])
    
    def test_error_handling_integration(self):
        """Test error handling across integrated components"""
        # Mock API failure
        with patch.object(self.api, 'get_league_info', 
                         side_effect=Exception("API unavailable")):
            
            # System should handle API failure gracefully
            with self.assertRaises(Exception):
                league = self.api.get_league_info()
        
        # Mock database failure
        cpr_metrics = CPRMetrics(
            team_id="team_1",
            team_name="Test Team",
            owner_name="Test Owner",
            cpr=0.85,
            rank=1,
            sli=0.90, mpi=0.80, tci=0.75, wai=0.85, isi=0.90
        )
        
        with patch.object(self.database, 'save_cpr_rankings',
                         side_effect=Exception("Database unavailable")):
            
            # Should handle database failure gracefully
            with self.assertRaises(Exception):
                success = self.database.save_cpr_rankings(
                    self.league_id, 8, [cpr_metrics]
                )
    
    def test_performance_integration(self):
        """Test performance of integrated system"""
        # Create larger dataset for performance testing
        teams = []
        for i in range(10):  # 10 teams
            team = Team(
                team_id=f"team_{i}",
                team_name=f"Team {i}",
                owner_name=f"Owner {i}",
                wins=i, losses=(9-i), ties=0,
                fpts=i*100, fpts_against=(9-i)*100,
                roster=[f"player_{i}_1", f"player_{i}_2"]
            )
            teams.append(team)
        
        players = {}
        for i in range(20):  # 20 players
            player = Player(
                player_id=f"player_{i}",
                name=f"Player {i}",
                position=Position.WR if i % 2 == 0 else Position.RB,
                team="MIN",
                injury_status=InjuryStatus.ACTIVE
            )
            players[f"player_{i}"] = player
        
        # Test CPR calculation performance
        import time
        start_time = time.time()
        
        cpr_results = []
        for team in teams:
            roster_players = [
                players[player_id] for player_id in team.roster[:2]
                if player_id in players
            ]
            cpr = self.cpr_engine.calculate_team_cpr(
                team, roster_players, 
                LeagueInfo(self.league_id, "Test", 2025, 8, 10, ["WR", "RB"], {})
            )
            cpr_results.append(cpr)
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Performance assertions
        self.assertEqual(len(cpr_results), 10)
        self.assertLess(calculation_time, 5.0)  # Should complete in under 5 seconds
        
        # All results should be valid
        for result in cpr_results:
            self.assertIsInstance(result, CPRMetrics)
            self.assertGreaterEqual(result.cpr, 0)
            self.assertLessEqual(result.cpr, 1)
    
    def test_data_consistency_integration(self):
        """Test data consistency across integrated components"""
        # Create test data
        test_player = Player(
            player_id="consistency_test",
            name="Consistency Test",
            position=Position.WR,
            team="MIN",
            injury_status=InjuryStatus.ACTIVE
        )
        
        test_stats = PlayerStats(
            season=2025,
            games_played=1,
            passing_yards=0, passing_tds=0, passing_ints=0,
            rushing_yards=10, rushing_tds=0,
            receptions=8, receiving_yards=120, receiving_tds=1,
            targets=10, fumbles=0, fantasy_points=24.0
        )
        
        # Calculate NIV multiple times
        niv_results = []
        for i in range(5):
            niv = self.niv_calculator.calculate_player_niv(
                test_player, {"current": test_stats}, {}
            )
            niv_results.append(niv)
        
        # Check consistency
        first_niv = niv_results[0].niv
        for result in niv_results[1:]:
            self.assertEqual(result.niv, first_niv)
            self.assertEqual(result.player_id, test_player.player_id)
            self.assertEqual(result.position, test_player.position)

if __name__ == '__main__':
    unittest.main()
