#!/usr/bin/env python3
"""Sleeper MCP Server - Provides Sleeper API tools via MCP"""
import asyncio
import json
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
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

from api import SleeperAPI
from models import LeagueInfo, Team, Player, PlayerStats, Matchup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sleeper API
sleeper_api = SleeperAPI("1267325171853701120")

# Create MCP server
server = Server("sleeper-server")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available Sleeper API tools"""
    return [
        Tool(
            name="get_league_info",
            description="Get basic league information including name, season, current week, and number of teams",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "Sleeper league ID (defaults to your league)",
                        "default": "1267325171853701120"
                    }
                }
            }
        ),
        Tool(
            name="get_league_teams",
            description="Get all teams in the league with rosters, records, and owner information",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "Sleeper league ID",
                        "default": "1267325171853701120"
                    },
                    "include_rosters": {
                        "type": "boolean",
                        "description": "Include full roster information",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="get_weekly_matchups",
            description="Get matchups for a specific week",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "Sleeper league ID",
                        "default": "1267325171853701120"
                    },
                    "week": {
                        "type": "integer",
                        "description": "Week number (defaults to current week)",
                        "default": None
                    }
                }
            }
        ),
        Tool(
            name="get_player_stats",
            description="Get player statistics for specific week(s)",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "string",
                        "description": "Sleeper player ID"
                    },
                    "weeks": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of weeks to get stats for",
                        "default": []
                    },
                    "season": {
                        "type": "integer",
                        "description": "Season year",
                        "default": 2025
                    }
                },
                "required": ["player_id"]
            }
        ),
        Tool(
            name="search_players",
            description="Search for players by name or position",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Player name or partial name to search for"
                    },
                    "position": {
                        "type": "string",
                        "description": "Filter by position (QB, RB, WR, TE, K, DEF)",
                        "enum": ["QB", "RB", "WR", "TE", "K", "DEF"]
                    },
                    "team": {
                        "type": "string",
                        "description": "Filter by NFL team abbreviation"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 25
                    }
                }
            }
        ),
        Tool(
            name="get_league_standings",
            description="Get current league standings with points for/against and playoff implications",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "Sleeper league ID",
                        "default": "1267325171853701120"
                    }
                }
            }
        ),
        Tool(
            name="get_transactions",
            description="Get recent league transactions (waivers, trades, free agent pickups)",
            inputSchema={
                "type": "object",
                "properties": {
                    "league_id": {
                        "type": "string",
                        "description": "Sleeper league ID",
                        "default": "1267325171853701120"
                    },
                    "week": {
                        "type": "integer",
                        "description": "Get transactions for specific week (default: recent)",
                        "default": None
                    },
                    "transaction_type": {
                        "type": "string",
                        "description": "Filter by transaction type",
                        "enum": ["waiver", "free_agent", "trade"],
                        "default": None
                    }
                }
            }
        ),
        Tool(
            name="get_player_news",
            description="Get recent news and injury updates for players",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "string",
                        "description": "Sleeper player ID"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back for news",
                        "default": 7
                    }
                },
                "required": ["player_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls for Sleeper API"""
    
    try:
        if name == "get_league_info":
            league_id = arguments.get("league_id", "1267325171853701120")
            league_info = sleeper_api.get_league_info(league_id)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "league_id": league_info.league_id,
                        "name": league_info.name,
                        "season": league_info.season,
                        "current_week": league_info.current_week,
                        "num_teams": league_info.num_teams,
                        "status": league_info.status,
                        "playoff_teams": league_info.playoff_teams,
                        "playoff_start_week": league_info.playoff_start_week
                    }, indent=2)
                )]
            )
        
        elif name == "get_league_teams":
            league_id = arguments.get("league_id", "1267325171853701120")
            include_rosters = arguments.get("include_rosters", True)
            
            teams = sleeper_api.get_rosters(league_id)
            
            result_data = []
            for team in teams:
                team_data = {
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "owner_name": team.owner_name,
                    "owner_id": team.owner_id,
                    "wins": team.wins,
                    "losses": team.losses,
                    "ties": team.ties,
                    "points_for": team.points_for,
                    "points_against": team.points_against,
                    "waiver_priority": team.waiver_priority,
                    "total_moves": team.total_moves
                }
                
                if include_rosters and team.roster:
                    team_data["roster"] = [
                        {
                            "player_id": player.player_id,
                            "name": player.name,
                            "position": player.position.value,
                            "team": player.team,
                            "status": player.status,
                            "injury_status": player.injury_status.value if player.injury_status else "HEALTHY"
                        }
                        for player in team.roster
                    ]
                
                result_data.append(team_data)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(result_data, indent=2)
                )]
            )
        
        elif name == "get_weekly_matchups":
            league_id = arguments.get("league_id", "1267325171853701120")
            week = arguments.get("week")
            
            matchups = sleeper_api.get_matchups(league_id, week)
            
            result_data = []
            for matchup in matchups:
                matchup_data = {
                    "matchup_id": matchup.matchup_id,
                    "week": matchup.week,
                    "home_team": {
                        "team_id": matchup.home_team.team_id,
                        "team_name": matchup.home_team.team_name,
                        "points": matchup.home_points
                    },
                    "away_team": {
                        "team_id": matchup.away_team.team_id,
                        "team_name": matchup.away_team.team_name,
                        "points": matchup.away_points
                    },
                    "winner": matchup.winner,
                    "is_playoff": matchup.is_playoff
                }
                result_data.append(matchup_data)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(result_data, indent=2)
                )]
            )
        
        elif name == "get_player_stats":
            player_id = arguments["player_id"]
            weeks = arguments.get("weeks", [])
            season = arguments.get("season", 2025)
            
            if not weeks:
                # Default to recent 4 weeks
                league_info = sleeper_api.get_league_info()
                current_week = league_info.current_week
                weeks = list(range(max(1, current_week - 3), current_week + 1))
            
            stats = {}
            for week in weeks:
                week_stats = sleeper_api.get_player_stats(player_id, week, season)
                if week_stats:
                    stats[f"week_{week}"] = {
                        "pass_yards": week_stats.pass_yards,
                        "pass_tds": week_stats.pass_tds,
                        "pass_ints": week_stats.pass_ints,
                        "rush_yards": week_stats.rush_yards,
                        "rush_tds": week_stats.rush_tds,
                        "receptions": week_stats.receptions,
                        "rec_yards": week_stats.rec_yards,
                        "rec_tds": week_stats.rec_tds,
                        "fumbles": week_stats.fumbles
                    }
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(stats, indent=2)
                )]
            )
        
        elif name == "search_players":
            search_term = arguments.get("search_term", "")
            position = arguments.get("position")
            team = arguments.get("team")
            limit = arguments.get("limit", 25)
            
            # Use Sleeper API to search players
            all_players = sleeper_api.get_all_players()
            
            results = []
            for player_id, player_data in all_players.items():
                # Apply filters
                if search_term and search_term.lower() not in player_data.get("full_name", "").lower():
                    continue
                
                if position and player_data.get("position") != position:
                    continue
                
                if team and player_data.get("team") != team:
                    continue
                
                results.append({
                    "player_id": player_id,
                    "name": player_data.get("full_name"),
                    "position": player_data.get("position"),
                    "team": player_data.get("team"),
                    "status": player_data.get("status"),
                    "injury_status": player_data.get("injury_status")
                })
                
                if len(results) >= limit:
                    break
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(results, indent=2)
                )]
            )
        
        elif name == "get_league_standings":
            league_id = arguments.get("league_id", "1267325171853701120")
            
            teams = sleeper_api.get_rosters(league_id)
            
            # Sort by wins, then points for
            sorted_teams = sorted(teams, key=lambda t: (t.wins, t.points_for), reverse=True)
            
            standings = []
            for rank, team in enumerate(sorted_teams, 1):
                standings.append({
                    "rank": rank,
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "owner_name": team.owner_name,
                    "record": f"{team.wins}-{team.losses}-{team.ties}",
                    "points_for": team.points_for,
                    "points_against": team.points_against,
                    "point_difference": team.points_for - team.points_against,
                    "waiver_priority": team.waiver_priority,
                    "playoff_seed": team.playoff_seed if hasattr(team, 'playoff_seed') else None
                })
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(standings, indent=2)
                )]
            )
        
        elif name == "get_transactions":
            league_id = arguments.get("league_id", "1267325171853701120")
            week = arguments.get("week")
            transaction_type = arguments.get("transaction_type")
            
            transactions = sleeper_api.get_transactions(league_id, week)
            
            # Filter by transaction type if specified
            if transaction_type:
                transactions = [t for t in transactions if t.get("type") == transaction_type]
            
            result_data = []
            for transaction in transactions:
                result_data.append({
                    "transaction_id": transaction.get("transaction_id"),
                    "type": transaction.get("type"),
                    "status": transaction.get("status"),
                    "timestamp": transaction.get("timestamp"),
                    "roster_id": transaction.get("roster_id"),
                    "adds": transaction.get("adds", {}),
                    "drops": transaction.get("drops", {}),
                    "waiver_bid": transaction.get("waiver_bid")
                })
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(result_data, indent=2)
                )]
            )
        
        elif name == "get_player_news":
            player_id = arguments["player_id"]
            days_back = arguments.get("days_back", 7)
            
            # This would integrate with a news API
            # For now, return basic player info
            all_players = sleeper_api.get_all_players()
            player_data = all_players.get(player_id, {})
            
            news_data = {
                "player_id": player_id,
                "name": player_data.get("full_name"),
                "position": player_data.get("position"),
                "team": player_data.get("team"),
                "status": player_data.get("status"),
                "injury_status": player_data.get("injury_status"),
                "news": "News integration would be implemented here"
            }
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(news_data, indent=2)
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
    """Main entry point for Sleeper MCP server"""
    logger.info("🏈 Starting Sleeper MCP Server...")
    
    # Run the server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sleever-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
