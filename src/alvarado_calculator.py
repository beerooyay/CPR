#!/usr/bin/env python3
"""
ALVARADO INDEX CALCULATOR
Real Shapley Value + ADP efficiency calculator for CPR framework
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from itertools import combinations
import logging

try:
    from .models import Team, Player, Position
    from .utils import make_sleeper_request, calculate_z_score
except ImportError:
    from models import Team, Player, Position
    from utils import make_sleeper_request, calculate_z_score

logger = logging.getLogger(__name__)

class AlvaradoCalculator:
    """Calculate Alvarado Index using Shapley Value + ADP methodology"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.draft_data = None
        self.adp_cache = {}
        
    def _fetch_draft_data(self) -> Dict[str, Any]:
        """Fetch draft data from Sleeper API"""
        if self.draft_data is not None:
            return self.draft_data
        
        try:
            # Get draft list
            drafts = make_sleeper_request(f"league/{self.league_id}/drafts")
            if not drafts:
                logger.error("No draft data found")
                return {}
            
            # Get draft picks for the most recent draft
            draft_id = drafts[0]['draft_id']
            picks = make_sleeper_request(f"draft/{draft_id}/picks")
            
            if not picks:
                logger.error("No draft picks found")
                return {}
            
            # Build ADP mapping
            adp_mapping = {}
            for pick in picks:
                player_id = pick['player_id']
                pick_no = pick['pick_no']
                round_num = pick['round']
                roster_id = pick['roster_id']
                
                adp_mapping[player_id] = {
                    'pick_no': pick_no,
                    'round': round_num,
                    'roster_id': roster_id,
                    'adp_cost': pick_no  # Higher pick number = higher cost
                }
            
            self.draft_data = {
                'draft_id': draft_id,
                'picks': picks,
                'adp_mapping': adp_mapping
            }
            
            logger.info(f"Draft data loaded: {len(picks)} picks")
            return self.draft_data
            
        except Exception as e:
            logger.error(f"Failed to fetch draft data: {e}")
            return {}
    
    def _get_player_adp_cost(self, player_id: str) -> float:
        """Get ADP cost for player (lower = cheaper)"""
        draft_data = self._fetch_draft_data()
        adp_mapping = draft_data.get('adp_mapping', {})
        
        if player_id in adp_mapping:
            pick_no = adp_mapping[player_id]['pick_no']
            # Convert to cost: early picks (1-24) = expensive, late picks = cheap
            # Normalize to 0-1 scale where 1 = most expensive (pick 1)
            max_picks = 144  # 12 teams * 12 rounds typical
            cost = 1.0 - (pick_no - 1) / max_picks
            return max(0.0, min(cost, 1.0))
        else:
            # Undrafted player (waiver pickup) = cheapest possible
            return 0.0
    
    def _calculate_shapley_value(self, player_id: str, team: Team, 
                                weekly_matchups: Dict[int, Dict[str, float]]) -> float:
        """Calculate Shapley value for player's contribution to team success"""
        
        if not weekly_matchups:
            logger.warning("No weekly matchup data for Shapley calculation")
            return 0.0
        
        total_contribution = 0.0
        total_weeks = 0
        
        # For each week, calculate marginal contribution
        for week, matchup_data in weekly_matchups.items():
            team_matchup = matchup_data.get(str(team.team_id))
            if not team_matchup:
                continue
            
            player_points = team_matchup.get('players_points', {}).get(player_id, 0.0)
            team_total = team_matchup.get('points', 0.0)
            
            if team_total > 0:
                # Player's contribution as percentage of team total
                contribution = player_points / team_total
                total_contribution += contribution
                total_weeks += 1
        
        if total_weeks == 0:
            return 0.0
        
        # Average weekly contribution
        avg_contribution = total_contribution / total_weeks
        
        # Scale to meaningful range (0-100)
        shapley_value = avg_contribution * 100
        
        return max(0.0, shapley_value)
    
    def _fetch_weekly_matchups(self, weeks: List[int] = None) -> Dict[int, Dict[str, Any]]:
        """Fetch weekly matchup data for Shapley calculation"""
        if weeks is None:
            weeks = list(range(1, 9))  # Weeks 1-8 (current)
        
        weekly_data = {}
        
        for week in weeks:
            try:
                matchups = make_sleeper_request(f"league/{self.league_id}/matchups/{week}")
                if matchups:
                    week_data = {}
                    for matchup in matchups:
                        roster_id = str(matchup.get('roster_id'))
                        week_data[roster_id] = {
                            'points': matchup.get('points', 0.0),
                            'players_points': matchup.get('players_points', {})
                        }
                    weekly_data[week] = week_data
                    
            except Exception as e:
                logger.warning(f"Failed to fetch week {week} matchups: {e}")
                continue
        
        logger.info(f"Loaded matchup data for {len(weekly_data)} weeks")
        return weekly_data
    
    def calculate_player_alvarado(self, player_id: str, team: Team, 
                                 weekly_matchups: Dict[int, Dict[str, Any]] = None) -> float:
        """Calculate Alvarado Index for a single player"""
        
        if weekly_matchups is None:
            weekly_matchups = self._fetch_weekly_matchups()
        
        # Calculate Shapley value (contribution to team success)
        shapley_value = self._calculate_shapley_value(player_id, team, weekly_matchups)
        
        # Get ADP cost
        adp_cost = self._get_player_adp_cost(player_id)
        
        # Calculate NIV z-score (simplified - using Shapley as proxy)
        niv_z = (shapley_value - 5.0) / 2.0  # Rough normalization
        
        # Calculate ADP z-score
        adp_z = (adp_cost - 0.5) / 0.3  # Rough normalization
        
        # Alvarado formula: Shapley_Value / [(NIV_z + ADP_z) / 2]²
        cost_factor = (niv_z + adp_z) / 2.0
        
        # Avoid division by zero
        if abs(cost_factor) < 0.1:
            cost_factor = 0.1
        
        alvarado_index = shapley_value / (cost_factor ** 2)
        
        # Normalize to reasonable range
        alvarado_index = max(0.0, min(alvarado_index, 100.0))
        
        logger.debug(f"Player {player_id}: Shapley={shapley_value:.2f}, ADP_cost={adp_cost:.2f}, Alvarado={alvarado_index:.2f}")
        
        return alvarado_index
    
    def calculate_team_alvarado(self, team: Team, 
                               weekly_matchups: Dict[int, Dict[str, Any]] = None) -> float:
        """Calculate average Alvarado Index for team's key players"""
        
        if weekly_matchups is None:
            weekly_matchups = self._fetch_weekly_matchups()
        
        # Focus on starters for team Alvarado
        key_players = team.starters[:7]  # Top 7 starters
        
        if not key_players:
            logger.warning(f"Team {team.team_name} has no starters")
            return 0.0
        
        alvarado_scores = []
        
        for player_id in key_players:
            try:
                player_alvarado = self.calculate_player_alvarado(player_id, team, weekly_matchups)
                alvarado_scores.append(player_alvarado)
                
            except Exception as e:
                logger.warning(f"Failed to calculate Alvarado for player {player_id}: {e}")
                continue
        
        if not alvarado_scores:
            return 0.0
        
        # Team Alvarado = average of key players
        team_alvarado = sum(alvarado_scores) / len(alvarado_scores)
        
        logger.debug(f"Team {team.team_name}: Alvarado Index = {team_alvarado:.3f}")
        
        return team_alvarado
    
    def calculate_league_alvarado(self, teams: List[Team]) -> Dict[str, float]:
        """Calculate Alvarado Index for all teams in league"""
        logger.info("Calculating Alvarado Index for all teams...")
        
        # Fetch weekly matchups once for all teams
        weekly_matchups = self._fetch_weekly_matchups()
        
        alvarado_scores = {}
        
        for team in teams:
            try:
                team_alvarado = self.calculate_team_alvarado(team, weekly_matchups)
                alvarado_scores[team.team_id] = team_alvarado
                
                logger.info(f"{team.team_name}: Alvarado Index = {team_alvarado:.3f}")
                
            except Exception as e:
                logger.error(f"Failed to calculate Alvarado for {team.team_name}: {e}")
                alvarado_scores[team.team_id] = 0.0
        
        return alvarado_scores
    
    def get_draft_value_analysis(self, teams: List[Team]) -> Dict[str, Any]:
        """Analyze draft value efficiency across the league"""
        logger.info("Analyzing draft value efficiency...")
        
        draft_data = self._fetch_draft_data()
        weekly_matchups = self._fetch_weekly_matchups()
        
        if not draft_data:
            return {}
        
        analysis = {
            'teams': {},
            'best_values': [],
            'worst_values': [],
            'undrafted_gems': []
        }
        
        all_player_values = []
        
        for team in teams:
            team_analysis = {
                'team_name': team.team_name,
                'players': {},
                'team_alvarado': 0.0
            }
            
            for player_id in team.roster:
                player_alvarado = self.calculate_player_alvarado(player_id, team, weekly_matchups)
                adp_cost = self._get_player_adp_cost(player_id)
                
                player_analysis = {
                    'alvarado_index': player_alvarado,
                    'adp_cost': adp_cost,
                    'value_rating': 'undrafted' if adp_cost == 0.0 else ('great' if player_alvarado > 10 and adp_cost < 0.5 else 'poor' if player_alvarado < 2 and adp_cost > 0.7 else 'average')
                }
                
                team_analysis['players'][player_id] = player_analysis
                all_player_values.append((player_id, player_alvarado, adp_cost))
            
            team_analysis['team_alvarado'] = self.calculate_team_alvarado(team, weekly_matchups)
            analysis['teams'][team.team_id] = team_analysis
        
        # Find best and worst values
        all_player_values.sort(key=lambda x: x[1], reverse=True)  # Sort by Alvarado
        
        analysis['best_values'] = all_player_values[:10]
        analysis['worst_values'] = all_player_values[-10:]
        analysis['undrafted_gems'] = [(pid, alv, cost) for pid, alv, cost in all_player_values if cost == 0.0 and alv > 5.0]
        
        return analysis

# Convenience functions
def calculate_alvarado_index(player_id: str, team: Team, league_id: str = "1267325171853701120") -> float:
    """Calculate Alvarado Index for a single player"""
    calculator = AlvaradoCalculator(league_id)
    return calculator.calculate_player_alvarado(player_id, team)

def calculate_team_alvarado_indices(teams: List[Team], league_id: str = "1267325171853701120") -> Dict[str, float]:
    """Calculate Alvarado Index for all teams"""
    calculator = AlvaradoCalculator(league_id)
    return calculator.calculate_league_alvarado(teams)
