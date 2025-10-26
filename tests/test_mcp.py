#!/usr/bin/env python3
"""Unit tests for MCP integration"""
import unittest
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp.client import MCPClient
from mcp.sleeper_server import server as sleeper_server
from mcp.firebase_server import server as firebase_server

class TestMCPClient(unittest.TestCase):
    """Test MCP client functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mcp_client = MCPClient()
    
    def test_mcp_client_initialization(self):
        """Test MCP client initializes correctly"""
        self.assertIsInstance(self.mcp_client, MCPClient)
        self.assertIsNotNone(self.mcp_client.servers)
        self.assertIsNotNone(self.mcp_client.config)
    
    def test_load_config(self):
        """Test configuration loading"""
        config = self.mcp_client._load_config()
        
        self.assertIsInstance(config, dict)
        self.assertIn("sleeper_server", config)
        self.assertIn("firebase_server", config)
    
    def test_load_config_missing_file(self):
        """Test configuration loading with missing file"""
        # Mock missing config file
        with patch('pathlib.Path.exists', return_value=False):
            config = self.mcp_client._load_config()
            self.assertIsInstance(config, dict)
    
    def test_initialize_servers(self):
        """Test server initialization"""
        # Mock server initialization
        with patch.object(self.mcp_client, '_initialize_server') as mock_init:
            mock_init.return_value = Mock()
            
            self.mcp_client.initialize_servers()
            
            # Should initialize both servers
            self.assertEqual(mock_init.call_count, 2)
    
    def test_call_tool_success(self):
        """Test successful tool call"""
        # Mock server response
        mock_server = Mock()
        mock_server.call_tool = AsyncMock(return_value={"result": "success"})
        
        self.mcp_client.servers["test_server"] = mock_server
        
        async def test_call():
            result = await self.mcp_client.call_tool(
                "test_server", "test_tool", {"param": "value"}
            )
            return result
        
        result = asyncio.run(test_call())
        
        self.assertEqual(result, {"result": "success"})
        mock_server.call_tool.assert_called_once_with(
            "test_tool", {"param": "value"}
        )
    
    def test_call_tool_server_not_found(self):
        """Test tool call with server not found"""
        async def test_call():
            result = await self.mcp_client.call_tool(
                "nonexistent_server", "test_tool", {}
            )
            return result
        
        result = asyncio.run(test_call())
        
        self.assertIn("error", result.lower())
    
    def test_call_tool_exception_handling(self):
        """Test tool call exception handling"""
        # Mock server that raises exception
        mock_server = Mock()
        mock_server.call_tool = AsyncMock(side_effect=Exception("Server error"))
        
        self.mcp_client.servers["test_server"] = mock_server
        
        async def test_call():
            result = await self.mcp_client.call_tool(
                "test_server", "test_tool", {}
            )
            return result
        
        result = asyncio.run(test_call())
        
        self.assertIn("error", result.lower())
    
    def test_list_tools(self):
        """Test listing available tools"""
        # Mock server tools
        mock_server = Mock()
        mock_server.list_tools = AsyncMock(return_value=[
            {"name": "tool1", "description": "Test tool 1"},
            {"name": "tool2", "description": "Test tool 2"}
        ])
        
        self.mcp_client.servers["test_server"] = mock_server
        
        async def test_list():
            result = await self.mcp_client.list_tools("test_server")
            return result
        
        result = asyncio.run(test_list())
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "tool1")
        self.assertEqual(result[1]["name"], "tool2")
    
    def test_get_server_status(self):
        """Test getting server status"""
        # Mock server status
        mock_server = Mock()
        mock_server.get_status = AsyncMock(return_value={"status": "running"})
        
        self.mcp_client.servers["test_server"] = mock_server
        
        async def test_status():
            result = await self.mcp_client.get_server_status("test_server")
            return result
        
        result = asyncio.run(test_status())
        
        self.assertEqual(result["status"], "running")

class TestSleeperServer(unittest.TestCase):
    """Test Sleeper MCP server"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = sleeper_server
    
    def test_server_initialization(self):
        """Test Sleeper server initializes correctly"""
        self.assertIsNotNone(self.server)
        self.assertEqual(self.server.name, "sleeper-server")
    
    def test_list_tools(self):
        """Test listing Sleeper tools"""
        async def test_list():
            tools = await self.server.list_tools()
            return tools
        
        tools = asyncio.run(test_list())
        
        self.assertIsInstance(tools, list)
        # Should have tools like get_league_info, get_rosters, etc.
        tool_names = [tool.name for tool in tools]
        self.assertIn("get_league_info", tool_names)
        self.assertIn("get_rosters", tool_names)
        self.assertIn("get_players", tool_names)
    
    def test_get_league_info_tool(self):
        """Test get_league_info tool"""
        tool = None
        tools = asyncio.run(self.server.list_tools())
        
        for t in tools:
            if t.name == "get_league_info":
                tool = t
                break
        
        self.assertIsNotNone(tool)
        self.assertIn("league_id", tool.inputSchema["required"])
    
    def test_get_rosters_tool(self):
        """Test get_rosters tool"""
        tool = None
        tools = asyncio.run(self.server.list_tools())
        
        for t in tools:
            if t.name == "get_rosters":
                tool = t
                break
        
        self.assertIsNotNone(tool)
        self.assertIn("league_id", tool.inputSchema["required"])
    
    def test_get_players_tool(self):
        """Test get_players tool"""
        tool = None
        tools = asyncio.run(self.server.list_tools())
        
        for t in tools:
            if t.name == "get_players":
                tool = t
                break
        
        self.assertIsNotNone(tool)
        # player_ids should be optional (can get all players)
        self.assertIn("player_ids", tool.inputSchema["properties"])

class TestFirebaseServer(unittest.TestCase):
    """Test Firebase MCP server"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = firebase_server
    
    def test_server_initialization(self):
        """Test Firebase server initializes correctly"""
        self.assertIsNotNone(self.server)
        self.assertEqual(self.server.name, "firebase-server")
    
    def test_list_tools(self):
        """Test listing Firebase tools"""
        async def test_list():
            tools = await self.server.list_tools()
            return tools
        
        tools = asyncio.run(test_list())
        
        self.assertIsInstance(tools, list)
        # Should have tools like save_data, get_data, etc.
        tool_names = [tool.name for tool in tools]
        self.assertIn("save_cpr_rankings", tool_names)
        self.assertIn("get_cpr_rankings", tool_names)
        self.assertIn("save_niv_data", tool_names)
        self.assertIn("get_niv_data", tool_names)
    
    def test_save_cpr_rankings_tool(self):
        """Test save_cpr_rankings tool"""
        tool = None
        tools = asyncio.run(self.server.list_tools())
        
        for t in tools:
            if t.name == "save_cpr_rankings":
                tool = t
                break
        
        self.assertIsNotNone(tool)
        self.assertIn("league_id", tool.inputSchema["required"])
        self.assertIn("week", tool.inputSchema["required"])
        self.assertIn("rankings", tool.inputSchema["required"])
    
    def test_get_cpr_rankings_tool(self):
        """Test get_cpr_rankings tool"""
        tool = None
        tools = asyncio.run(self.server.list_tools())
        
        for t in tools:
            if t.name == "get_cpr_rankings":
                tool = t
                break
        
        self.assertIsNotNone(tool)
        self.assertIn("league_id", tool.inputSchema["required"])
        self.assertIn("week", tool.inputSchema["required"])
    
    def test_save_niv_data_tool(self):
        """Test save_niv_data tool"""
        tool = None
        tools = asyncio.run(self.server.list_tools())
        
        for t in tools:
            if t.name == "save_niv_data":
                tool = t
                break
        
        self.assertIsNotNone(tool)
        self.assertIn("league_id", tool.inputSchema["required"])
        self.assertIn("week", tool.inputSchema["required"])
        self.assertIn("niv_data", tool.inputSchema["required"])

class TestMCPIntegration(unittest.TestCase):
    """Test MCP integration scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mcp_client = MCPClient()
    
    @patch('mcp.client.MCPClient._initialize_server')
    def test_full_server_initialization(self, mock_init):
        """Test full server initialization process"""
        mock_init.return_value = Mock()
        
        self.mcp_client.initialize_servers()
        
        # Should initialize all configured servers
        self.assertGreater(mock_init.call_count, 0)
    
    def test_cross_server_communication(self):
        """Test communication between servers"""
        # Mock both servers
        mock_sleeper = Mock()
        mock_firebase = Mock()
        
        mock_sleeper.call_tool = AsyncMock(return_value={
            "league_info": {"league_id": "test", "name": "Test League"}
        })
        
        mock_firebase.call_tool = AsyncMock(return_value={
            "saved": True, "document_id": "test_doc"
        })
        
        self.mcp_client.servers["sleeper_server"] = mock_sleeper
        self.mcp_client.servers["firebase_server"] = mock_firebase
        
        async def test_workflow():
            # Get data from Sleeper
            league_data = await self.mcp_client.call_tool(
                "sleeper_server", "get_league_info", {"league_id": "test"}
            )
            
            # Save data to Firebase
            save_result = await self.mcp_client.call_tool(
                "firebase_server", "save_league_info", 
                {"league_id": "test", "data": league_data}
            )
            
            return league_data, save_result
        
        league_data, save_result = asyncio.run(test_workflow())
        
        self.assertIn("league_info", league_data)
        self.assertTrue(save_result["saved"])
    
    def test_error_propagation(self):
        """Test error propagation across servers"""
        # Mock server that fails
        mock_server = Mock()
        mock_server.call_tool = AsyncMock(side_effect=Exception("Server unavailable"))
        
        self.mcp_client.servers["test_server"] = mock_server
        
        async def test_error():
            result = await self.mcp_client.call_tool(
                "test_server", "test_tool", {}
            )
            return result
        
        result = asyncio.run(test_error())
        
        self.assertIn("error", result.lower())
        # Should not crash the entire system
    
    def test_concurrent_tool_calls(self):
        """Test concurrent tool calls to multiple servers"""
        # Mock servers
        mock_server1 = Mock()
        mock_server2 = Mock()
        
        mock_server1.call_tool = AsyncMock(return_value={"server": "1", "result": "success"})
        mock_server2.call_tool = AsyncMock(return_value={"server": "2", "result": "success"})
        
        self.mcp_client.servers["server1"] = mock_server1
        self.mcp_client.servers["server2"] = mock_server2
        
        async def test_concurrent():
            # Make concurrent calls
            tasks = [
                self.mcp_client.call_tool("server1", "test_tool", {}),
                self.mcp_client.call_tool("server2", "test_tool", {})
            ]
            
            results = await asyncio.gather(*tasks)
            return results
        
        results = asyncio.run(test_concurrent())
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["server"], "1")
        self.assertEqual(results[1]["server"], "2")
    
    def test_tool_caching(self):
        """Test tool result caching"""
        # Mock server with consistent responses
        mock_server = Mock()
        mock_server.call_tool = AsyncMock(return_value={"cached": "result"})
        
        self.mcp_client.servers["test_server"] = mock_server
        
        async def test_caching():
            # First call
            result1 = await self.mcp_client.call_tool(
                "test_server", "test_tool", {"param": "value"}
            )
            
            # Second call with same parameters
            result2 = await self.mcp_client.call_tool(
                "test_server", "test_tool", {"param": "value"}
            )
            
            return result1, result2
        
        result1, result2 = asyncio.run(test_caching())
        
        # Results should be the same
        self.assertEqual(result1, result2)
        # Server should be called twice (unless caching is implemented)
        self.assertEqual(mock_server.call_tool.call_count, 2)

if __name__ == '__main__':
    unittest.main()
