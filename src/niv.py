"""NIV (Net Impact Value) Engine for CPR-NFL system"""
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

from .models import Player, Team, NIVMetrics, Position

logger = logging.getLogger(__name__)

class NIVEngine:
    """Net Impact Value calculation engine"""
    
    def __init__(self, config: Dict[str, Any], league_id: str):
        self.config = config
        self.league_id = league_id
        self.niv_weights = config.get('niv_weights', {
            'positional_niv': 0.25,
            'market_niv': 0.25,
            'explosive_niv': 0.25,
            'consistency_niv': 0.25
        })
        self.current_season = config.get('current_season', 2025)
        
        logger.info(f"NIV Engine initialized for league {league_id}")
        logger.info(f"NIV weights: {self.niv_weights}")
    
    def calculate_league_niv(self, teams: List[Team], players: Dict[str, Player]) -> Dict[str, Any]:
        """Calculate NIV rankings for all players in the league"""
        logger.info("Starting NIV calculations for league...")
        
        try:
            # Get all rostered players
            rostered_players = self._get_rostered_players(teams, players)
            
            if not rostered_players:
                logger.warning("No rostered players found")
                return {
                    'rankings': [],
                    'algorithm_version': 'NIV_v1.0',
                    'calculation_timestamp': datetime.now().isoformat()
                }
            
            # Calculate NIV components for each player
            niv_rankings = []
            
            for player_id, player in rostered_players.items():
                try:
                    niv_metrics = self._calculate_player_niv(player, rostered_players)
                    niv_rankings.append(niv_metrics)
                except Exception as e:
                    logger.warning(f"Failed to calculate NIV for player {player.name}: {e}")
                    continue
            
            # Sort by NIV score (highest first)
            niv_rankings.sort(key=lambda x: x.niv, reverse=True)
            
            # Assign ranks
            for i, metrics in enumerate(niv_rankings):
                metrics.rank = i + 1
                # Assign positional ranks
                position_players = [m for m in niv_rankings if m.position == metrics.position]
                position_players.sort(key=lambda x: x.niv, reverse=True)
                metrics.positional_rank = next(
                    (i + 1 for i, m in enumerate(position_players) if m.player_id == metrics.player_id), 
                    1
                )
            
            # Assign NIV tiers
            self._assign_niv_tiers(niv_rankings)
            
            logger.info(f"NIV calculations completed for {len(niv_rankings)} players")
            
            return {
                'rankings': niv_rankings,  # Raw NIVMetrics objects for database
                'rankings_serialized': [self._serialize_niv_metrics(m) for m in niv_rankings],  # Serialized for API
                'total_players': len(niv_rankings),
                'algorithm_version': 'NIV_v1.0',
                'calculation_timestamp': datetime.now().isoformat(),
                'league_id': self.league_id,
                'season': self.current_season
            }
            
        except Exception as e:
            logger.error(f"NIV calculation failed: {e}")
            raise
    
    def _get_rostered_players(self, teams: List[Team], players: Dict[str, Player]) -> Dict[str, Player]:
        """Get all players that are on team rosters"""
        rostered_players = {}
        
        for team in teams:
            if hasattr(team, 'roster') and team.roster:
                for player_id in team.roster:
                    if player_id in players:
                        player = players[player_id]
                        # Add team context to player
                        player.team_id = team.team_id
                        rostered_players[player_id] = player
        
        logger.info(f"Found {len(rostered_players)} rostered players")
        return rostered_players
    
    def _calculate_player_niv(self, player: Player, all_players: Dict[str, Player]) -> NIVMetrics:
        """Calculate NIV metrics for a single player"""
        
        # Get player stats for current season
        current_stats = player.stats.get(self.current_season) if player.stats else None
        
        if not current_stats:
            # Use default values for players without stats
            fantasy_points = 0.0
            games_played = 0
            consistency = 0.0
            explosive_games = 0
        else:
            fantasy_points = current_stats.fantasy_points or 0.0
            games_played = current_stats.games_played or 0
            
            # Calculate consistency (inverse of standard deviation of weekly scores)
            # For now, use a simple approximation based on total points and games
            if games_played > 0:
                avg_points = fantasy_points / games_played
                consistency = min(avg_points / 20.0, 1.0)
            else:
                avg_points = 0.0
                consistency = 0.0
            
            # Count explosive games (games with >1.5x average)
            if games_played > 0:
                avg_points = fantasy_points / games_played
                # Estimate explosive games as percentage of total games
                explosive_games = max(0, int(games_played * (avg_points / 15.0) * 0.3))
            else:
                explosive_games = 0
        
        # Calculate NIV components
        positional_niv = self._calculate_positional_niv(player, all_players)
        market_niv = self._calculate_market_niv(player, fantasy_points)
        explosive_niv = self._calculate_explosive_niv(explosive_games, games_played)
        consistency_niv = self._calculate_consistency_niv(consistency)
        
        # Calculate overall NIV
        niv = (
            self.niv_weights['positional_niv'] * positional_niv +
            self.niv_weights['market_niv'] * market_niv +
            self.niv_weights['explosive_niv'] * explosive_niv +
            self.niv_weights['consistency_niv'] * consistency_niv
        )
        
        return NIVMetrics(
            player_id=player.player_id,
            name=player.name,
            position=player.position,
            team_id=getattr(player, 'team_id', ''),
            niv=round(niv, 2),
            positional_niv=round(positional_niv, 2),
            market_niv=round(market_niv, 2),
            explosive_niv=round(explosive_niv, 2),
            consistency_niv=round(consistency_niv, 2),
            rank=0,  # Will be set later
            positional_rank=0  # Will be set later
            # niv_tier is a property, not a field
        )
    
    def _calculate_positional_niv(self, player: Player, all_players: Dict[str, Player]) -> float:
        """Calculate positional NIV based on scarcity and value at position"""
        position_players = [p for p in all_players.values() if p.position == player.position]
        
        if not position_players:
            return 50.0  # Default value
        
        current_stats = player.stats.get(self.current_season) if player.stats else None
        player_points = current_stats.fantasy_points if current_stats and current_stats.fantasy_points else 0.0

        position_points = []
        for p in position_players:
            p_stats = p.stats.get(self.current_season) if p.stats else None
            points = p_stats.fantasy_points if p_stats and p_stats.fantasy_points else 0.0
            position_points.append(points)

        if not position_points or max(position_points) == 0:
            return 50.0

        # Use numpy for safe percentile calculation
        percentile = (np.sum(np.array(position_points) < player_points) / len(position_points)) * 100
        
        # Apply position scarcity multipliers
        position_multipliers = {
            Position.QB: 0.8,   # Less scarce
            Position.RB: 1.2,   # More scarce
            Position.WR: 1.0,   # Baseline
            Position.TE: 1.3,   # Most scarce
            Position.K: 0.6,    # Least valuable
            Position.DEF: 0.7,  # Low value
            Position.IDP: 1.1   # Moderately scarce
        }
        
        multiplier = position_multipliers.get(player.position, 1.0)
        return min(percentile * multiplier, 100.0)
    
    def _calculate_market_niv(self, player: Player, fantasy_points: float) -> float:
        """Calculate market NIV based on overall fantasy production"""
        if fantasy_points <= 0:
            return 0.0
        # Normalize fantasy points to 0-100 scale, 300 is a good top-end score
        market_niv = min((fantasy_points / 300.0) * 100, 100.0)
        
        return market_niv
    
    def _calculate_explosive_niv(self, explosive_games: int, total_games: int) -> float:
        """Calculate explosive NIV based on big game potential"""
        if total_games == 0:
            return 0.0
        explosive_rate = explosive_games / total_games
        return min(explosive_rate * 100, 100.0)
    
    def _calculate_consistency_niv(self, consistency: float) -> float:
        """Calculate consistency NIV based on week-to-week reliability"""
        return consistency * 100
    
    def _assign_niv_tiers(self, niv_rankings: List[NIVMetrics]) -> None:
        """Assign NIV tiers (S, A, B, C, D) based on NIV scores"""
        # NIV tiers are calculated as properties in the model
        # This method is kept for compatibility but doesn't need to do anything
        # since niv_tier is automatically calculated based on niv score
        pass
    
    def _serialize_niv_metrics(self, metrics: NIVMetrics) -> Dict[str, Any]:
        """Convert NIVMetrics to dictionary for JSON serialization"""
        return {
            'player_id': metrics.player_id,
            'name': metrics.name,
            'position': metrics.position.value,
            'team_id': metrics.team_id,
            'niv': metrics.niv,
            'positional_niv': metrics.positional_niv,
            'market_niv': metrics.market_niv,
            'explosive_niv': metrics.explosive_niv,
            'consistency_niv': metrics.consistency_niv,
            'rank': metrics.rank,
            'positional_rank': metrics.positional_rank,
            'niv_tier': metrics.niv_tier
        }
    
    def get_algorithm_explanation(self) -> str:
        """Get explanation of NIV algorithm"""
        return """
## NIV (Net Impact Value) Algorithm

NIV measures a player's overall fantasy impact through four key components:

### Components (25% each):
1. **Positional NIV**: Value relative to position scarcity and peer performance
2. **Market NIV**: Overall fantasy production and scoring ability  
3. **Explosive NIV**: Big game potential and ceiling outcomes
4. **Consistency NIV**: Week-to-week reliability and floor outcomes

### Tiers:
- **S Tier**: Elite (Top 10%) - Game-changing players
- **A Tier**: Excellent (Top 25%) - High-impact starters
- **B Tier**: Good (Top 50%) - Solid contributors
- **C Tier**: Average (Top 75%) - Depth/streaming options
- **D Tier**: Below Average (Bottom 25%) - Avoid/drop candidates

### Position Scarcity Multipliers:
- TE: 1.3x (most scarce)
- RB: 1.2x (very scarce)
- IDP: 1.1x (moderately scarce)
- WR: 1.0x (baseline)
- QB: 0.8x (less scarce)
- DEF: 0.7x (low impact)
- K: 0.6x (least valuable)
"""
