"""CPR-NFL Core Modules"""

__version__ = "1.0.0"
__author__ = "CPR-NFL Team"

from .models import (
    Team, Player, PlayerStats, Position, InjuryStatus,
    CPRMetrics, NIVMetrics, LeagueInfo, Matchup, Transaction, LeagueAnalysis
)
from .cpr import CPREngine
from .niv import NIVEngine
from .database import Database
from .utils import *

__all__ = [
    # Models
    'LeagueInfo', 'Team', 'Player', 'PlayerStats', 'CPRMetrics', 'NIVMetrics', 'Position', 'InjuryStatus',
    
    # API
    
    # Engines
    'CPREngine', 'NIVEngine',
    
    # Database
    'Database',
    
    # Utils
    'setup_logging', 'validate_league_id', 'safe_divide'
]
