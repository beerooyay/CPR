#!/usr/bin/env python3
"""Unit tests for Jaylen AI agent"""
import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from jaylen import JaylenAI, create_jaylen_ai
from models import Player, Team, CPRMetrics, NIVMetrics, Position, InjuryStatus

class TestJaylenAI(unittest.TestCase):
    """Test Jaylen AI agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the AI model to avoid actual API calls
        with patch('jaylen.OpenRouter'), \
             patch('jaylen.MCPClient'):
            self.jaylen = JaylenAI()
    
    def test_jaylen_ai_initialization(self):
        """Test Jaylen AI initializes correctly"""
        self.assertIsInstance(self.jaylen, JaylenAI)
        self.assertIsNotNone(self.jaylen.model)
        self.assertIsNotNone(self.jaylen.mcp_client)
    
    def test_format_messages(self):
        """Test message formatting"""
        messages = [
            {"role": "user", "content": "Hello Jaylen"},
            {"role": "assistant", "content": "Hello there!"}
        ]
        
        formatted = self.jaylen._format_messages(messages)
        
        self.assertIsInstance(formatted, list)
        self.assertEqual(len(formatted), len(messages))
        
        # Check format structure
        for msg in formatted:
            self.assertIn("role", msg)
            self.assertIn("content", msg)
    
    def test_format_messages_empty(self):
        """Test message formatting with empty list"""
        formatted = self.jaylen._format_messages([])
        self.assertEqual(formatted, [])
    
    def test_format_cpr_context(self):
        """Test CPR context formatting"""
        # Create test CPR metrics
        cpr_metrics = [
            CPRMetrics(
                team_id="team1",
                team_name="Team 1",
                owner_name="Owner 1",
                cpr=0.85,
                rank=1,
                sli=0.90,
                mpi=0.80,
                tci=0.75,
                wai=0.85,
                isi=0.90
            ),
            CPRMetrics(
                team_id="team2", 
                team_name="Team 2",
                owner_name="Owner 2",
                cpr=0.65,
                rank=3,
                sli=0.70,
                mpi=0.60,
                tci=0.65,
                wai=0.70,
                isi=0.60
            )
        ]
        
        context = self.jaylen._format_cpr_context(cpr_metrics)
        
        self.assertIsInstance(context, str)
        self.assertIn("Team 1", context)
        self.assertIn("Team 2", context)
        self.assertIn("0.85", context)  # CPR score
        self.assertIn("Owner 1", context)
    
    def test_format_cpr_context_empty(self):
        """Test CPR context formatting with empty list"""
        context = self.jaylen._format_cpr_context([])
        self.assertIsInstance(context, str)
        self.assertIn("No CPR data", context)
    
    def test_format_niv_context(self):
        """Test NIV context formatting"""
        # Create test NIV metrics
        niv_metrics = [
            NIVMetrics(
                player_id="player1",
                name="Star Player",
                position=Position.WR,
                niv=0.90,
                positional_niv=0.85,
                market_niv=0.95,
                consistency_niv=0.80,
                explosive_niv=0.92,
                rank=1
            ),
            NIVMetrics(
                player_id="player2",
                name="Good Player", 
                position=Position.RB,
                niv=0.75,
                positional_niv=0.70,
                market_niv=0.80,
                consistency_niv=0.75,
                explosive_niv=0.70,
                rank=5
            )
        ]
        
        context = self.jaylen._format_niv_context(niv_metrics)
        
        self.assertIsInstance(context, str)
        self.assertIn("Star Player", context)
        self.assertIn("Good Player", context)
        self.assertIn("WR", context)
        self.assertIn("RB", context)
        self.assertIn("0.90", context)  # NIV score
    
    def test_format_niv_context_empty(self):
        """Test NIV context formatting with empty list"""
        context = self.jaylen._format_niv_context([])
        self.assertIsInstance(context, str)
        self.assertIn("No NIV data", context)
    
    def test_format_league_context(self):
        """Test league context formatting"""
        league_data = {
            "league_info": {
                "name": "Test League",
                "season": 2025,
                "current_week": 8,
                "num_teams": 10
            },
            "teams": [
                Team(
                    team_id="team1",
                    team_name="Team 1",
                    owner_name="Owner 1",
                    wins=5, losses=3, ties=0,
                    fpts=1000.0, fpts_against=900.0,
                    roster=[]
                )
            ]
        }
        
        context = self.jaylen._format_league_context(league_data)
        
        self.assertIsInstance(context, str)
        self.assertIn("Test League", context)
        self.assertIn("2025", context)
        self.assertIn("Week 8", context)
        self.assertIn("10 teams", context)
        self.assertIn("Team 1", context)
    
    def test_format_league_context_missing_data(self):
        """Test league context formatting with missing data"""
        context = self.jaylen._format_league_context({})
        self.assertIsInstance(context, str)
        self.assertIn("No league data", context)
    
    @patch('jaylen.JaylenAI._call_ai_model')
    def test_analyze_cpr_rankings(self, mock_call_ai):
        """Test CPR rankings analysis"""
        # Mock AI response
        mock_call_ai.return_value = "Team 1 is performing excellently with a CPR of 0.85."
        
        cpr_metrics = [
            CPRMetrics(
                team_id="team1",
                team_name="Team 1",
                owner_name="Owner 1",
                cpr=0.85,
                rank=1,
                sli=0.90, mpi=0.80, tci=0.75, wai=0.85, isi=0.90
            )
        ]
        
        result = self.jaylen.analyze_cpr_rankings(cpr_metrics)
        
        self.assertIsInstance(result, str)
        self.assertIn("Team 1", result)
        self.assertIn("0.85", result)
        mock_call_ai.assert_called_once()
    
    @patch('jaylen.JaylenAI._call_ai_model')
    def test_analyze_niv_rankings(self, mock_call_ai):
        """Test NIV rankings analysis"""
        # Mock AI response
        mock_call_ai.return_value = "Star Player has excellent NIV of 0.90."
        
        niv_metrics = [
            NIVMetrics(
                player_id="player1",
                name="Star Player",
                position=Position.WR,
                niv=0.90,
                positional_niv=0.85,
                market_niv=0.95,
                consistency_niv=0.80,
                explosive_niv=0.92,
                rank=1
            )
        ]
        
        result = self.jaylen.analyze_niv_rankings(niv_metrics)
        
        self.assertIsInstance(result, str)
        self.assertIn("Star Player", result)
        self.assertIn("0.90", result)
        mock_call_ai.assert_called_once()
    
    @patch('jaylen.JaylenAI._call_ai_model')
    def test_get_trade_advice(self, mock_call_ai):
        """Test trade advice generation"""
        # Mock AI response
        mock_call_ai.return_value = "Consider trading Player 1 for Player 2."
        
        team_data = {
            "team": Team(
                team_id="team1",
                team_name="Team 1",
                owner_name="Owner 1",
                wins=5, losses=3, ties=0,
                fpts=1000.0, fpts_against=900.0,
                roster=["player1", "player2"]
            ),
            "players": [
                Player("player1", "Player 1", Position.WR, "MIN", InjuryStatus.ACTIVE),
                Player("player2", "Player 2", Position.RB, "GB", InjuryStatus.ACTIVE)
            ]
        }
        
        result = self.jaylen.get_trade_advice(team_data)
        
        self.assertIsInstance(result, str)
        mock_call_ai.assert_called_once()
    
    @patch('jaylen.JaylenAI._call_ai_model')
    def test_answer_question(self, mock_call_ai):
        """Test general question answering"""
        # Mock AI response
        mock_call_ai.return_value = "Based on the data, I recommend..."
        
        question = "Who should I start this week?"
        context = {"some": "context"}
        
        result = self.jaylen.answer_question(question, context)
        
        self.assertIsInstance(result, str)
        mock_call_ai.assert_called_once()
    
    def test_call_ai_model_with_mock(self):
        """Test AI model calling with mocked response"""
        # Mock the model's chat completion
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Mock AI response"
        
        self.jaylen.model.chat.completions.create = Mock(return_value=mock_response)
        
        messages = [{"role": "user", "content": "Test message"}]
        result = self.jaylen._call_ai_model(messages)
        
        self.assertEqual(result, "Mock AI response")
        self.jaylen.model.chat.completions.create.assert_called_once()
    
    def test_error_handling_in_ai_calls(self):
        """Test error handling in AI model calls"""
        # Mock the model to raise an exception
        self.jaylen.model.chat.completions.create = Mock(
            side_effect=Exception("API Error")
        )
        
        messages = [{"role": "user", "content": "Test message"}]
        
        # Should handle the error gracefully
        result = self.jaylen._call_ai_model(messages)
        
        # Should return an error message, not crash
        self.assertIsInstance(result, str)
        self.assertIn("error", result.lower())
    
    def test_create_jaylen_ai_function(self):
        """Test the create_jaylen_ai factory function"""
        with patch('jaylen.OpenRouter'), \
             patch('jaylen.MCPClient'):
            
            jaylen = create_jaylen_ai()
            
            self.assertIsInstance(jaylen, JaylenAI)
            self.assertIsNotNone(jaylen.model)
            self.assertIsNotNone(jaylen.mcp_client)
    
    def test_create_jaylen_ai_with_config(self):
        """Test the create_jaylen_ai function with custom config"""
        config = {
            "model_name": "test-model",
            "api_key": "test-key"
        }
        
        with patch('jaylen.OpenRouter') as mock_openrouter, \
             patch('jaylen.MCPClient'):
            
            jaylen = create_jaylen_ai(config)
            
            self.assertIsInstance(jaylen, JaylenAI)
            mock_openrouter.assert_called_with(
                api_key="test-key",
                model="test-model"
            )
    
    def test_mcp_client_integration(self):
        """Test MCP client integration"""
        # Mock MCP client methods
        self.jaylen.mcp_client.call_tool = Mock(return_value={"result": "success"})
        
        # Test that MCP client can be called through Jaylen
        result = self.jaylen.mcp_client.call_tool("test_tool", {"param": "value"})
        
        self.assertEqual(result, {"result": "success"})
        self.jaylen.mcp_client.call_tool.assert_called_once_with(
            "test_tool", {"param": "value"}
        )
    
    def test_context_data_validation(self):
        """Test validation of context data"""
        # Test with None context
        result = self.jaylen._format_league_context(None)
        self.assertIsInstance(result, str)
        self.assertIn("No league data", result)
        
        # Test with malformed context
        malformed_context = {"invalid": "data"}
        result = self.jaylen._format_league_context(malformed_context)
        self.assertIsInstance(result, str)
    
    def test_large_dataset_handling(self):
        """Test handling of large datasets"""
        # Create large dataset
        large_cpr_data = [
            CPRMetrics(
                team_id=f"team_{i}",
                team_name=f"Team {i}",
                owner_name=f"Owner {i}",
                cpr=0.5 + (i * 0.01),
                rank=i,
                sli=0.5, mpi=0.5, tci=0.5, wai=0.5, isi=0.5
            )
            for i in range(100)  # 100 teams
        ]
        
        context = self.jaylen._format_cpr_context(large_cpr_data)
        
        self.assertIsInstance(context, str)
        self.assertIn("Team 1", context)
        self.assertIn("Team 100", context)
        # Should handle large datasets without issues

if __name__ == '__main__':
    unittest.main()
