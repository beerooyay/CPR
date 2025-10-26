"""CPR-NFL Core Modules"""

__version__ = "1.0.0"
__author__ = "CPR-NFL Team"

from .models import (
    Team, Player, PlayerStats, Position, InjuryStatus,
    CPRMetrics, NIVMetrics, LeagueInfo, Matchup, Transaction, LeagueAnalysis
)
from .api import SleeperAPI, AsyncSleeperAPI
from .cpr import CPREngine
from .niv import NIVCalculator, NIVConfig
from .database import Database
from .utils import *
from .jaylen import JaylenAI

__all__ = [
    # Models
    'Team', 'Player', 'PlayerStats', 'Position', 'InjuryStatus',
    'CPRMetrics', 'NIVMetrics', 'LeagueInfo', 'Matchup', 'Transaction', 'LeagueAnalysis',
    
    # API
    'SleeperAPI', 'AsyncSleeperAPI',
    
    # Engines
    'CPREngine', 'NIVCalculator', 'NIVConfig', 'JaylenAI',
    
    # Database
    'Database',
    
    # Utils (all functions imported)
]
