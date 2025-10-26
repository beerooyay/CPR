"""NIV (Normalized Impact Value) Calculator for CPR-NFL"""
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

try:
    from .models import Player, PlayerStats, Position, InjuryStatus, NIVMetrics
    from .utils import calculate_z_score, normalize_values, weighted_average
except ImportError:
    from models import Player, PlayerStats, Position, InjuryStatus, NIVMetrics
    from utils import calculate_z_score, normalize_values, weighted_average

logger = logging.getLogger(__name__)

@dataclass
class NIVConfig:
    """Configuration for NIV calculations"""
    
    # Scoring weights (standard PPR)
    passing_yd_weight: float = 0.04
    passing_td_weight: float = 4.0
    passing_int_weight: float = -2.0
    rushing_yd_weight: float = 0.1
    rushing_td_weight: float = 6.0
    rec_weight: float = 1.0
    receiving_yd_weight: float = 0.1
    receiving_td_weight: float = 6.0
    fumble_weight: float = -2.0
    
    # NIV calculation weights
    recent_performance_weight: float = 0.4
    consistency_weight: float = 0.2
    upside_weight: float = 0.2
    schedule_weight: float = 0.1
    injury_weight: float = 0.1
    
    # Time windows
    recent_weeks: int = 4
    consistency_weeks: int = 8
    season_weight: float = 0.7
    recent_weight: float = 0.3

class NIVCalculator:
    """NIV (Normalized Impact Value) calculation engine"""
    
    def __init__(self, config: NIVConfig = None):
        self.config = config or NIVConfig()
        logger.info("NIV Calculator initialized")
    
    def calculate_player_niv(self, player: Player, 
                            player_stats: Dict[str, PlayerStats],
                            league_context: Dict[str, Any]) -> NIVMetrics:
        """Calculate NIV for a single player"""
        
        try:
            # Get recent performance
            recent_performance = self._calculate_recent_performance(player, player_stats)
            
            # Calculate consistency
            consistency_score = self._calculate_consistency(player, player_stats)
            
            # Calculate upside potential
            upside_score = self._calculate_upside_potential(player, player_stats, league_context)
            
            # Calculate schedule adjustment
            schedule_adj = self._calculate_schedule_adjustment(player, league_context)
            
            # Calculate injury risk
            injury_risk = self._calculate_injury_risk(player)
            
            # Calculate positional NIV
            positional_niv = self._calculate_positional_niv(
                player, recent_performance, consistency_score, 
                upside_score, schedule_adj, injury_risk
            )
            
            # Calculate overall NIV
            overall_niv = self._calculate_overall_niv(positional_niv, player.position)
            
            return NIVMetrics(
                player_id=player.player_id,
                name=player.name,
                position=player.position,
                niv=overall_niv,
                positional_niv=positional_niv,
                market_niv=recent_performance,
                consistency_niv=consistency_score,
                explosive_niv=upside_score
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate NIV for {player.name}: {e}")
            return NIVMetrics(
                player_id=player.player_id,
                name=player.name,
                position=player.position,
                niv=0.0,
                positional_niv=0.0,
                market_niv=0.0,
                consistency_niv=0.0,
                explosive_niv=0.0
            )
    
    def _calculate_recent_performance(self, player: Player, 
                                     player_stats: Dict[str, PlayerStats]) -> float:
        """Calculate recent performance score"""
        
        if not player_stats:
            return 0.0
        
        # Get recent weeks
        recent_stats = list(player_stats.values())[-self.config.recent_weeks:]
        
        if not recent_stats:
            return 0.0
        
        # Calculate fantasy points for recent games
        fantasy_points = []
        for stats in recent_stats:
            points = self._calculate_fantasy_points(stats)
            fantasy_points.append(points)
        
        if not fantasy_points:
            return 0.0
        
        # Calculate performance metrics
        avg_points = statistics.mean(fantasy_points)
        max_points = max(fantasy_points)
        trend = self._calculate_performance_trend(fantasy_points)
        
        # Normalize and combine
        normalized_avg = normalize_values([avg_points], 0, 30)[0]  # 0-30 point range
        normalized_max = normalize_values([max_points], 0, 50)[0]  # 0-50 point range
        normalized_trend = normalize_values([trend], -1, 1)[0]  # -1 to 1 trend
        
        recent_performance = weighted_average(
            [normalized_avg, normalized_max, normalized_trend],
            [0.5, 0.3, 0.2]
        )
        
        return max(0, min(1, recent_performance))
    
    def _calculate_consistency(self, player: Player, 
                              player_stats: Dict[str, PlayerStats]) -> float:
        """Calculate consistency score"""
        
        if not player_stats:
            return 0.0
        
        # Get consistency window
        consistency_stats = list(player_stats.values())[-self.config.consistency_weeks:]
        
        if len(consistency_stats) < 3:
            return 0.5  # Default for insufficient data
        
        # Calculate fantasy points
        fantasy_points = []
        for stats in consistency_stats:
            points = self._calculate_fantasy_points(stats)
            fantasy_points.append(points)
        
        if not fantasy_points:
            return 0.0
        
        # Calculate consistency metrics
        avg_points = statistics.mean(fantasy_points)
        std_dev = statistics.stdev(fantasy_points) if len(fantasy_points) > 1 else 0
        
        # Lower standard deviation = higher consistency
        if avg_points > 0:
            coefficient_of_variation = std_dev / avg_points
            consistency = 1 - min(1, coefficient_of_variation)
        else:
            consistency = 0.0
        
        return max(0, min(1, consistency))
    
    def _calculate_upside_potential(self, player: Player,
                                   player_stats: Dict[str, PlayerStats],
                                   league_context: Dict[str, Any]) -> float:
        """Calculate upside potential score"""
        
        # Base upside on position and recent performance
        position_upside = self._get_position_upside(player.position)
        
        # Adjust for recent breakout games
        recent_stats = list(player_stats.values())[-self.config.recent_weeks:]
        if not recent_stats:
            return position_upside * 0.5
        
        # Find best recent performance
        best_points = 0
        for stats in recent_stats:
            points = self._calculate_fantasy_points(stats)
            best_points = max(best_points, points)
        
        # Normalize best performance
        normalized_best = normalize_values([best_points], 0, 40)[0]
        
        # Combine position upside with recent performance
        upside = weighted_average(
            [position_upside, normalized_best],
            [0.6, 0.4]
        )
        
        return max(0, min(1, upside))
    
    def _calculate_schedule_adjustment(self, player: Player,
                                      league_context: Dict[str, Any]) -> float:
        """Calculate schedule-based adjustment"""
        
        # Get upcoming opponents (placeholder - would integrate with schedule API)
        upcoming_opponents = league_context.get('upcoming_opponents', {}).get(player.player_id, [])
        
        if not upcoming_opponents:
            return 0.5  # Neutral when no schedule data
        
        # Calculate opponent difficulty (lower = easier)
        difficulty_scores = []
        for opponent in upcoming_opponents[:4]:  # Next 4 games
            # Placeholder: would use actual defensive rankings
            difficulty = opponent.get('defensive_rank', 16) / 32  # Normalize to 0-1
            difficulty_scores.append(1 - difficulty)  # Invert so easier = higher score
        
        if difficulty_scores:
            schedule_adj = statistics.mean(difficulty_scores)
        else:
            schedule_adj = 0.5
        
        return max(0, min(1, schedule_adj))
    
    def _calculate_injury_risk(self, player: Player) -> float:
        """Calculate injury risk factor (0 = healthy, 1 = high risk)"""
        
        if player.injury_status == InjuryStatus.ACTIVE:
            return 0.0
        elif player.injury_status == InjuryStatus.QUESTIONABLE:
            return 0.3
        elif player.injury_status == InjuryStatus.DOUBTFUL:
            return 0.7
        elif player.injury_status == InjuryStatus.OUT:
            return 1.0
        elif player.injury_status == InjuryStatus.INJURED_RESERVE:
            return 1.0
        elif player.injury_status == InjuryStatus.SUSPENDED:
            return 0.5
        else:
            return 0.1  # Small risk for unknown status
    
    def _calculate_positional_niv(self, player: Player,
                                 recent_performance: float,
                                 consistency_score: float,
                                 upside_score: float,
                                 schedule_adj: float,
                                 injury_risk: float) -> float:
        """Calculate position-specific NIV"""
        
        # Calculate weighted NIV
        position_weights = self._get_position_weights(player.position)
        
        values = [
            recent_performance,
            consistency_score,
            upside_score,
            schedule_adj,
            (1 - injury_risk)  # Invert injury risk
        ]
        weight_values = [
            position_weights['recent'],
            position_weights['consistency'],
            position_weights['upside'],
            position_weights['schedule'],
            position_weights['injury']
        ]
        
        positional_niv = weighted_average(values, weight_values)
        
        return max(0, min(1, positional_niv))
    
    def _calculate_overall_niv(self, positional_niv: float, position: Position) -> float:
        """Calculate overall NIV with position normalization"""
        
        # Position adjustment factors
        position_factors = {
            Position.QB: 1.2,    # QBs have highest impact
            Position.RB: 1.1,    # RBs high impact
            Position.WR: 1.0,    # WRs baseline
            Position.TE: 0.9,    # TEs slightly lower
            Position.K: 0.5,     # Kickers low impact
            Position.DEF: 0.6    # Defenses low impact
        }
        
        factor = position_factors.get(position, 1.0)
        overall_niv = positional_niv * factor
        
        return max(0, min(1, overall_niv))
    
    def _calculate_fantasy_points(self, stats: PlayerStats) -> float:
        """Calculate fantasy points from stats"""
        
        points = 0.0
        
        # Passing
        points += stats.passing_yards * self.config.passing_yd_weight
        points += stats.passing_tds * self.config.passing_td_weight
        points += stats.passing_ints * self.config.passing_int_weight
        
        # Rushing
        points += stats.rushing_yards * self.config.rushing_yd_weight
        points += stats.rushing_tds * self.config.rushing_td_weight
        
        # Receiving
        points += stats.receptions * self.config.rec_weight
        points += stats.receiving_yards * self.config.receiving_yd_weight
        points += stats.receiving_tds * self.config.receiving_td_weight
        
        # Turnovers
        points += stats.fumbles * self.config.fumble_weight
        
        return points
    
    def _calculate_performance_trend(self, fantasy_points: List[float]) -> float:
        """Calculate performance trend (-1 to 1)"""
        
        if len(fantasy_points) < 2:
            return 0.0
        
        # Simple linear trend
        x = list(range(len(fantasy_points)))
        n = len(fantasy_points)
        
        sum_x = sum(x)
        sum_y = sum(fantasy_points)
        sum_xy = sum(x[i] * fantasy_points[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Calculate slope
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Normalize slope to -1 to 1 range
        normalized_slope = max(-1, min(1, slope / 5))  # Assume 5 points per game as max trend
        
        return normalized_slope
    
    def _get_position_upside(self, position: Position) -> float:
        """Get base upside potential by position"""
        
        upside_map = {
            Position.QB: 0.8,    # High upside
            Position.RB: 0.7,    # High upside
            Position.WR: 0.6,    # Good upside
            Position.TE: 0.5,    # Moderate upside
            Position.K: 0.2,     # Low upside
            Position.DEF: 0.3    # Low upside
        }
        
        return upside_map.get(position, 0.5)
    
    def _get_position_weights(self, position: Position) -> Dict[str, float]:
        """Get NIV calculation weights by position"""
        
        base_weights = {
            'recent': self.config.recent_performance_weight,
            'consistency': self.config.consistency_weight,
            'upside': self.config.upside_weight,
            'schedule': self.config.schedule_weight,
            'injury': self.config.injury_weight
        }
        
        # Adjust weights by position
        if position == Position.QB:
            base_weights['consistency'] *= 1.2  # QB consistency more important
            base_weights['upside'] *= 1.1
        elif position == Position.RB:
            base_weights['recent'] *= 1.1  # RB recent performance more important
            base_weights['injury'] *= 1.3  # RB injury risk higher
        elif position == Position.WR:
            base_weights['upside'] *= 1.2  # WR upside more important
            base_weights['schedule'] *= 1.1
        elif position == Position.TE:
            base_weights['consistency'] *= 0.8  # TE consistency less predictable
            base_weights['upside'] *= 1.3
        
        # Normalize weights to sum to 1
        total_weight = sum(base_weights.values())
        return {k: v / total_weight for k, v in base_weights.items()}
    
    def calculate_league_niv_rankings(self, players: List[Player],
                                    player_stats: Dict[str, Dict[str, PlayerStats]],
                                    league_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate NIV rankings for all players in league"""
        
        logger.info(f"Calculating NIV rankings for {len(players)} players")
        
        league_context = league_context or {}
        niv_results = []
        
        for player in players:
            stats = player_stats.get(player.player_id, {})
            niv_metrics = self.calculate_player_niv(player, stats, league_context)
            niv_results.append(niv_metrics)
        
        # Sort by overall NIV
        niv_results.sort(key=lambda x: x.overall_niv, reverse=True)
        
        # Calculate positional rankings
        positional_rankings = self._calculate_positional_rankings(niv_results)
        
        # Calculate league metrics
        league_metrics = self._calculate_league_niv_metrics(niv_results)
        
        return {
            'rankings': niv_results,
            'positional_rankings': positional_rankings,
            'league_metrics': league_metrics,
            'calculated_at': datetime.now()
        }
    
    def _calculate_positional_rankings(self, niv_results: List[NIVMetrics]) -> Dict[str, List[NIVMetrics]]:
        """Calculate rankings by position"""
        
        positional_rankings = {}
        
        # Group by position
        by_position = {}
        for niv in niv_results:
            # Would need to get player position from player data
            # For now, return empty structure
            pass
        
        return positional_rankings
    
    def _calculate_league_niv_metrics(self, niv_results: List[NIVMetrics]) -> Dict[str, float]:
        """Calculate league-wide NIV metrics"""
        
        if not niv_results:
            return {}
        
        overall_nivs = [niv.overall_niv for niv in niv_results]
        
        return {
            'total_players': len(niv_results),
            'avg_niv': statistics.mean(overall_nivs),
            'median_niv': statistics.median(overall_nivs),
            'max_niv': max(overall_nivs),
            'min_niv': min(overall_nivs),
            'std_dev_niv': statistics.stdev(overall_nivs) if len(overall_nivs) > 1 else 0
        }

# Factory function
def create_niv_calculator(config: NIVConfig = None) -> NIVCalculator:
    """Create NIV calculator with configuration"""
    return NIVCalculator(config)
