"""MCP Client for CPR-NFL System"""
import asyncio
import json
import subprocess
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP client for tool discovery and execution"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.sessions = {}
        self.tools = {}
        self.timeout = self.config.get('timeout', 30)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 1.0)
        
        logger.info("MCP Client initialized")
    
    async def connect_server(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Connect to an MCP server"""
        try:
            logger.info(f"Connecting to MCP server: {server_name}")
            
            # For now, we'll simulate MCP connections
            # In production, this would use actual MCP protocol
            if server_name == "firebase":
                self.sessions[server_name] = FirebaseMCPSession(server_config)
            elif server_name == "sleeper":
                self.sessions[server_name] = SleeperMCPSession(server_config)
            else:
                logger.error(f"Unknown server type: {server_name}")
                return False
            
            # Get available tools
            tools = await self.sessions[server_name].list_tools()
            self.tools[server_name] = tools
            
            logger.info(f"Connected to {server_name} with {len(tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            return False
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on an MCP server"""
        if server_name not in self.sessions:
            raise ValueError(f"Server {server_name} not connected")
        
        session = self.sessions[server_name]
        
        for attempt in range(self.retry_attempts):
            try:
                result = await session.call_tool(tool_name, arguments)
                logger.debug(f"Tool {tool_name} on {server_name} returned: {type(result)}")
                return result
                
            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Tool call failed (attempt {attempt + 1}): {e}. Retrying...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Tool call failed after {self.retry_attempts} attempts: {e}")
                    raise
    
    async def list_tools(self, server_name: str = None) -> Dict[str, List[Dict]]:
        """List available tools"""
        if server_name:
            return {server_name: self.tools.get(server_name, [])}
        return self.tools.copy()
    
    async def disconnect_all(self):
        """Disconnect from all servers"""
        for server_name in list(self.sessions.keys()):
            try:
                await self.sessions[server_name].close()
                del self.sessions[server_name]
                logger.info(f"Disconnected from {server_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {server_name}: {e}")
        
        self.tools.clear()

class FirebaseMCPSession:
    """Mock Firebase MCP session"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = True
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List Firebase tools"""
        return [
            {
                "name": "firestore_get_document",
                "description": "Get a document from Firestore",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "id": {"type": "string"}
                    },
                    "required": ["collection", "id"]
                }
            },
            {
                "name": "firestore_add_document",
                "description": "Add a document to Firestore",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "data": {"type": "object"}
                    },
                    "required": ["collection", "data"]
                }
            },
            {
                "name": "firestore_update_document",
                "description": "Update a document in Firestore",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"},
                        "id": {"type": "string"},
                        "data": {"type": "object"}
                    },
                    "required": ["collection", "id", "data"]
                }
            },
            {
                "name": "firestore_list_documents",
                "description": "List documents in a collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string"}
                    },
                    "required": ["collection"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call Firebase tool"""
        # Import here to avoid circular imports
        sys.path.append('./src')
        from database import Database
        
        db = Database()
        
        if tool_name == "firestore_get_document":
            collection = arguments["collection"]
            doc_id = arguments["id"]
            
            if collection == "cpr_rankings" and doc_id == "latest":
                return db.get_cpr_rankings("1267325171853701120", latest_only=True)
            elif collection == "niv_rankings" and doc_id == "latest":
                return db.get_niv_data("1267325171853701120", latest_only=True)
            else:
                return {"error": f"Unknown collection/document: {collection}/{doc_id}"}
        
        elif tool_name == "firestore_add_document":
            collection = arguments["collection"]
            data = arguments["data"]
            
            if collection == "cpr_rankings":
                success = db.save_cpr_rankings("1267325171853701120", data)
                return {"success": success}
            elif collection == "niv_rankings":
                success = db.save_niv_data("1267325171853701120", data)
                return {"success": success}
            else:
                return {"error": f"Unknown collection: {collection}"}
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def close(self):
        """Close session"""
        self.connected = False

class SleeperMCPSession:
    """Mock Sleeper MCP session"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = True
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List Sleeper tools"""
        return [
            {
                "name": "get_league_info",
                "description": "Get league information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"}
                    },
                    "required": ["league_id"]
                }
            },
            {
                "name": "get_team_rosters",
                "description": "Get team rosters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "league_id": {"type": "string"}
                    },
                    "required": ["league_id"]
                }
            },
            {
                "name": "get_player_data",
                "description": "Get player information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "player_ids": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["player_ids"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call Sleeper tool"""
        # Import here to avoid circular imports
        sys.path.append('./src')
        from api import SleeperAPI
        
        league_id = arguments.get("league_id", "1267325171853701120")
        api = SleeperAPI(league_id)
        
        if tool_name == "get_league_info":
            league_info = api.get_league_info()
            return {
                "name": league_info.name,
                "season": league_info.season,
                "current_week": league_info.current_week,
                "num_teams": league_info.num_teams,
                "status": league_info.status
            }
        
        elif tool_name == "get_team_rosters":
            teams = api.get_rosters()
            return [
                {
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "owner_name": team.owner_name,
                    "wins": team.wins,
                    "losses": team.losses,
                    "roster_size": len(team.roster)
                }
                for team in teams
            ]
        
        elif tool_name == "get_player_data":
            player_ids = arguments.get("player_ids", [])
            players = api.get_players(player_ids)
            
            return [
                {
                    "player_id": player_id,
                    "name": player.name,
                    "position": player.position.value,
                    "team": player.team,
                    "status": player.status,
                    "injury_status": player.injury_status.value
                }
                for player_id, player in players.items()
            ]
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def close(self):
        """Close session"""
        self.connected = False

# Factory function
async def create_mcp_client(config: Dict[str, Any] = None) -> MCPClient:
    """Create and configure MCP client"""
    client = MCPClient(config)
    
    # Connect to default servers
    servers = {
        "firebase": {
            "command": "npx",
            "args": ["-y", "@gannonh/firebase-mcp"],
            "env": {
                "SERVICE_ACCOUNT_KEY_PATH": "./firebase-credentials.json"
            }
        },
        "sleeper": {
            "command": "python",
            "args": ["mcp/sleeper_server.py"],
            "env": {
                "SLEEPER_LEAGUE_ID": "1267325171853701120"
            }
        }
    }
    
    for server_name, server_config in servers.items():
        await client.connect_server(server_name, server_config)
    
    return client
