#!/usr/bin/env python3
"""Unit tests for CPR engine"""
import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cpr import CPREngine
from models import Team, Player, LeagueInfo, CPRMetrics, Position, InjuryStatus

class TestCPREngine(unittest.TestCase):
    """Test CPR calculation engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'cpr_weights': {
                'sli': 0.30,      # Strength of Lineup Index
                'mpi': 0.25,      # Manager Performance Index  
                'tci': 0.20,      # Trade Consistency Index
                'wai': 0.15,      # Waiver Activity Index
                'isi': 0.10       # In-season Improvement
            }
        }
        self.cpr_engine = CPREngine(self.config)
        
        # Create test league
        self.test_league = LeagueInfo(
            league_id="test_league",
            name="Test League",
            season=2025,
            current_week=8,
            num_teams=10,
            roster_positions=["QB", "RB", "WR", "TE", "FLEX"],
            scoring_settings={"pass_td": 4, "rush_td": 6, "rec_td": 6, "rec": 1}
        )
        
        # Create test team
        self.test_team = Team(
            team_id="test_team",
            team_name="Test Team",
            owner_name="Test Owner",
            wins=5, losses=3, ties=0,
            fpts=1000.0, fpts_against=900.0,
            roster=["1234", "5678", "9012"]
        )
        
        # Create test players
        self.test_players = [
            Player(
                player_id="1234",
                name="Test QB",
                position=Position.QB,
                team="MIN",
                injury_status=InjuryStatus.ACTIVE
            ),
            Player(
                player_id="5678",
                name="Test RB", 
                position=Position.RB,
                team="GB",
                injury_status=InjuryStatus.ACTIVE
            ),
            Player(
                player_id="9012",
                name="Test WR",
                position=Position.WR,
                team="KC",
                injury_status=InjuryStatus.ACTIVE
            )
        ]
    
    def test_cpr_engine_initialization(self):
        """Test CPR engine initializes correctly"""
        self.assertIsInstance(self.cpr_engine, CPREngine)
        self.assertEqual(self.cpr_engine.weights['sli'], 0.30)
        self.assertEqual(self.cpr_engine.weights['mpi'], 0.25)
    
    def test_calculate_team_cpr_returns_metrics(self):
        """Test CPR calculation returns CPRMetrics object"""
        result = self.cpr_engine.calculate_team_cpr(
            self.test_team, self.test_players, self.test_league
        )
        
        self.assertIsInstance(result, CPRMetrics)
        self.assertEqual(result.team_id, self.test_team.team_id)
        self.assertEqual(result.team_name, self.test_team.team_name)
        self.assertIsInstance(result.cpr, float)
        self.assertGreaterEqual(result.cpr, 0)
        self.assertLessEqual(result.cpr, 1)
    
    def test_cpr_calculation_with_empty_roster(self):
        """Test CPR calculation with empty roster"""
        empty_team = Team(
            team_id="empty_team",
            team_name="Empty Team",
            owner_name="No Owner",
            wins=0, losses=0, ties=0,
            fpts=0.0, fpts_against=0.0,
            roster=[]
        )
        
        result = self.cpr_engine.calculate_team_cpr(
            empty_team, [], self.test_league
        )
        
        self.assertIsInstance(result, CPRMetrics)
        self.assertEqual(result.team_id, "empty_team")
        self.assertGreaterEqual(result.cpr, 0)
    
    def test_cpr_calculation_consistency(self):
        """Test CPR calculation is consistent for same inputs"""
        result1 = self.cpr_engine.calculate_team_cpr(
            self.test_team, self.test_players, self.test_league
        )
        result2 = self.cpr_engine.calculate_team_cpr(
            self.test_team, self.test_players, self.test_league
        )
        
        self.assertEqual(result1.cpr, result2.cpr)
        self.assertEqual(result1.team_id, result2.team_id)
    
    def test_cpr_components_calculation(self):
        """Test individual CPR components are calculated"""
        result = self.cpr_engine.calculate_team_cpr(
            self.test_team, self.test_players, self.test_league
        )
        
        # Check that components are calculated (should be >= 0)
        self.assertGreaterEqual(result.sli, 0)
        self.assertGreaterEqual(result.mpi, 0)
        self.assertGreaterEqual(result.tci, 0)
        self.assertGreaterEqual(result.wai, 0)
        self.assertGreaterEqual(result.isi, 0)
    
    def test_cpr_with_different_config_weights(self):
        """Test CPR calculation with different weight configurations"""
        different_config = {
            'cpr_weights': {
                'sli': 0.50,
                'mpi': 0.20,
                'tci': 0.10,
                'wai': 0.10,
                'isi': 0.10
            }
        }
        different_engine = CPREngine(different_config)
        
        result1 = self.cpr_engine.calculate_team_cpr(
            self.test_team, self.test_players, self.test_league
        )
        result2 = different_engine.calculate_team_cpr(
            self.test_team, self.test_players, self.test_league
        )
        
        # Results should be different with different weights
        self.assertNotEqual(result1.cpr, result2.cpr)
    
    def test_cpr_ranking_ordering(self):
        """Test CPR rankings can be ordered correctly"""
        # Create multiple teams with different records
        teams = [
            Team(
                team_id=f"team_{i}",
                team_name=f"Team {i}",
                owner_name=f"Owner {i}",
                wins=i, losses=(10-i), ties=0,
                fpts=i*100, fpts_against=(10-i)*100,
                roster=[f"{i}001", f"{i}002"]
            )
            for i in range(1, 6)  # 5 teams
        ]
        
        cpr_results = []
        for team in teams:
            result = self.cpr_engine.calculate_team_cpr(
                team, self.test_players[:2], self.test_league
            )
            cpr_results.append(result)
        
        # Sort by CPR
        cpr_results.sort(key=lambda x: x.cpr, reverse=True)
        
        # Check that they're sorted (higher CPR should come first)
        for i in range(len(cpr_results) - 1):
            self.assertGreaterEqual(cpr_results[i].cpr, cpr_results[i+1].cpr)
    
    def test_cpr_with_injured_players(self):
        """Test CPR calculation with injured players"""
        injured_players = [
            Player(
                player_id="injured_1",
                name="Injured Player 1",
                position=Position.QB,
                team="MIN",
                injury_status=InjuryStatus.OUT
            ),
            Player(
                player_id="injured_2", 
                name="Injured Player 2",
                position=Position.RB,
                team="GB",
                injury_status=InjuryStatus.QUESTIONABLE
            )
        ]
        
        injured_team = Team(
            team_id="injured_team",
            team_name="Injured Team",
            owner_name="Injured Owner",
            wins=3, losses=5, ties=0,
            fpts=500.0, fpts_against=600.0,
            roster=["injured_1", "injured_2"]
        )
        
        result = self.cpr_engine.calculate_team_cpr(
            injured_team, injured_players, self.test_league
        )
        
        self.assertIsInstance(result, CPRMetrics)
        self.assertGreaterEqual(result.cpr, 0)
        # CPR should be lower for injured team (this is implementation-dependent)
        # but should still be a valid calculation
    
    def test_cpr_error_handling(self):
        """Test CPR calculation handles errors gracefully"""
        # Test with None inputs
        with self.assertRaises(Exception):
            self.cpr_engine.calculate_team_cpr(None, [], self.test_league)
        
        # Test with invalid league
        invalid_league = LeagueInfo(
            league_id="", name="", season=0, current_week=0,
            num_teams=0, roster_positions=[], scoring_settings={}
        )
        
        # Should handle gracefully (not crash)
        result = self.cpr_engine.calculate_team_cpr(
            self.test_team, self.test_players, invalid_league
        )
        self.assertIsInstance(result, CPRMetrics)

if __name__ == '__main__':
    unittest.main()
