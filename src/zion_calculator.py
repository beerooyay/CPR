#!/usr/bin/env python3
"""
ZION TENSOR CALCULATOR
Real 4D Strength of Schedule tensor calculator for CPR framework
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import statistics
import logging

try:
    from .models import Team, Player, Position
    from .utils import make_sleeper_request
    from .ingram_calculator import IngramCalculator
    from .alvarado_calculator import AlvaradoCalculator
except ImportError:
    from models import Team, Player, Position
    from utils import make_sleeper_request
    from ingram_calculator import IngramCalculator
    from alvarado_calculator import AlvaradoCalculator

logger = logging.getLogger(__name__)

class ZionTensorCalculator:
    """Calculate Zion Tensor using 4D Strength of Schedule methodology"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.ingram_calc = IngramCalculator()
        self.alvarado_calc = AlvaradoCalculator(league_id)
        self.matchup_cache = {}
        
    def _fetch_all_matchups(self, weeks: List[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """Fetch all weekly matchups for tensor calculation"""
        if weeks is None:
            weeks = list(range(1, 9))  # Weeks 1-8 (current)
        
        all_matchups = {}
        
        for week in weeks:
            try:
                matchups = make_sleeper_request(f"league/{self.league_id}/matchups/{week}")
                if matchups:
                    all_matchups[week] = matchups
                    
            except Exception as e:
                logger.warning(f"Failed to fetch week {week} matchups: {e}")
                continue
        
        logger.info(f"✅ Loaded matchups for {len(all_matchups)} weeks")
        return all_matchups
    
    def _get_team_opponents(self, team_id: str, all_matchups: Dict[int, List[Dict[str, Any]]]) -> List[str]:
        """Get list of opponent team IDs for a team"""
        opponents = []
        
        for week, matchups in all_matchups.items():
            # Find team's matchup for this week
            team_matchup = None
            for matchup in matchups:
                if str(matchup.get('roster_id')) == str(team_id):
                    team_matchup = matchup
                    break
            
            if not team_matchup:
                continue
            
            # Find opponent in same matchup_id
            matchup_id = team_matchup.get('matchup_id')
            if matchup_id:
                for matchup in matchups:
                    if (matchup.get('matchup_id') == matchup_id and 
                        str(matchup.get('roster_id')) != str(team_id)):
                        opponents.append(str(matchup.get('roster_id')))
                        break
        
        return opponents
    
    def _calculate_dimension_1_traditional(self, team_id: str, opponents: List[str], 
                                         teams: List[Team]) -> float:
        """Dimension 1: Traditional SoS (opponent win percentage)"""
        if not opponents:
            return 0.5  # Neutral if no opponents
        
        # Create team lookup
        team_lookup = {str(team.team_id): team for team in teams}
        
        opponent_win_pcts = []
        
        for opp_id in opponents:
            opponent = team_lookup.get(opp_id)
            if opponent:
                win_pct = opponent.win_percentage
                opponent_win_pcts.append(win_pct)
        
        if not opponent_win_pcts:
            return 0.5
        
        # Average opponent win percentage
        avg_opp_win_pct = statistics.mean(opponent_win_pcts)
        
        logger.debug(f"Team {team_id} Traditional SoS: {avg_opp_win_pct:.3f}")
        return avg_opp_win_pct
    
    def _calculate_dimension_2_volatility(self, team_id: str, opponents: List[str],
                                        all_matchups: Dict[int, List[Dict[str, Any]]]) -> float:
        """Dimension 2: Volatility Exposure (opponent score variance)"""
        if not opponents:
            return 0.0
        
        # Collect opponent weekly scores
        opponent_scores = {opp_id: [] for opp_id in set(opponents)}
        
        for week, matchups in all_matchups.items():
            for matchup in matchups:
                roster_id = str(matchup.get('roster_id'))
                if roster_id in opponent_scores:
                    points = matchup.get('points', 0.0)
                    opponent_scores[roster_id].append(points)
        
        # Calculate variance for each opponent
        opponent_variances = []
        
        for opp_id, scores in opponent_scores.items():
            if len(scores) > 1:
                variance = statistics.variance(scores)
                opponent_variances.append(variance)
        
        if not opponent_variances:
            return 0.0
        
        # Average opponent variance (normalized)
        avg_variance = statistics.mean(opponent_variances)
        normalized_variance = min(avg_variance / 1000.0, 1.0)  # Normalize to 0-1
        
        logger.debug(f"Team {team_id} Volatility Exposure: {normalized_variance:.3f}")
        return normalized_variance
    
    def _calculate_dimension_3_positional(self, team_id: str, opponents: List[str],
                                        teams: List[Team], players: Dict[str, Player]) -> float:
        """Dimension 3: Positional Stress (opponent Ingram indices)"""
        if not opponents:
            return 0.5
        
        # Create team lookup
        team_lookup = {str(team.team_id): team for team in teams}
        
        opponent_ingram_scores = []
        
        for opp_id in set(opponents):  # Remove duplicates
            opponent = team_lookup.get(opp_id)
            if opponent:
                ingram_score = self.ingram_calc.calculate_team_ingram(opponent, players)
                opponent_ingram_scores.append(ingram_score)
        
        if not opponent_ingram_scores:
            return 0.5
        
        # Average opponent Ingram (higher = more balanced opponents = harder)
        avg_opp_ingram = statistics.mean(opponent_ingram_scores)
        
        logger.debug(f"Team {team_id} Positional Stress: {avg_opp_ingram:.3f}")
        return avg_opp_ingram
    
    def _calculate_dimension_4_efficiency(self, team_id: str, opponents: List[str],
                                        teams: List[Team]) -> float:
        """Dimension 4: Efficiency Pressure (opponent Alvarado indices)"""
        if not opponents:
            return 0.5
        
        # Create team lookup
        team_lookup = {str(team.team_id): team for team in teams}
        
        opponent_alvarado_scores = []
        
        for opp_id in set(opponents):  # Remove duplicates
            opponent = team_lookup.get(opp_id)
            if opponent:
                try:
                    alvarado_score = self.alvarado_calc.calculate_team_alvarado(opponent)
                    opponent_alvarado_scores.append(alvarado_score)
                except Exception as e:
                    logger.warning(f"Failed to calculate Alvarado for opponent {opp_id}: {e}")
                    continue
        
        if not opponent_alvarado_scores:
            return 0.5
        
        # Average opponent Alvarado (higher = more efficient opponents = harder)
        avg_opp_alvarado = statistics.mean(opponent_alvarado_scores)
        
        # Normalize to 0-1 range
        normalized_alvarado = min(avg_opp_alvarado / 20.0, 1.0)
        
        logger.debug(f"Team {team_id} Efficiency Pressure: {normalized_alvarado:.3f}")
        return normalized_alvarado
    
    def calculate_team_zion_tensor(self, team: Team, teams: List[Team], 
                                  players: Dict[str, Player]) -> Dict[str, Any]:
        """Calculate 4D Zion Tensor for a single team"""
        
        # Fetch all matchup data
        all_matchups = self._fetch_all_matchups()
        
        # Get team's opponents
        opponents = self._get_team_opponents(team.team_id, all_matchups)
        
        if not opponents:
            logger.warning(f"No opponents found for team {team.team_name}")
            return {
                'tensor_vector': [0.5, 0.0, 0.5, 0.5],
                'tensor_magnitude': 0.5,
                'dimensions': {
                    'traditional': 0.5,
                    'volatility': 0.0,
                    'positional': 0.5,
                    'efficiency': 0.5
                }
            }
        
        # Calculate each dimension
        dim1_traditional = self._calculate_dimension_1_traditional(team.team_id, opponents, teams)
        dim2_volatility = self._calculate_dimension_2_volatility(team.team_id, opponents, all_matchups)
        dim3_positional = self._calculate_dimension_3_positional(team.team_id, opponents, teams, players)
        dim4_efficiency = self._calculate_dimension_4_efficiency(team.team_id, opponents, teams)
        
        # Create 4D tensor vector
        tensor_vector = [dim1_traditional, dim2_volatility, dim3_positional, dim4_efficiency]
        
        # Calculate tensor magnitude: ||tensor|| = sqrt(dim1² + dim2² + dim3² + dim4²)
        tensor_magnitude = math.sqrt(sum(dim ** 2 for dim in tensor_vector))
        
        result = {
            'tensor_vector': tensor_vector,
            'tensor_magnitude': tensor_magnitude,
            'dimensions': {
                'traditional': dim1_traditional,
                'volatility': dim2_volatility,
                'positional': dim3_positional,
                'efficiency': dim4_efficiency
            },
            'opponents_faced': len(set(opponents)),
            'interpretation': self._interpret_tensor(tensor_vector)
        }
        
        logger.debug(f"Team {team.team_name}: Zion Tensor = {tensor_magnitude:.3f} {tensor_vector}")
        
        return result
    
    def _interpret_tensor(self, tensor_vector: List[float]) -> Dict[str, str]:
        """Interpret what the tensor dimensions mean"""
        dim1, dim2, dim3, dim4 = tensor_vector
        
        interpretation = {}
        
        # Traditional SoS
        if dim1 > 0.6:
            interpretation['traditional'] = "Facing strong opponents (high win %)"
        elif dim1 < 0.4:
            interpretation['traditional'] = "Facing weak opponents (low win %)"
        else:
            interpretation['traditional'] = "Facing average opponents"
        
        # Volatility
        if dim2 > 0.3:
            interpretation['volatility'] = "High volatility opponents (boom/bust)"
        elif dim2 < 0.1:
            interpretation['volatility'] = "Consistent opponents"
        else:
            interpretation['volatility'] = "Moderate opponent volatility"
        
        # Positional
        if dim3 > 0.7:
            interpretation['positional'] = "Facing well-balanced rosters"
        elif dim3 < 0.3:
            interpretation['positional'] = "Facing unbalanced rosters"
        else:
            interpretation['positional'] = "Facing average roster balance"
        
        # Efficiency
        if dim4 > 0.7:
            interpretation['efficiency'] = "Facing efficient draft/value teams"
        elif dim4 < 0.3:
            interpretation['efficiency'] = "Facing inefficient teams"
        else:
            interpretation['efficiency'] = "Facing average efficiency teams"
        
        return interpretation
    
    def calculate_league_zion_tensors(self, teams: List[Team], 
                                    players: Dict[str, Player]) -> Dict[str, Dict[str, Any]]:
        """Calculate Zion Tensors for all teams in league"""
        logger.info("Calculating Zion Tensors for all teams...")
        
        zion_tensors = {}
        
        for team in teams:
            try:
                tensor_result = self.calculate_team_zion_tensor(team, teams, players)
                zion_tensors[team.team_id] = tensor_result
                
                magnitude = tensor_result['tensor_magnitude']
                logger.info(f"✅ {team.team_name}: Zion Tensor = {magnitude:.3f}")
                
            except Exception as e:
                logger.error(f"❌ Failed to calculate Zion Tensor for {team.team_name}: {e}")
                zion_tensors[team.team_id] = {
                    'tensor_vector': [0.5, 0.0, 0.5, 0.5],
                    'tensor_magnitude': 0.5,
                    'dimensions': {'traditional': 0.5, 'volatility': 0.0, 'positional': 0.5, 'efficiency': 0.5}
                }
        
        return zion_tensors
    
    def analyze_schedule_difficulty(self, teams: List[Team], 
                                  players: Dict[str, Player]) -> Dict[str, Any]:
        """Analyze schedule difficulty across all dimensions"""
        logger.info("Analyzing schedule difficulty across league...")
        
        zion_tensors = self.calculate_league_zion_tensors(teams, players)
        
        analysis = {
            'teams': zion_tensors,
            'hardest_schedule': None,
            'easiest_schedule': None,
            'most_volatile': None,
            'most_balanced_opponents': None,
            'league_averages': {}
        }
        
        # Calculate rankings
        magnitude_rankings = [(team.team_name, zion_tensors[team.team_id]['tensor_magnitude']) 
                            for team in teams]
        magnitude_rankings.sort(key=lambda x: x[1], reverse=True)
        
        analysis['hardest_schedule'] = magnitude_rankings[0] if magnitude_rankings else None
        analysis['easiest_schedule'] = magnitude_rankings[-1] if magnitude_rankings else None
        
        # Find most volatile schedule
        volatility_rankings = [(team.team_name, zion_tensors[team.team_id]['dimensions']['volatility']) 
                             for team in teams]
        volatility_rankings.sort(key=lambda x: x[1], reverse=True)
        analysis['most_volatile'] = volatility_rankings[0] if volatility_rankings else None
        
        # Calculate league averages
        if zion_tensors:
            avg_magnitude = statistics.mean([data['tensor_magnitude'] for data in zion_tensors.values()])
            avg_traditional = statistics.mean([data['dimensions']['traditional'] for data in zion_tensors.values()])
            avg_volatility = statistics.mean([data['dimensions']['volatility'] for data in zion_tensors.values()])
            avg_positional = statistics.mean([data['dimensions']['positional'] for data in zion_tensors.values()])
            avg_efficiency = statistics.mean([data['dimensions']['efficiency'] for data in zion_tensors.values()])
            
            analysis['league_averages'] = {
                'tensor_magnitude': avg_magnitude,
                'traditional': avg_traditional,
                'volatility': avg_volatility,
                'positional': avg_positional,
                'efficiency': avg_efficiency
            }
        
        return analysis

# Convenience functions
def calculate_zion_tensor(team: Team, teams: List[Team], players: Dict[str, Player], 
                         league_id: str = "1267325171853701120") -> Dict[str, Any]:
    """Calculate Zion Tensor for a single team"""
    calculator = ZionTensorCalculator(league_id)
    return calculator.calculate_team_zion_tensor(team, teams, players)

def calculate_league_zion_tensors(teams: List[Team], players: Dict[str, Player],
                                league_id: str = "1267325171853701120") -> Dict[str, Dict[str, Any]]:
    """Calculate Zion Tensors for all teams"""
    calculator = ZionTensorCalculator(league_id)
    return calculator.calculate_league_zion_tensors(teams, players)
