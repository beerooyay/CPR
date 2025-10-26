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
        """Get team rosters"""
        data = self._make_request(f"league/{self.league_id}/rosters")
        
        teams = []
        for roster in data:
            team = Team(
                team_id=roster["roster_id"],
                team_name=roster.get("metadata", {}).get("team_name", f"Team {roster['roster_id']}"),
                owner_name=roster.get("owner_name", "Unknown"),
                wins=int(roster.get("settings", {}).get("wins", 0)),
                losses=int(roster.get("settings", {}).get("losses", 0)),
                ties=int(roster.get("settings", {}).get("ties", 0)),
                fpts=float(roster.get("settings", {}).get("fpts", 0)),
                fpts_against=float(roster.get("settings", {}).get("fpts_against", 0)),
                starters=roster.get("starters", []),
                roster=roster.get("players", []),
                bench=[]  # Will be calculated later
            )
            
            # Calculate bench players (roster - starters)
            team.bench = [p for p in team.roster if p not in team.starters]
            teams.append(team)
        
        return teams
    
    def get_players(self, player_ids: List[str]) -> Dict[str, Player]:
        """Get player information for given IDs"""
        players = {}
        
        # Get all NFL players (API returns dict, not list)
        all_players_data = self._make_request("players/nfl")
        
        for player_id in player_ids:
            if player_id in all_players_data:
                player_data = all_players_data[player_id]
                
                # Parse position
                position_str = player_data.get("position", "UNK")
                try:
                    position = Position(position_str)
                except ValueError:
                    position = Position.QB  # Default fallback
                
                # Parse fantasy positions
                fantasy_positions = []
                for pos_str in player_data.get("fantasy_positions", [position_str]):
                    try:
                        fantasy_positions.append(Position(pos_str))
                    except ValueError:
                        continue
                
                # Parse injury status
                injury_str = player_data.get("injury_status", "Active")
                try:
                    injury_status = InjuryStatus(injury_str)
                except ValueError:
                    injury_status = InjuryStatus.ACTIVE
                
                player = Player(
                    player_id=player_id,
                    name=player_data.get("full_name", "Unknown Player"),
                    position=position,
                    team=player_data.get("team", "FA"),
                    height=player_data.get("height", ""),
                    weight=int(player_data.get("weight", 0)),
                    college=player_data.get("college", ""),
                    draft_year=int(player_data.get("draft_year", 0)),
                    draft_round=int(player_data.get("draft_round", 0)),
                    status=player_data.get("status", "Active"),
                    injury_status=injury_status,
                    fantasy_positions=fantasy_positions
                )
                
                players[player_id] = player
        
        return players
    
    def get_player_stats(self, season: int = 2024) -> Dict[str, PlayerStats]:
        """Get player statistics for a season"""
        try:
            stats_data = self._make_request(f"players/nfl/{season}/stats")
        except requests.exceptions.RequestException:
            logger.warning(f"Could not fetch stats for season {season}")
            return {}
        
        player_stats = {}
        
        for player_id, stats in stats_data.items():
            player_stats[player_id] = PlayerStats(
                season=season,
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
        
        return player_stats
    
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
