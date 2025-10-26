#!/usr/bin/env python3
"""Firebase MCP Server - Provides Firebase database tools via MCP"""
import asyncio
import json
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, GetResourceRequest, GetResourceResult
)

from database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
database = Database()

# Create MCP server
server = Server("firebase-server")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available Firebase database tools"""
    return [
        Tool(
            name="get_cpr_rankings",
            description="Get CPR (Commissioner's Power Rankings) for a league",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "week": {
                        "type": "integer",
                        "description": "Specific week to get rankings for",
                        "default": None
                    },
                    "latest_only": {
                        "type": "boolean",
                        "description": "Only return the most recent rankings",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="save_cpr_rankings",
            description="Save CPR rankings to Firebase database",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "week": {
                        "type": "integer",
                        "description": "Week number",
                        "default": None
                    },
                    "rankings": {
                        "type": "array",
                        "description": "Array of team rankings with CPR metrics",
                        "items": {
                            "type": "object",
                            "properties": {
                                "team_id": {"type": "string"},
                                "team_name": {"type": "string"},
                                "rank": {"type": "integer"},
                                "cpr_score": {"type": "number"},
                                "sli": {"type": "number"},
                                "bsi": {"type": "number"},
                                "smi": {"type": "number"},
                                "ingram_index": {"type": "number"},
                                "alvarado_index": {"type": "number"},
                                "zion_index": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["rankings"]
            }
        ),
        Tool(
            name="get_niv_data",
            description="Get NIV (Normalized Impact Value) data for players",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "player_id": {
                        "type": "string",
                        "description": "Specific player ID to get NIV for"
                    },
                    "position": {
                        "type": "string",
                        "description": "Filter by position",
                        "enum": ["QB", "RB", "WR", "TE", "K", "DEF"]
                    },
                    "week": {
                        "type": "integer",
                        "description": "Specific week to get NIV for"
                    }
                }
            }
        ),
        Tool(
            name="save_niv_data",
            description="Save NIV calculations to Firebase database",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "week": {
                        "type": "integer",
                        "description": "Week number",
                        "default": None
                    },
                    "niv_data": {
                        "type": "array",
                        "description": "Array of player NIV data",
                        "items": {
                            "type": "object",
                            "properties": {
                                "player_id": {"type": "string"},
                                "overall_niv": {"type": "number"},
                                "positional_niv": {"type": "number"},
                                "recent_performance": {"type": "number"},
                                "consistency_score": {"type": "number"},
                                "upside_score": {"type": "number"},
                                "schedule_adjustment": {"type": "number"},
                                "injury_risk": {"type": "number"}
                            }
                        }
                    }
                },
                "required": ["niv_data"]
            }
        ),
        Tool(
            name="get_league_history",
            description="Get historical data for a league",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year",
                        "default": None
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Type of historical data",
                        "enum": ["rankings", "champions", "trade_history", "waiver_history"],
                        "default": "rankings"
                    }
                }
            }
        ),
        Tool(
            name="save_league_event",
            description="Save league events (trades, waivers, championships) to database",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Type of event",
                        "enum": ["trade", "waiver_claim", "championship", "draft"],
                        "default": "trade"
                    },
                    "event_data": {
                        "type": "object",
                        "description": "Event-specific data",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "teams_involved": {"type": "array"},
                            "players_moved": {"type": "array"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "required": ["event_type", "event_data"]
            }
        ),
        Tool(
            name="get_analytics_data",
            description="Get analytics data for reports and insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "analytics_type": {
                        "type": "string",
                        "description": "Type of analytics",
                        "enum": ["season_trends", "team_performance", "player_value", "trade_analysis"],
                        "default": "season_trends"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Timeframe for analytics",
                        "enum": ["season", "last_4_weeks", "last_8_weeks", "playoffs"],
                        "default": "season"
                    }
                }
            }
        ),
        Tool(
            name="backup_data",
            description="Create backup of league data",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "League ID",
                        "default": "1267325171853701120"
                    },
                    "data_types": {
                        "type": "array",
                        "description": "Types of data to backup",
                        "items": {
                            "type": "string",
                            "enum": ["cpr_rankings", "niv_data", "league_events", "analytics"]
                        },
                        "default": ["cpr_rankings", "niv_data"]
                    },
                    "backup_name": {
                        "type": "string",
                        "description": "Custom backup name",
                        "default": None
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls for Firebase database"""
    
    try:
        if name == "get_cpr_rankings":
            league_id = arguments.get("league_id", "1267325171853701120")
            week = arguments.get("week")
            latest_only = arguments.get("latest_only", True)
            
            cpr_data = database.get_cpr_rankings(league_id, week, latest_only)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(cpr_data, indent=2)
                )]
            )
        
        elif name == "save_cpr_rankings":
            league_id = arguments.get("league_id", "1267325171853701120")
            week = arguments.get("week", datetime.now().isocalendar()[1])
            rankings = arguments["rankings"]
            
            # Add metadata
            cpr_document = {
                "league_id": league_id,
                "week": week,
                "rankings": rankings,
                "calculated_at": datetime.now().isoformat(),
                "calculated_by": "cpr-nfl-system"
            }
            
            success = database.save_cpr_rankings(league_id, week, cpr_document)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": success,
                        "message": f"CPR rankings saved for week {week}" if success else "Failed to save CPR rankings",
                        "league_id": league_id,
                        "week": week,
                        "teams_saved": len(rankings)
                    }, indent=2)
                )]
            )
        
        elif name == "get_niv_data":
            league_id = arguments.get("league_id", "1267325171853701120")
            player_id = arguments.get("player_id")
            position = arguments.get("position")
            week = arguments.get("week")
            
            niv_data = database.get_niv_data(league_id, player_id, position, week)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(niv_data, indent=2)
                )]
            )
        
        elif name == "save_niv_data":
            league_id = arguments.get("league_id", "1267325171853701120")
            week = arguments.get("week", datetime.now().isocalendar()[1])
            niv_data = arguments["niv_data"]
            
            # Add metadata
            niv_document = {
                "league_id": league_id,
                "week": week,
                "niv_data": niv_data,
                "calculated_at": datetime.now().isoformat(),
                "calculated_by": "cpr-nfl-system"
            }
            
            success = database.save_niv_data(league_id, week, niv_document)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": success,
                        "message": f"NIV data saved for week {week}" if success else "Failed to save NIV data",
                        "league_id": league_id,
                        "week": week,
                        "players_saved": len(niv_data)
                    }, indent=2)
                )]
            )
        
        elif name == "get_league_history":
            league_id = arguments.get("league_id", "1267325171853701120")
            season = arguments.get("season")
            data_type = arguments.get("data_type", "rankings")
            
            history_data = database.get_league_history(league_id, season, data_type)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(history_data, indent=2)
                )]
            )
        
        elif name == "save_league_event":
            league_id = arguments.get("league_id", "1267325171853701120")
            event_type = arguments["event_type"]
            event_data = arguments["event_data"]
            
            # Add metadata
            event_document = {
                "league_id": league_id,
                "event_type": event_type,
                "event_data": event_data,
                "timestamp": datetime.now().isoformat(),
                "recorded_by": "cpr-nfl-system"
            }
            
            success = database.save_league_event(league_id, event_document)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": success,
                        "message": f"{event_type} event saved" if success else "Failed to save event",
                        "event_id": event_document.get("timestamp"),
                        "league_id": league_id
                    }, indent=2)
                )]
            )
        
        elif name == "get_analytics_data":
            league_id = arguments.get("league_id", "1267325171853701120")
            analytics_type = arguments.get("analytics_type", "season_trends")
            timeframe = arguments.get("timeframe", "season")
            
            analytics_data = database.get_analytics_data(league_id, analytics_type, timeframe)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(analytics_data, indent=2)
                )]
            )
        
        elif name == "backup_data":
            league_id = arguments.get("league_id", "1267325171853701120")
            data_types = arguments.get("data_types", ["cpr_rankings", "niv_data"])
            backup_name = arguments.get("backup_name")
            
            if not backup_name:
                backup_name = f"backup_{league_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_data = {}
            for data_type in data_types:
                if data_type == "cpr_rankings":
                    backup_data["cpr_rankings"] = database.get_cpr_rankings(league_id, latest_only=False)
                elif data_type == "niv_data":
                    backup_data["niv_data"] = database.get_niv_data(league_id)
                elif data_type == "league_events":
                    backup_data["league_events"] = database.get_league_history(league_id)
                elif data_type == "analytics":
                    backup_data["analytics"] = database.get_analytics_data(league_id)
            
            # Save backup
            backup_document = {
                "backup_name": backup_name,
                "league_id": league_id,
                "data_types": data_types,
                "backup_data": backup_data,
                "created_at": datetime.now().isoformat(),
                "created_by": "cpr-nfl-system"
            }
            
            success = database.create_backup(league_id, backup_name, backup_document)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": success,
                        "message": f"Backup '{backup_name}' created" if success else "Failed to create backup",
                        "backup_name": backup_name,
                        "league_id": league_id,
                        "data_types": data_types,
                        "size_estimate": len(str(backup_data))
                    }, indent=2)
                )]
            )
        
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )],
                isError=True
            )
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}"
            )],
            isError=True
        )

async def main():
    """Main entry point for Firebase MCP server"""
    logger.info("🔥 Starting Firebase MCP Server...")
    
    # Run the server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="firebase-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
