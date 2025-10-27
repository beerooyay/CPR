#!/usr/bin/env python3
"""
INGRAM INDEX CALCULATOR
Real HHI-based positional balance calculator for CPR framework
"""

import math
from typing import Dict, List, Any, Optional
from collections import Counter
import logging

try:
    from .models import Team, Player, Position
    from .utils import make_sleeper_request
except ImportError:
    from models import Team, Player, Position
    from utils import make_sleeper_request

logger = logging.getLogger(__name__)

class IngramCalculator:
    """Calculate Ingram Index using HHI positional balance methodology"""
    
    def __init__(self):
        # Legion roster structure (from memory)
        self.starter_positions = {
            'QB': 1,    # 1 QB (locked)
            'RB': 1,    # 1 RB (locked) 
            'WR': 1,    # 1 WR (locked)
            'FLEX_WRT': 2,  # 2 W/R/T FLEX slots
            'FLEX_WT': 1,   # 1 W/T FLEX slot
            'IDP': 1    # 1 IDP slot
        }
        self.total_starters = 7
        self.bench_size = 5  # 5 bench + 1 IR
        
        # Weights from memory
        self.starter_weight = 0.7
        self.bench_weight = 0.3
    
    def _get_position_category(self, position: Position) -> str:
        """Map position to HHI category"""
        if position == Position.QB:
            return 'QB'
        elif position == Position.RB:
            return 'RB'
        elif position == Position.WR:
            return 'WR'
        elif position == Position.TE:
            return 'TE'
        elif position == Position.IDP:
            return 'IDP'
        else:
            return 'OTHER'
    
    def _calculate_hhi(self, position_counts: Dict[str, int], total_players: int) -> float:
        """Calculate Herfindahl-Hirschman Index for position concentration"""
        if total_players == 0:
            return 0.0
        
        hhi = 0.0
        for count in position_counts.values():
            percentage = count / total_players
            hhi += percentage ** 2
        
        return hhi
    
    def _get_player_positions(self, player_ids: List[str], players: Dict[str, Player]) -> Dict[str, int]:
        """Get position counts for list of player IDs"""
        position_counts = Counter()
        
        for player_id in player_ids:
            player = players.get(player_id)
            if player:
                pos_category = self._get_position_category(player.position)
                position_counts[pos_category] += 1
        
        return dict(position_counts)
    
    def calculate_team_ingram(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Ingram Index for a team using real HHI methodology"""
        
        # Get starters and bench
        starters = team.starters[:self.total_starters]  # Ensure exactly 7 starters
        bench = [p for p in team.roster if p not in starters][:self.bench_size]  # Max 5 bench
        
        if not starters:
            logger.warning(f"Team {team.team_name} has no starters")
            return 0.0
        
        # Calculate position distributions
        starter_positions = self._get_player_positions(starters, players)
        bench_positions = self._get_player_positions(bench, players)
        
        # Calculate HHI for starters and bench
        starter_hhi = self._calculate_hhi(starter_positions, len(starters))
        bench_hhi = self._calculate_hhi(bench_positions, len(bench)) if bench else 0.0
        
        # Calculate weighted Ingram Index
        # Ingram = 1 - [(Starter_Weight × Starter_HHI) + (Bench_Weight × Bench_HHI)]
        weighted_hhi = (self.starter_weight * starter_hhi) + (self.bench_weight * bench_hhi)
        ingram_index = 1.0 - weighted_hhi
        
        # Ensure result is between 0 and 1
        ingram_index = max(0.0, min(ingram_index, 1.0))
        
        logger.debug(f"Team {team.team_name}: Starter HHI={starter_hhi:.3f}, Bench HHI={bench_hhi:.3f}, Ingram={ingram_index:.3f}")
        
        return ingram_index
    
    def calculate_league_ingram(self, teams: List[Team], players: Dict[str, Player]) -> Dict[str, float]:
        """Calculate Ingram Index for all teams in league"""
        logger.info("Calculating Ingram Index for all teams...")
        
        ingram_scores = {}
        
        for team in teams:
            try:
                ingram_score = self.calculate_team_ingram(team, players)
                ingram_scores[team.team_id] = ingram_score
                
                logger.info(f"✅ {team.team_name}: Ingram Index = {ingram_score:.3f}")
                
            except Exception as e:
                logger.error(f"❌ Failed to calculate Ingram for {team.team_name}: {e}")
                ingram_scores[team.team_id] = 0.0
        
        return ingram_scores
    
    def get_positional_breakdown(self, team: Team, players: Dict[str, Player]) -> Dict[str, Any]:
        """Get detailed positional breakdown for analysis"""
        starters = team.starters[:self.total_starters]
        bench = [p for p in team.roster if p not in starters][:self.bench_size]
        
        starter_positions = self._get_player_positions(starters, players)
        bench_positions = self._get_player_positions(bench, players)
        
        return {
            'team_name': team.team_name,
            'starters': {
                'positions': starter_positions,
                'total': len(starters),
                'hhi': self._calculate_hhi(starter_positions, len(starters))
            },
            'bench': {
                'positions': bench_positions,
                'total': len(bench),
                'hhi': self._calculate_hhi(bench_positions, len(bench))
            },
            'ingram_index': self.calculate_team_ingram(team, players)
        }
    
    def analyze_positional_balance(self, teams: List[Team], players: Dict[str, Player]) -> Dict[str, Any]:
        """Analyze positional balance across the league"""
        logger.info("Analyzing league positional balance...")
        
        analysis = {
            'teams': {},
            'league_averages': {},
            'most_balanced': None,
            'least_balanced': None
        }
        
        ingram_scores = []
        
        for team in teams:
            breakdown = self.get_positional_breakdown(team, players)
            analysis['teams'][team.team_id] = breakdown
            ingram_scores.append((team.team_name, breakdown['ingram_index']))
        
        # Sort by Ingram Index
        ingram_scores.sort(key=lambda x: x[1], reverse=True)
        
        analysis['most_balanced'] = ingram_scores[0] if ingram_scores else None
        analysis['least_balanced'] = ingram_scores[-1] if ingram_scores else None
        
        # Calculate league averages
        if ingram_scores:
            avg_ingram = sum(score[1] for score in ingram_scores) / len(ingram_scores)
            analysis['league_averages']['ingram_index'] = avg_ingram
        
        logger.info(f"Most balanced team: {analysis['most_balanced']}")
        logger.info(f"Least balanced team: {analysis['least_balanced']}")
        
        return analysis

# Convenience functions
def calculate_ingram_index(team: Team, players: Dict[str, Player]) -> float:
    """Calculate Ingram Index for a single team"""
    calculator = IngramCalculator()
    return calculator.calculate_team_ingram(team, players)

def calculate_league_ingram_indices(teams: List[Team], players: Dict[str, Player]) -> Dict[str, float]:
    """Calculate Ingram Index for all teams"""
    calculator = IngramCalculator()
    return calculator.calculate_league_ingram(teams, players)
