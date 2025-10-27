"""Data models for CPR-NFL system"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class Position(Enum):
    """Player positions"""
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DEF = "DEF"
    FLEX = "FLEX"
    SUPER_FLEX = "SUPER_FLEX"
    IDP = "IDP"

class InjuryStatus(Enum):
    """Injury status enum"""
    ACTIVE = "Active"
    QUESTIONABLE = "Questionable"
    DOUBTFUL = "Doubtful"
    OUT = "Out"
    INJURED_RESERVE = "Injured Reserve"
    SUSPENDED = "Suspended"

@dataclass
class PlayerStats:
    """Player statistics for a season"""
    season: int
    games_played: int
    passing_yards: int = 0
    passing_tds: int = 0
    passing_ints: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    targets: int = 0
    fumbles: int = 0
    fantasy_points: float = 0.0
    
    @property
    def fantasy_points_per_game(self) -> float:
        """Calculate fantasy points per game"""
        return self.fantasy_points / max(self.games_played, 1)
    
    @property
    def yards_per_reception(self) -> float:
        """Calculate yards per reception"""
        return self.receiving_yards / max(self.receptions, 1)
    
    @property
    def yards_per_carry(self) -> float:
        """Calculate yards per carry"""
        rush_attempts = max(self.rushing_yards // 10, 1)  # Estimate attempts
        return self.rushing_yards / rush_attempts

@dataclass
class Player:
    """NFL player model"""
    player_id: str
    name: str
    position: Position
    team: str
    height: str = ""
    weight: int = 0
    college: str = ""
    draft_year: int = 0
    draft_round: int = 0
    status: str = "Active"
    injury_status: InjuryStatus = InjuryStatus.ACTIVE
    fantasy_positions: List[Position] = None
    stats: Dict[int, PlayerStats] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.fantasy_positions is None:
            self.fantasy_positions = [self.position]
        if self.stats is None:
            self.stats = {}
    
    def get_season_stats(self, season: int) -> Optional[PlayerStats]:
        """Get player stats for a specific season"""
        return self.stats.get(season)
    
    def is_healthy(self) -> bool:
        """Check if player is healthy"""
        return self.injury_status in [InjuryStatus.ACTIVE, InjuryStatus.QUESTIONABLE]

@dataclass
class Team:
    """Fantasy team model"""
    team_id: str
    team_name: str
    owner_name: str
    wins: int = 0
    losses: int = 0
    ties: int = 0
    fpts: float = 0.0
    fpts_against: float = 0.0
    roster: List[str] = None
    starters: List[str] = None
    bench: List[str] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.roster is None:
            self.roster = []
        if self.starters is None:
            self.starters = []
        if self.bench is None:
            self.bench = []
    
    @property
    def win_percentage(self) -> float:
        """Calculate win percentage"""
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / total_games
    
    @property
    def points_for_per_game(self) -> float:
        """Calculate points scored per game"""
        total_games = self.wins + self.losses + self.ties
        return self.fpts / max(total_games, 1)
    
    @property
    def points_against_per_game(self) -> float:
        """Calculate points allowed per game"""
        total_games = self.wins + self.losses + self.ties
        return self.fpts_against / max(total_games, 1)

@dataclass
class CPRMetrics:
    """CPR metrics for a team"""
    team_id: str
    team_name: str
    cpr: float
    sli: float  # Strength of Lineup Index
    bsi: float  # Bench Strength Index
    smi: float  # Schedule Momentum Index
    ingram: float  # Ingram Index (HHI positional balance)
    alvarado: float  # Alvarado Index (Shapley/ADP value efficiency)
    zion: float  # Zion Tensor (4D strength of schedule)
    rank: int = 0
    actual_rank: int = 0
    wins: int = 0
    losses: int = 0
    
    @property
    def cpr_tier(self) -> str:
        """Get CPR tier classification"""
        if self.cpr >= 1.5:
            return "Elite"
        elif self.cpr >= 1.2:
            return "Strong"
        elif self.cpr >= 1.0:
            return "Average"
        elif self.cpr >= 0.8:
            return "Below Average"
        else:
            return "Poor"

@dataclass
class NIVMetrics:
    """NIV metrics for a player"""
    player_id: str
    name: str
    position: Position
    niv: float
    positional_niv: float
    market_niv: float
    consistency_niv: float
    explosive_niv: float
    team_id: str = ""
    rank: int = 0
    positional_rank: int = 0
    
    @property
    def niv_tier(self) -> str:
        """Get NIV tier classification"""
        if self.niv >= 20:
            return "Elite"
        elif self.niv >= 15:
            return "Strong"
        elif self.niv >= 10:
            return "Average"
        elif self.niv >= 5:
            return "Below Average"
        else:
            return "Poor"

@dataclass
class LeagueInfo:
    """League information model"""
    league_id: str
    name: str
    season: int
    current_week: int
    num_teams: int
    roster_positions: List[str]
    scoring_settings: Dict[str, float]
    playoff_weeks: List[int] = None
    status: str = "in_season"
    
    def __post_init__(self):
        """Initialize default values"""
        if self.playoff_weeks is None:
            self.playoff_weeks = []

@dataclass
class Matchup:
    """Matchup model"""
    matchup_id: str
    week: int
    team1_id: str
    team2_id: str
    team1_score: float = 0.0
    team2_score: float = 0.0
    team1_points: Dict[str, float] = None
    team2_points: Dict[str, float] = None
    status: str = "pending"
    
    def __post_init__(self):
        """Initialize default values"""
        if self.team1_points is None:
            self.team1_points = {}
        if self.team2_points is None:
            self.team2_points = {}
    
    @property
    def winner(self) -> Optional[str]:
        """Get winner of matchup"""
        if self.status != "complete":
            return None
        if self.team1_score > self.team2_score:
            return self.team1_id
        elif self.team2_score > self.team1_score:
            return self.team2_id
        else:
            return None

@dataclass
class Transaction:
    """Transaction model"""
    transaction_id: str
    league_id: str
    team_id: str
    player_id: str
    type: str  # add, drop, trade
    timestamp: datetime
    status: str = "pending"
    
    @property
    def is_recent(self) -> bool:
        """Check if transaction is recent (last 7 days)"""
        return (datetime.now() - self.timestamp).days <= 7

@dataclass
class LeagueAnalysis:
    """Complete league analysis results"""
    league_info: LeagueInfo
    cpr_rankings: List[CPRMetrics]
    niv_rankings: List[NIVMetrics]
    teams: List[Team]
    players: Dict[str, Player]
    matchups: List[Matchup] = None
    transactions: List[Transaction] = None
    analysis_timestamp: datetime = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.matchups is None:
            self.matchups = []
        if self.transactions is None:
            self.transactions = []
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now()
    
    @property
    def league_health(self) -> float:
        """Calculate overall league health score"""
        if not self.cpr_rankings:
            return 0.0
        
        # Health based on competitive balance
        top_cpr = max(team.cpr for team in self.cpr_rankings)
        bottom_cpr = min(team.cpr for team in self.cpr_rankings)
        spread = top_cpr - bottom_cpr
        
        # Lower spread = higher health
        health = max(0.0, 1.0 - (spread / 2.0))
        return health
    
    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        for team in self.teams:
            if team.team_id == team_id:
                return team
        return None
    
    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Get player by ID"""
        return self.players.get(player_id)
