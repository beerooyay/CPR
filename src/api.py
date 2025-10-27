"""Sleeper API client for CPR-NFL system"""
import requests
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import logging

from models import LeagueInfo, Team, Player, PlayerStats, Position, InjuryStatus, Matchup, Transaction

logger = logging.getLogger(__name__)

class SleeperAPI:
    """Sleeper API client with rate limiting and caching"""
    
    def __init__(self, league_id: str, rate_limit: float = 1.0):
        self.league_id = league_id
        self.base_url = "https://api.sleeper.app/v1"
        self.rate_limit = rate_limit  # seconds between requests
        self.last_request_time = 0
        self.session = requests.Session()
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    def _rate_limit_wait(self):
        """Wait to respect rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key"""
        param_str = str(sorted(params.items())) if params else ""
        return f"{endpoint}:{param_str}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache:
            return False
        timestamp, _ = self.cache[cache_key]
        return (time.time() - timestamp) < self.cache_ttl
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make rate-limited request with caching"""
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            _, cached_data = self.cache[cache_key]
            logger.debug(f"Cache hit for {endpoint}")
            return cached_data
        
        # Make actual request
        self._rate_limit_wait()
        
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            self.cache[cache_key] = (time.time(), data)
            logger.debug(f"Fetched and cached {endpoint}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise
    
    def get_league_info(self) -> LeagueInfo:
        """Get league information"""
        data = self._make_request(f"league/{self.league_id}")
        
        return LeagueInfo(
            league_id=data["league_id"],
            name=data["name"],
            season=int(data["season"]),
            current_week=int(data.get("current_week", 1)),
            num_teams=int(data.get("settings", {}).get("num_teams", 0)),
            roster_positions=data["roster_positions"],
            scoring_settings=data["scoring_settings"],
            playoff_weeks=data.get("playoff_weeks", []),
            status=data.get("status", "in_season")
        )
    
    def get_rosters(self) -> List[Team]:
        """Get team rosters with owner display names and team names."""
        rosters_data = self._make_request(f"league/{self.league_id}/rosters")
        # Map owner_id -> display_name and team_name from users endpoint
        users_data = self._make_request(f"league/{self.league_id}/users")
        
        owner_map = {}
        team_name_map = {}
        try:
            for user in users_data:
                owner_id = str(user["user_id"])
                owner_map[owner_id] = user.get("display_name", "Unknown")
                # Get team name from user metadata
                user_meta = user.get("metadata", {}) or {}
                team_name_map[owner_id] = user_meta.get("team_name", "")
        except Exception:
            pass

        teams: List[Team] = []
        for roster in rosters_data:
            owner_id = str(roster.get("owner_id", ""))
            owner_name = owner_map.get(owner_id, "Unknown")
            
            # Use team name from users metadata, fallback to display name, then roster ID
            team_name = team_name_map.get(owner_id, "").strip()
            if not team_name:
                team_name = f"{owner_name}" if owner_name != "Unknown" else f"Team {roster.get('roster_id')}"

            settings = roster.get("settings", {}) or {}
            players = roster.get("players", []) or []
            starters = roster.get("starters", []) or []

            team = Team(
                team_id=str(roster.get("roster_id")),
                team_name=team_name,
                owner_name=owner_name,
                wins=int(settings.get("wins", 0)),
                losses=int(settings.get("losses", 0)),
                ties=int(settings.get("ties", 0)),
                fpts=float(settings.get("fpts", 0)),
                fpts_against=float(settings.get("fpts_against", 0)),
                roster=players,
                starters=starters,
                bench=[]
            )

            team.bench = [p for p in team.roster if p not in team.starters]
            teams.append(team)

        return teams
    
    def get_players(self, player_ids: List[str]) -> Dict[str, Player]:
        """Get player information for given IDs"""
        players = {}

        def map_pos(pos: Optional[str]) -> Position:
            if not pos:
                return Position.WR
            p = pos.upper()
            if p in {"QB","RB","WR","TE","K"}:
                return Position[p]
            if p in {"DST","DEF"}:
                return Position.DEF
            if p in {"DL","DE","DT","LB","OLB","ILB","DB","CB","S"}:
                return Position.IDP
            # Fallback
            return Position.WR

        # Get all NFL players (API returns dict, not list)
        all_players_data = self._make_request("players/nfl")

        for player_id in player_ids:
            if player_id in all_players_data:
                player_data = all_players_data[player_id]

                # Prefer fantasy_positions first
                fp_list = player_data.get("fantasy_positions") or []
                fantasy_positions: List[Position] = []
                for fp in fp_list:
                    try:
                        fantasy_positions.append(map_pos(fp))
                    except Exception:
                        continue
                # Base position
                position = map_pos(player_data.get("position"))
                if not fantasy_positions:
                    fantasy_positions = [position]

                # Injury status
                injury_str = player_data.get("injury_status", "Active")
                try:
                    injury_status = InjuryStatus(injury_str)
                except ValueError:
                    injury_status = InjuryStatus.ACTIVE

                player = Player(
                    player_id=player_id,
                    name=player_data.get("full_name") or (player_data.get("first_name","?") + " " + player_data.get("last_name","?") ).strip(),
                    position=position,
                    team=player_data.get("team", "FA") or "FA",
                    height=player_data.get("height", ""),
                    weight=int(player_data.get("weight", 0) or 0),
                    college=player_data.get("college", ""),
                    draft_year=int(player_data.get("draft_year", 0) or 0),
                    draft_round=int(player_data.get("draft_round", 0) or 0),
                    status=player_data.get("status", "Active") or "Active",
                    injury_status=injury_status,
                    fantasy_positions=fantasy_positions
                )

                players[player_id] = player
        
        return players
    
    def get_player_stats(self, season: int = 2024) -> Dict[str, PlayerStats]:
        """Get player statistics for a season with fallback to previous season."""
        seasons_to_try = [season]
        if season and isinstance(season, int):
            seasons_to_try.append(season - 1)

        for s in seasons_to_try:
            try:
                stats_data = self._make_request(f"players/nfl/{s}/stats")
                if not isinstance(stats_data, dict) or not stats_data:
                    raise requests.exceptions.RequestException("empty stats body")
            except requests.exceptions.RequestException:
                logger.warning(f"Could not fetch stats for season {s}")
                continue

            player_stats: Dict[str, PlayerStats] = {}
            for player_id, stats in stats_data.items():
                player_stats[player_id] = PlayerStats(
                    season=s,
                    games_played=int(stats.get("gp", 0)),
                    passing_yards=int(stats.get("passing_yds", 0)),
                    passing_tds=int(stats.get("passing_td", 0)),
                    passing_ints=int(stats.get("passing_int", 0)),
                    rushing_yards=int(stats.get("rushing_yds", 0)),
                    rushing_tds=int(stats.get("rushing_td", 0)),
                    receptions=int(stats.get("rec", 0)),
                    receiving_yards=int(stats.get("receiving_yds", 0)),
                    receiving_tds=int(stats.get("receiving_td", 0)),
                    targets=int(stats.get("targets", 0)),
                    fumbles=int(stats.get("fumbles_lost", 0)),
                    fantasy_points=float(stats.get("fantasy_points_ppr", 0.0))
                )
            if player_stats:
                return player_stats

        # Final fallback: build current-season fantasy points from league matchups
        try:
            current_week = self.get_current_week()
            if not isinstance(current_week, int) or current_week < 1:
                return {}

            agg_points: Dict[str, float] = {}
            games_played: Dict[str, int] = {}

            for w in range(1, current_week + 1):
                try:
                    data = self._make_request(f"league/{self.league_id}/matchups/{w}")
                except requests.exceptions.RequestException:
                    continue
                # Each entry corresponds to a team in the week
                for entry in data:
                    pts_map = entry.get("players_points") or entry.get("players_points_ppr") or {}
                    if not isinstance(pts_map, dict):
                        continue
                    for pid, pts in pts_map.items():
                        try:
                            p = float(pts)
                        except (TypeError, ValueError):
                            p = 0.0
                        agg_points[pid] = agg_points.get(pid, 0.0) + p
                        games_played[pid] = games_played.get(pid, 0) + 1

            # Build minimal PlayerStats from aggregated points
            built: Dict[str, PlayerStats] = {}
            for pid, total in agg_points.items():
                built[pid] = PlayerStats(
                    season=season,
                    games_played=games_played.get(pid, 0),
                    fantasy_points=round(total, 2)
                )
            return built
        except Exception as e:
            logger.warning(f"Failed to build stats from matchups: {e}")
            return {}
    
    def get_matchups(self, week: int) -> List[Matchup]:
        """Get matchups for a specific week"""
        try:
            matchups_data = self._make_request(f"league/{self.league_id}/matchups/{week}")
        except requests.exceptions.RequestException:
            logger.warning(f"Could not fetch matchups for week {week}")
            return []
        
        matchups = []
        
        for matchup_data in matchups_data:
            matchup = Matchup(
                matchup_id=matchup_data["matchup_id"],
                week=week,
                team1_id=matchup_data["roster_id"],
                team2_id=matchup_data.get("matchup_id", ""),  # This might need adjustment
                team1_score=float(matchup_data.get("points", 0)),
                team2_score=0.0,  # Will be populated when we find the opponent
                team1_points=matchup_data.get("players_points", {}),
                status="complete" if matchup_data.get("points") else "pending"
            )
            matchups.append(matchup)
        
        return matchups
    
    def get_transactions(self, week: int = None) -> List[Transaction]:
        """Get transactions for a week or all recent transactions"""
        try:
            if week:
                transactions_data = self._make_request(f"league/{self.league_id}/transactions/{week}")
            else:
                # Get recent transactions (last 2 weeks)
                transactions_data = []
                for w in range(max(1, self.get_current_week() - 2), self.get_current_week() + 1):
                    try:
                        week_data = self._make_request(f"league/{self.league_id}/transactions/{w}")
                        transactions_data.extend(week_data)
                    except requests.exceptions.RequestException:
                        continue
        except requests.exceptions.RequestException:
            logger.warning("Could not fetch transactions")
            return []
        
        transactions = []
        
        for trans_data in transactions_data:
            transaction = Transaction(
                transaction_id=trans_data["transaction_id"],
                league_id=self.league_id,
                team_id=trans_data.get("roster_id", ""),  # Use empty string if missing
                player_id=trans_data.get("player_id", ""),
                type=trans_data.get("type", "unknown"),
                timestamp=datetime.fromtimestamp(trans_data.get("status_timestamp", time.time())),
                status=trans_data.get("status", "pending")
            )
            transactions.append(transaction)
        
        return transactions
    
    def get_current_week(self) -> int:
        """Get current NFL week"""
        try:
            nfl_state = self._make_request("state/nfl")
            return int(nfl_state.get("week", 1))
        except requests.exceptions.RequestException:
            return 1
    
    def fetch_all_data(self) -> Dict[str, Any]:
        """Fetch all league data in one call"""
        logger.info(f"Fetching complete data for league {self.league_id}")
        
        # Get basic league info
        league_info = self.get_league_info()
        
        # Get teams and rosters
        teams = self.get_rosters()
        
        # Get all player IDs from rosters
        all_player_ids = []
        for team in teams:
            all_player_ids.extend(team.roster)
        all_player_ids = list(set(all_player_ids))  # Remove duplicates
        
        # Get player information
        players = self.get_players(all_player_ids)
        
        # Get player stats
        player_stats = self.get_player_stats(league_info.season)
        
        # Attach stats to players
        for player_id, stats in player_stats.items():
            if player_id in players:
                players[player_id].stats[league_info.season] = stats
        
        # Get recent matchups
        matchups = []
        for week in range(max(1, league_info.current_week - 2), league_info.current_week + 1):
            week_matchups = self.get_matchups(week)
            matchups.extend(week_matchups)
        
        # Get recent transactions
        transactions = self.get_transactions()
        
        return {
            "league_info": league_info,
            "teams": teams,
            "players": players,
            "matchups": matchups,
            "transactions": transactions,
            "fetch_timestamp": datetime.now().isoformat()
        }
    
    def clear_cache(self):
        """Clear the API cache"""
        self.cache.clear()
        logger.info("API cache cleared")

class AsyncSleeperAPI:
    """Async version of Sleeper API for better performance"""
    
    def __init__(self, league_id: str, rate_limit: float = 1.0):
        self.league_id = league_id
        self.base_url = "https://api.sleeper.app/v1"
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make async request with rate limiting"""
        # Respect rate limits
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        
        url = f"{self.base_url}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self.last_request_time = time.time()
                    return data
            except aiohttp.ClientError as e:
                logger.error(f"Async request failed for {endpoint}: {e}")
                raise
    
    async def fetch_league_data_async(self) -> Dict[str, Any]:
        """Fetch league data concurrently"""
        league_info_task = self._make_request(f"league/{self.league_id}")
        rosters_task = self._make_request(f"league/{self.league_id}/rosters")
        
        league_info, rosters_data = await asyncio.gather(
            league_info_task, rosters_task
        )
        
        # Extract player IDs
        player_ids = []
        for roster in rosters_data:
            player_ids.extend(roster.get("players", []))
        player_ids = list(set(player_ids))
        
        # Fetch player data
        players_data = await self._make_request("players/nfl")
        
        return {
            "league_info": league_info,
            "rosters": rosters_data,
            "players": players_data
        }
