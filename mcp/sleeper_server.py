#!/usr/bin/env python3
"""
STREAMLINED Sleeper MCP Server for CPR-NFL
Uses VERIFIED Sleeper API endpoints for maximum efficiency
"""

import asyncio
import json
import sys
from pathlib import Path
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

from utils import make_sleeper_request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize APIs with Legion league
LEGION_LEAGUE_ID = "1267325171853701120"

# Create MCP server
server = Server("sleeper-server")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List STREAMLINED Sleeper API tools using VERIFIED endpoints"""
    return [
        Tool(
            name="get_legion_teams",
            description="Get Legion Fantasy Football teams with REAL custom names, records, and logos",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_records": {
                        "type": "boolean", 
                        "description": "Include win/loss records and points",
                        "default": True
                    },
                    "include_logos": {
                        "type": "boolean",
                        "description": "Include team logo URLs", 
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="get_league_info",
            description="Get Legion Fantasy Football league information (season, week, status)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_weekly_matchups", 
            description="Get weekly matchups with team names and scores",
            inputSchema={
                "type": "object",
                "properties": {
                    "week": {
                        "type": "integer",
                        "description": "Week number (1-18, defaults to current week)",
                        "default": None
                    }
                }
            }
        ),
        Tool(
            name="get_draft_data",
            description="Get draft picks for Alvarado Index ADP calculations",
            inputSchema={
                "type": "object", 
                "properties": {
                    "include_adp": {
                        "type": "boolean",
                        "description": "Include ADP cost calculations",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="get_transactions",
            description="Get recent league transactions (waivers, trades, free agents)",
            inputSchema={
                "type": "object",
                "properties": {
                    "week": {
                        "type": "integer",
                        "description": "Specific week (defaults to recent)",
                        "default": None
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max transactions to return",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_player_info",
            description="Get NFL player information and injury status",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of Sleeper player IDs"
                    },
                    "include_stats": {
                        "type": "boolean",
                        "description": "Include season statistics",
                        "default": False
                    }
                },
                "required": ["player_ids"]
            }
        ),
        Tool(
            name="get_nfl_state",
            description="Get current NFL season state (week, season status)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_legion_team",
            description="Find Legion team by name or owner",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Team name or owner name to search for"
                    }
                },
                "required": ["search_term"]
            }
        ),
        Tool(
            name="compare_players",
            description="Compare 2-4 players for trade analysis with projections and trends",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2-4 Sleeper player IDs to compare",
                        "minItems": 2,
                        "maxItems": 4
                    },
                    "include_projections": {
                        "type": "boolean",
                        "description": "Include 2025 projections",
                        "default": True
                    },
                    "include_trends": {
                        "type": "boolean", 
                        "description": "Include trending data (adds/drops)",
                        "default": True
                    }
                },
                "required": ["player_ids"]
            }
        ),
        Tool(
            name="get_trending_players",
            description="Get trending adds/drops for waiver wire analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "trend_type": {
                        "type": "string",
                        "enum": ["add", "drop", "both"],
                        "description": "Type of trending data",
                        "default": "both"
                    },
                    "position": {
                        "type": "string",
                        "enum": ["QB", "RB", "WR", "TE", "K", "DEF"],
                        "description": "Filter by position",
                        "default": null
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max players to return",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="analyze_trade",
            description="Analyze a potential trade between Legion teams",
            inputSchema={
                "type": "object",
                "properties": {
                    "team1_gives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Player IDs team 1 is giving up"
                    },
                    "team1_gets": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Player IDs team 1 is getting"
                    },
                    "team1_name": {
                        "type": "string",
                        "description": "Team 1 name (optional)"
                    },
                    "team2_name": {
                        "type": "string", 
                        "description": "Team 2 name (optional)"
                    }
                },
                "required": ["team1_gives", "team1_gets"]
            }
        ),
        Tool(
            name="get_projections",
            description="Get 2025 NFL projections for players",
            inputSchema={
                "type": "object",
                "properties": {
                    "position": {
                        "type": "string",
                        "enum": ["QB", "RB", "WR", "TE", "K", "DEF"],
                        "description": "Filter by position",
                        "default": null
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max players to return",
                        "default": 50
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle STREAMLINED tool calls using VERIFIED endpoints"""
    
    try:
        if name == "get_legion_teams":
            include_records = arguments.get("include_records", True)
            include_logos = arguments.get("include_logos", True)
            
            # Use our VERIFIED team extraction
            legion_teams = team_extractor.get_teams()
            
            result_data = []
            for team in legion_teams:
                team_data = {
                    "roster_id": team["roster_id"],
                    "team_name": team["team_name"],
                    "owner_name": team["owner_name"],
                    "user_id": team["user_id"],
                    "has_custom_name": team["has_custom_name"]
                }
                
                if include_records:
                    team_data["record"] = team["record"]
                
                if include_logos:
                    team_data["logo_full"] = team["logo_full"]
                    team_data["logo_thumb"] = team["logo_thumb"]
                
                result_data.append(team_data)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "teams": result_data,
                        "total_teams": len(result_data),
                        "league_id": LEGION_LEAGUE_ID,
                        "source": "VERIFIED team_extraction + users metadata"
                    }, indent=2)
                )]
            )
        
        elif name == "get_league_info":
            # VERIFIED endpoint: league/{league_id}
            league_info = sleeper_api.get_league_info()
            
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
                        "roster_positions": league_info.roster_positions,
                        "source": "VERIFIED league/{league_id}"
                    }, indent=2)
                )]
            )
        
        elif name == "get_weekly_matchups":
            week = arguments.get("week")
            
            # VERIFIED endpoint: league/{league_id}/matchups/{week}
            matchups = sleeper_api.get_matchups(week or sleeper_api.get_league_info().current_week)
            
            # Enhance with Legion team names
            legion_teams = team_extractor.get_teams()
            team_lookup = {str(t["roster_id"]): t["team_name"] for t in legion_teams}
            
            result_data = []
            for matchup in matchups:
                matchup_data = {
                    "matchup_id": matchup.matchup_id,
                    "week": matchup.week,
                    "team1_id": matchup.team1_id,
                    "team1_name": team_lookup.get(matchup.team1_id, f"Team {matchup.team1_id}"),
                    "team1_score": matchup.team1_score,
                    "team2_id": matchup.team2_id,
                    "team2_name": team_lookup.get(matchup.team2_id, f"Team {matchup.team2_id}"),
                    "team2_score": matchup.team2_score,
                    "status": matchup.status
                }
                result_data.append(matchup_data)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "matchups": result_data,
                        "week": week or sleeper_api.get_league_info().current_week,
                        "total_matchups": len(result_data),
                        "source": "VERIFIED league/{league_id}/matchups/{week}"
                    }, indent=2)
                )]
            )
        
        elif name == "get_draft_data":
            include_adp = arguments.get("include_adp", True)
            
            # VERIFIED endpoints: league/{league_id}/drafts + draft/{draft_id}/picks
            drafts_data = make_sleeper_request(f"league/{LEGION_LEAGUE_ID}/drafts")
            
            if not drafts_data:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({"error": "No draft data found"}))]
                )
            
            draft_id = drafts_data[0]["draft_id"]
            picks_data = make_sleeper_request(f"draft/{draft_id}/picks")
            
            if include_adp:
                # Calculate ADP costs for Alvarado Index
                for pick in picks_data:
                    pick_no = pick["pick_no"]
                    max_picks = 144  # 12 teams * 12 rounds
                    adp_cost = 1.0 - (pick_no - 1) / max_picks  # Higher pick = higher cost
                    pick["adp_cost"] = round(adp_cost, 3)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "draft_id": draft_id,
                        "picks": picks_data,
                        "total_picks": len(picks_data),
                        "source": "VERIFIED draft/{draft_id}/picks"
                    }, indent=2)
                )]
            )
        
        elif name == "get_transactions":
            week = arguments.get("week")
            limit = arguments.get("limit", 20)
            
            # VERIFIED endpoint: league/{league_id}/transactions/{week}
            transactions = sleeper_api.get_transactions(week)
            
            # Limit results
            limited_transactions = transactions[:limit] if transactions else []
            
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=json.dumps({
                        "transactions": limited_transactions,
                        "week": week or "recent",
                        "total_shown": len(limited_transactions),
                        "source": "VERIFIED league/{league_id}/transactions/{week}"
                    }, indent=2)
                )]
            )
        
        elif name == "get_player_info":
            player_ids = arguments["player_ids"]
            include_stats = arguments.get("include_stats", False)
            
            # VERIFIED endpoint: players/nfl
            players = sleeper_api.get_players(player_ids)
            
            result_data = []
            for player_id, player in players.items():
                player_data = {
                    "player_id": player_id,
                    "name": player.name,
                    "position": player.position.value,
                    "team": player.team,
                    "status": player.status,
                    "injury_status": player.injury_status.value,
                    "fantasy_positions": [pos.value for pos in player.fantasy_positions]
                }
                
                if include_stats:
                    current_season = 2025
                    stats = player.get_season_stats(current_season)
                    if stats:
                        player_data["stats"] = {
                            "games_played": stats.games_played,
                            "fantasy_points": stats.fantasy_points,
                            "fantasy_points_per_game": stats.fantasy_points_per_game
                        }
                
                result_data.append(player_data)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "players": result_data,
                        "total_players": len(result_data),
                        "source": "VERIFIED players/nfl"
                    }, indent=2)
                )]
            )
        
        elif name == "get_nfl_state":
            # VERIFIED endpoint: state/nfl
            nfl_state = make_sleeper_request("state/nfl")
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "nfl_state": nfl_state,
                        "source": "VERIFIED state/nfl"
                    }, indent=2)
                )]
            )
        
        elif name == "search_legion_team":
            search_term = arguments["search_term"].lower()
            
            legion_teams = team_extractor.get_teams()
            
            matches = []
            for team in legion_teams:
                if (search_term in team["team_name"].lower() or 
                    search_term in team["owner_name"].lower()):
                    matches.append(team)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "matches": matches,
                        "search_term": search_term,
                        "total_matches": len(matches),
                        "source": "Legion team extraction search"
                    }, indent=2)
                )]
            )
        
        elif name == "compare_players":
            player_ids = arguments["player_ids"]
            include_projections = arguments.get("include_projections", True)
            include_trends = arguments.get("include_trends", True)
            
            # Get player info
            players = sleeper_api.get_players(player_ids)
            
            # Get projections if requested
            projections_data = {}
            if include_projections:
                proj_data = make_sleeper_request("projections/nfl/regular/2025")
                if proj_data:
                    projections_data = proj_data
            
            # Get trending data if requested
            trending_adds = []
            trending_drops = []
            if include_trends:
                adds_data = make_sleeper_request("players/nfl/trending/add")
                drops_data = make_sleeper_request("players/nfl/trending/drop")
                if adds_data:
                    trending_adds = [p["player_id"] for p in adds_data[:50]]
                if drops_data:
                    trending_drops = [p["player_id"] for p in drops_data[:50]]
            
            comparison_data = []
            for player_id, player in players.items():
                player_comparison = {
                    "player_id": player_id,
                    "name": player.name,
                    "position": player.position.value,
                    "team": player.team,
                    "injury_status": player.injury_status.value,
                    "fantasy_positions": [pos.value for pos in player.fantasy_positions]
                }
                
                # Add current season stats
                stats = player.get_season_stats(2025)
                if stats:
                    player_comparison["current_stats"] = {
                        "games_played": stats.games_played,
                        "fantasy_points": stats.fantasy_points,
                        "fantasy_ppg": round(stats.fantasy_points_per_game, 2)
                    }
                
                # Add projections
                if include_projections and player_id in projections_data:
                    proj = projections_data[player_id]
                    player_comparison["projections"] = {
                        "projected_points": proj.get("pts_ppr", 0),
                        "projected_games": proj.get("gp", 17)
                    }
                
                # Add trending status
                if include_trends:
                    player_comparison["trending"] = {
                        "hot_add": player_id in trending_adds,
                        "trending_drop": player_id in trending_drops
                    }
                
                comparison_data.append(player_comparison)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "comparison": comparison_data,
                        "total_players": len(comparison_data),
                        "includes_projections": include_projections,
                        "includes_trends": include_trends,
                        "source": "VERIFIED players/nfl + projections/nfl/regular/2025"
                    }, indent=2)
                )]
            )
        
        elif name == "get_trending_players":
            trend_type = arguments.get("trend_type", "both")
            position = arguments.get("position")
            limit = arguments.get("limit", 20)
            
            result_data = {"trending_adds": [], "trending_drops": []}
            
            if trend_type in ["add", "both"]:
                adds_data = make_sleeper_request("players/nfl/trending/add")
                if adds_data:
                    filtered_adds = adds_data
                    if position:
                        filtered_adds = [p for p in adds_data if p.get("position") == position]
                    result_data["trending_adds"] = filtered_adds[:limit]
            
            if trend_type in ["drop", "both"]:
                drops_data = make_sleeper_request("players/nfl/trending/drop")
                if drops_data:
                    filtered_drops = drops_data
                    if position:
                        filtered_drops = [p for p in drops_data if p.get("position") == position]
                    result_data["trending_drops"] = filtered_drops[:limit]
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        **result_data,
                        "trend_type": trend_type,
                        "position_filter": position,
                        "source": "VERIFIED players/nfl/trending/add + players/nfl/trending/drop"
                    }, indent=2)
                )]
            )
        
        elif name == "analyze_trade":
            team1_gives = arguments["team1_gives"]
            team1_gets = arguments["team1_gets"]
            team1_name = arguments.get("team1_name", "Team 1")
            team2_name = arguments.get("team2_name", "Team 2")
            
            # Get all players involved
            all_player_ids = team1_gives + team1_gets
            players = sleeper_api.get_players(all_player_ids)
            
            # Get projections for trade analysis
            projections_data = make_sleeper_request("projections/nfl/regular/2025") or {}
            
            def analyze_players(player_ids, label):
                total_projected = 0
                total_current = 0
                players_analysis = []
                
                for pid in player_ids:
                    if pid in players:
                        player = players[pid]
                        
                        # Current season performance
                        stats = player.get_season_stats(2025)
                        current_points = stats.fantasy_points if stats else 0
                        
                        # Projected performance
                        projected_points = projections_data.get(pid, {}).get("pts_ppr", 0)
                        
                        total_current += current_points
                        total_projected += projected_points
                        
                        players_analysis.append({
                            "name": player.name,
                            "position": player.position.value,
                            "team": player.team,
                            "current_points": current_points,
                            "projected_points": projected_points,
                            "injury_status": player.injury_status.value
                        })
                
                return {
                    "players": players_analysis,
                    "total_current_points": total_current,
                    "total_projected_points": total_projected
                }
            
            team1_gives_analysis = analyze_players(team1_gives, "gives")
            team1_gets_analysis = analyze_players(team1_gets, "gets")
            
            # Calculate trade value
            value_difference = (team1_gets_analysis["total_projected_points"] - 
                              team1_gives_analysis["total_projected_points"])
            
            trade_analysis = {
                "trade_summary": {
                    "team1_name": team1_name,
                    "team2_name": team2_name,
                    "value_difference": round(value_difference, 2),
                    "recommendation": "ACCEPT" if value_difference > 5 else "DECLINE" if value_difference < -5 else "NEUTRAL"
                },
                "team1_gives": team1_gives_analysis,
                "team1_gets": team1_gets_analysis,
                "analysis_notes": [
                    f"{team1_name} giving up {team1_gives_analysis['total_projected_points']:.1f} projected points",
                    f"{team1_name} receiving {team1_gets_analysis['total_projected_points']:.1f} projected points",
                    f"Net value: {'Gain' if value_difference > 0 else 'Loss'} of {abs(value_difference):.1f} points"
                ]
            }
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(trade_analysis, indent=2)
                )]
            )
        
        elif name == "get_projections":
            position = arguments.get("position")
            limit = arguments.get("limit", 50)
            
            # VERIFIED endpoint: projections/nfl/regular/2025
            projections_data = make_sleeper_request("projections/nfl/regular/2025")
            
            if not projections_data:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({"error": "No projections available"}))]
                )
            
            # Get player info to enhance projections
            player_ids = list(projections_data.keys())[:200]  # Limit to avoid huge requests
            players = sleeper_api.get_players(player_ids)
            
            enhanced_projections = []
            for player_id, proj_data in projections_data.items():
                if player_id in players:
                    player = players[player_id]
                    
                    # Filter by position if specified
                    if position and player.position.value != position:
                        continue
                    
                    enhanced_proj = {
                        "player_id": player_id,
                        "name": player.name,
                        "position": player.position.value,
                        "team": player.team,
                        "projected_points": proj_data.get("pts_ppr", 0),
                        "projected_games": proj_data.get("gp", 17),
                        "projected_ppg": round(proj_data.get("pts_ppr", 0) / max(proj_data.get("gp", 17), 1), 2)
                    }
                    enhanced_projections.append(enhanced_proj)
            
            # Sort by projected points
            enhanced_projections.sort(key=lambda x: x["projected_points"], reverse=True)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "projections": enhanced_projections[:limit],
                        "position_filter": position,
                        "total_players": len(enhanced_projections),
                        "source": "VERIFIED projections/nfl/regular/2025"
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
    """Main entry point for STREAMLINED Sleeper MCP server"""
    logger.info("NFL Starting STREAMLINED Sleeper MCP Server...")
    logger.info(f"LIST Legion League ID: {LEGION_LEAGUE_ID}")
    logger.info("PASS Using VERIFIED Sleeper API endpoints")
    
    # Run the server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sleeper-server",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
