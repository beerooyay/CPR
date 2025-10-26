#!/usr/bin/env python3
"""Unit tests for NIV calculator"""
import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from niv import NIVCalculator, NIVConfig
from models import Player, PlayerStats, NIVMetrics, Position, InjuryStatus

class TestNIVCalculator(unittest.TestCase):
    """Test NIV calculation engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.niv_calculator = NIVCalculator()
        
        # Create test player
        self.test_player = Player(
            player_id="test_player",
            name="Test Player",
            position=Position.WR,
            team="MIN",
            injury_status=InjuryStatus.ACTIVE
        )
        
        # Create test stats
        self.test_stats = {
            "week1": PlayerStats(
                season=2025,
                games_played=1,
                passing_yards=0, passing_tds=0, passing_ints=0,
                rushing_yards=10, rushing_tds=0,
                receptions=8, receiving_yards=120, receiving_tds=1,
                targets=10, fumbles=0, fantasy_points=24.0
            ),
            "week2": PlayerStats(
                season=2025,
                games_played=1,
                passing_yards=0, passing_tds=0, passing_ints=0,
                rushing_yards=5, rushing_tds=0,
                receptions=6, receiving_yards=95, receiving_tds=0,
                targets=8, fumbles=0, fantasy_points=15.5
            ),
            "week3": PlayerStats(
                season=2025,
                games_played=1,
                passing_yards=0, passing_tds=0, passing_ints=0,
                rushing_yards=15, rushing_tds=1,
                receptions=10, receiving_yards=150, receiving_tds=2,
                targets=12, fumbles=1, fantasy_points=35.5
            )
        }
    
    def test_niv_calculator_initialization(self):
        """Test NIV calculator initializes correctly"""
        self.assertIsInstance(self.niv_calculator, NIVCalculator)
        self.assertIsInstance(self.niv_calculator.config, NIVConfig)
        self.assertEqual(self.niv_calculator.config.passing_yd_weight, 0.04)
        self.assertEqual(self.niv_calculator.config.rec_weight, 1.0)
    
    def test_calculate_player_niv_returns_metrics(self):
        """Test NIV calculation returns NIVMetrics object"""
        result = self.niv_calculator.calculate_player_niv(
            self.test_player, self.test_stats, {}
        )
        
        self.assertIsInstance(result, NIVMetrics)
        self.assertEqual(result.player_id, self.test_player.player_id)
        self.assertEqual(result.name, self.test_player.name)
        self.assertEqual(result.position, self.test_player.position)
        self.assertIsInstance(result.niv, float)
        self.assertGreaterEqual(result.niv, 0)
        self.assertLessEqual(result.niv, 1)
    
    def test_niv_calculation_with_empty_stats(self):
        """Test NIV calculation with empty stats"""
        result = self.niv_calculator.calculate_player_niv(
            self.test_player, {}, {}
        )
        
        self.assertIsInstance(result, NIVMetrics)
        self.assertEqual(result.player_id, self.test_player.player_id)
        # Should return zero/neutral values for empty stats
        self.assertGreaterEqual(result.niv, 0)
    
    def test_niv_calculation_consistency(self):
        """Test NIV calculation is consistent for same inputs"""
        result1 = self.niv_calculator.calculate_player_niv(
            self.test_player, self.test_stats, {}
        )
        result2 = self.niv_calculator.calculate_player_niv(
            self.test_player, self.test_stats, {}
        )
        
        self.assertEqual(result1.niv, result2.niv)
        self.assertEqual(result1.player_id, result2.player_id)
        self.assertEqual(result1.positional_niv, result2.positional_niv)
    
    def test_fantasy_points_calculation(self):
        """Test fantasy points calculation"""
        stats = self.test_stats["week1"]
        points = self.niv_calculator._calculate_fantasy_points(stats)
        
        # Expected: 8 receptions * 1.0 + 120 receiving_yards * 0.1 + 1 receiving_td * 6.0 + 10 rushing_yards * 0.1
        # = 8.0 + 12.0 + 6.0 + 1.0 = 27.0 (minus fumble * 2.0 = 25.0)
        expected = (8 * 1.0) + (120 * 0.1) + (1 * 6.0) + (10 * 0.1) - (0 * 2.0)
        self.assertEqual(points, expected)
    
    def test_fantasy_points_qb_calculation(self):
        """Test fantasy points calculation for QB"""
        qb_stats = PlayerStats(
            season=2025,
            games_played=1,
            passing_yards=250, passing_tds=2, passing_ints=1,
            rushing_yards=20, rushing_tds=0,
            receptions=0, receiving_yards=0, receiving_tds=0,
            targets=0, fumbles=0, fantasy_points=0.0
        )
        
        points = self.niv_calculator._calculate_fantasy_points(qb_stats)
        
        # Expected: 250 * 0.04 + 2 * 4.0 + 1 * -2.0 + 20 * 0.1
        # = 10.0 + 8.0 - 2.0 + 2.0 = 18.0
        expected = (250 * 0.04) + (2 * 4.0) + (1 * -2.0) + (20 * 0.1)
        self.assertEqual(points, expected)
    
    def test_recent_performance_calculation(self):
        """Test recent performance calculation"""
        performance = self.niv_calculator._calculate_recent_performance(
            self.test_player, self.test_stats
        )
        
        self.assertIsInstance(performance, float)
        self.assertGreaterEqual(performance, 0)
        self.assertLessEqual(performance, 1)
    
    def test_consistency_calculation(self):
        """Test consistency calculation"""
        consistency = self.niv_calculator._calculate_consistency(
            self.test_player, self.test_stats
        )
        
        self.assertIsInstance(consistency, float)
        self.assertGreaterEqual(consistency, 0)
        self.assertLessEqual(consistency, 1)
    
    def test_upside_calculation(self):
        """Test upside calculation"""
        upside = self.niv_calculator._calculate_upside(
            self.test_player, self.test_stats
        )
        
        self.assertIsInstance(upside, float)
        self.assertGreaterEqual(upside, 0)
        self.assertLessEqual(upside, 1)
    
    def test_injury_risk_calculation(self):
        """Test injury risk calculation for different statuses"""
        # Test active player
        active_player = Player(
            player_id="active",
            name="Active Player",
            position=Position.WR,
            team="MIN",
            injury_status=InjuryStatus.ACTIVE
        )
        risk = self.niv_calculator._calculate_injury_risk(active_player)
        self.assertEqual(risk, 0.0)
        
        # Test questionable player
        questionable_player = Player(
            player_id="questionable",
            name="Questionable Player", 
            position=Position.WR,
            team="MIN",
            injury_status=InjuryStatus.QUESTIONABLE
        )
        risk = self.niv_calculator._calculate_injury_risk(questionable_player)
        self.assertEqual(risk, 0.3)
        
        # Test out player
        out_player = Player(
            player_id="out",
            name="Out Player",
            position=Position.WR,
            team="MIN",
            injury_status=InjuryStatus.OUT
        )
        risk = self.niv_calculator._calculate_injury_risk(out_player)
        self.assertEqual(risk, 1.0)
    
    def test_positional_niv_calculation(self):
        """Test positional NIV calculation"""
        positional_niv = self.niv_calculator._calculate_positional_niv(
            self.test_player, 0.5, 0.6, 0.7, 0.8, 0.1
        )
        
        self.assertIsInstance(positional_niv, float)
        self.assertGreaterEqual(positional_niv, 0)
        self.assertLessEqual(positional_niv, 1)
    
    def test_overall_niv_calculation(self):
        """Test overall NIV calculation"""
        overall_niv = self.niv_calculator._calculate_overall_niv(0.5, Position.WR)
        
        self.assertIsInstance(overall_niv, float)
        self.assertGreaterEqual(overall_niv, 0)
        self.assertLessEqual(overall_niv, 1)
    
    def test_niv_for_different_positions(self):
        """Test NIV calculation for different positions"""
        positions = [Position.QB, Position.RB, Position.WR, Position.TE]
        
        for position in positions:
            player = Player(
                player_id=f"test_{position.value.lower()}",
                name=f"Test {position.value}",
                position=position,
                team="MIN",
                injury_status=InjuryStatus.ACTIVE
            )
            
            result = self.niv_calculator.calculate_player_niv(
                player, self.test_stats, {}
            )
            
            self.assertIsInstance(result, NIVMetrics)
            self.assertEqual(result.position, position)
            self.assertGreaterEqual(result.niv, 0)
    
    def test_niv_with_custom_config(self):
        """Test NIV calculation with custom configuration"""
        custom_config = NIVConfig(
            passing_yd_weight=0.05,
            rec_weight=1.5,
            receiving_td_weight=8.0
        )
        custom_calculator = NIVCalculator(custom_config)
        
        result1 = self.niv_calculator.calculate_player_niv(
            self.test_player, self.test_stats, {}
        )
        result2 = custom_calculator.calculate_player_niv(
            self.test_player, self.test_stats, {}
        )
        
        # Results should be different with different configs
        self.assertNotEqual(result1.niv, result2.niv)
    
    def test_niv_error_handling(self):
        """Test NIV calculation handles errors gracefully"""
        # Test with None player
        with self.assertRaises(Exception):
            self.niv_calculator.calculate_player_niv(None, self.test_stats, {})
        
        # Test with invalid stats (should handle gracefully)
        invalid_stats = {
            "invalid": PlayerStats(
                season=2025,
                games_played=1,
                passing_yards=-1,  # Invalid negative yards
                passing_tds=0, passing_ints=0,
                rushing_yards=0, rushing_tds=0,
                receptions=0, receiving_yards=0, receiving_tds=0,
                targets=0, fumbles=0, fantasy_points=0.0
            )
        }
        
        # Should handle gracefully (not crash)
        result = self.niv_calculator.calculate_player_niv(
            self.test_player, invalid_stats, {}
        )
        self.assertIsInstance(result, NIVMetrics)
    
    def test_niv_ranking_ordering(self):
        """Test NIV rankings can be ordered correctly"""
        # Create players with different performance levels
        players_data = [
            (Player("p1", "Star Player", Position.WR, "MIN", InjuryStatus.ACTIVE), 
             {"week1": PlayerStats(2025, 1, 0, 0, 0, 0, 0, 10, 200, 2, 15, 0, 40.0)}),
            (Player("p2", "Good Player", Position.WR, "GB", InjuryStatus.ACTIVE),
             {"week1": PlayerStats(2025, 1, 0, 0, 0, 0, 0, 8, 120, 1, 10, 0, 24.0)}),
            (Player("p3", "Average Player", Position.WR, "KC", InjuryStatus.ACTIVE),
             {"week1": PlayerStats(2025, 1, 0, 0, 0, 0, 0, 5, 80, 0, 8, 0, 13.0)})
        ]
        
        niv_results = []
        for player, stats in players_data:
            result = self.niv_calculator.calculate_player_niv(player, stats, {})
            niv_results.append(result)
        
        # Sort by NIV
        niv_results.sort(key=lambda x: x.niv, reverse=True)
        
        # Check that they're sorted (higher NIV should come first)
        for i in range(len(niv_results) - 1):
            self.assertGreaterEqual(niv_results[i].niv, niv_results[i+1].niv)

if __name__ == '__main__':
    unittest.main()
