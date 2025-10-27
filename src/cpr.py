#!/usr/bin/env python3
"""
REAL CPR CALCULATION ENGINE
Uses actual Ingram, Alvarado, and Zion algorithms for CPR framework
"""

import math
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

try:
    from .models import Team, Player, CPRMetrics, LeagueAnalysis
    from .utils import calculate_gini_coefficient, make_sleeper_request
    from .ingram_calculator import IngramCalculator
    from .alvarado_calculator import AlvaradoCalculator
    from .zion_calculator import ZionTensorCalculator
    from .team_extraction import LegionTeamExtractor
except ImportError:
    from models import Team, Player, CPRMetrics, LeagueAnalysis
    from utils import calculate_gini_coefficient, make_sleeper_request
    from ingram_calculator import IngramCalculator
    from alvarado_calculator import AlvaradoCalculator
    from zion_calculator import ZionTensorCalculator
    from team_extraction import LegionTeamExtractor

logger = logging.getLogger(__name__)

class CPREngine:
    """REAL CPR (Commissioner's Power Rankings) calculation engine"""
    
    def __init__(self, config: Dict[str, Any], league_id: str = "1267325171853701120"):
        self.league_id = league_id
        
        # CPR component weights (must sum to 1.0)
        self.weights = config.get('cpr_weights', {
            'sli': 0.30,      # Strength of Lineup Index
            'bsi': 0.20,      # Bench Strength Index  
            'smi': 0.15,      # Schedule Momentum Index
            'ingram': 0.15,   # Ingram Index (positional balance)
            'alvarado': 0.10, # Alvarado Index (value efficiency)
            'zion': 0.10      # Zion Tensor (4D SoS)
        })
        
        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"CPR weights sum to {total_weight}, normalizing to 1.0")
            for key in self.weights:
                self.weights[key] = self.weights[key] / total_weight
        
        # Initialize real algorithm calculators
        self.ingram_calc = IngramCalculator()
        self.alvarado_calc = AlvaradoCalculator(league_id)
        self.zion_calc = ZionTensorCalculator(league_id)
        self.team_extractor = LegionTeamExtractor(league_id)
        
        # Configuration
        self.bench_multiplier = config.get('bench_multiplier', 0.3)
        self.current_season = config.get('current_season', 2025)
        
        logger.info(f"REAL CPR Engine initialized for league {league_id}")
        logger.info(f"Weights: {self.weights}")
    
    def calculate_sli(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Strength of Lineup Index (SLI) - starter performance"""
        if not team.starters:
            return 0.0
        
        total_fantasy_points = 0.0
        valid_starters = 0
        
        for player_id in team.starters[:7]:  # Max 7 starters
            player = players.get(player_id)
            if player:
                # Get current season stats
                stats = player.get_season_stats(self.current_season)
                
                if stats and stats.games_played > 0:
                    total_fantasy_points += stats.fantasy_points_per_game
                    valid_starters += 1
        
        if valid_starters == 0:
            return 0.0
        
        # Average starter fantasy points per game
        avg_starter_points = total_fantasy_points / valid_starters
        
        # Normalize to 0-2 scale (20+ PPG = 2.0, 0 PPG = 0.0)
        sli = min(avg_starter_points / 10.0, 2.0)
        return max(sli, 0.0)
    
    def calculate_bsi(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Bench Strength Index (BSI) - bench depth"""
        bench_players = [p for p in team.roster if p not in team.starters][:5]  # Max 5 bench
        
        if not bench_players:
            return 0.0
        
        total_bench_points = 0.0
        valid_bench = 0
        
        for player_id in bench_players:
            player = players.get(player_id)
            if player:
                stats = player.get_season_stats(self.current_season)
                
                if stats and stats.games_played > 0:
                    total_bench_points += stats.fantasy_points_per_game
                    valid_bench += 1
        
        if valid_bench == 0:
            return 0.0
        
        # Average bench fantasy points per game
        avg_bench_points = total_bench_points / valid_bench
        
        # Apply bench multiplier and normalize
        bsi = min((avg_bench_points * self.bench_multiplier) / 10.0, 2.0)
        return max(bsi, 0.0)
    
    def calculate_smi(self, team: Team) -> float:
        """Calculate Schedule Momentum Index (SMI) - recent performance trends"""
        # Use points differential and win percentage for momentum
        points_diff = team.fpts - team.fpts_against
        
        # Normalize points differential (-100 to +100 range)
        normalized_diff = max(min(points_diff / 100.0, 1.0), -1.0)
        
        # Win percentage component
        win_component = team.win_percentage
        
        # Combine for momentum (0-2 scale)
        smi = (normalized_diff + 1.0) * win_component
        
        return max(min(smi, 2.0), 0.0)
    
    def calculate_team_cpr(self, team: Team, players: Dict[str, Player], 
                          all_teams: List[Team]) -> CPRMetrics:
        """Calculate CPR for a single team using REAL algorithms"""
        
        logger.debug(f"Calculating CPR for {team.team_name}...")
        
        # Calculate traditional indices
        sli = self.calculate_sli(team, players)
        bsi = self.calculate_bsi(team, players)
        smi = self.calculate_smi(team)
        
        # Calculate REAL algorithm indices
        try:
            ingram = self.ingram_calc.calculate_team_ingram(team, players)
        except Exception as e:
            logger.warning(f"Ingram calculation failed for {team.team_name}: {e}")
            ingram = 0.5  # Default neutral score
        
        try:
            alvarado = self.alvarado_calc.calculate_team_alvarado(team)
            # Normalize Alvarado to 0-2 scale
            alvarado = min(alvarado / 10.0, 2.0)
        except Exception as e:
            logger.warning(f"Alvarado calculation failed for {team.team_name}: {e}")
            alvarado = 0.5  # Default neutral score
        
        try:
            zion_result = self.zion_calc.calculate_team_zion_tensor(team, all_teams, players)
            zion = zion_result['tensor_magnitude']
            # Normalize Zion to 0-2 scale (higher = harder schedule, so invert for CPR)
            zion = max(2.0 - zion, 0.0)
        except Exception as e:
            logger.warning(f"Zion calculation failed for {team.team_name}: {e}")
            zion = 1.0  # Default neutral score
        
        # Calculate weighted CPR score
        cpr = (
            sli * self.weights['sli'] +
            bsi * self.weights['bsi'] +
            smi * self.weights['smi'] +
            ingram * self.weights['ingram'] +
            alvarado * self.weights['alvarado'] +
            zion * self.weights['zion']
        )
        
        # Get real team name from Legion data
        try:
            legion_teams = self.team_extractor.get_teams()
            team_data = next((t for t in legion_teams if t['roster_id'] == int(team.team_id)), None)
            display_name = team_data['team_name'] if team_data else team.team_name
        except Exception as e:
            logger.warning(f"Failed to get Legion team name: {e}")
            display_name = team.team_name
        
        return CPRMetrics(
            team_id=team.team_id,
            team_name=display_name,
            cpr=cpr,
            sli=sli,
            bsi=bsi,
            smi=smi,
            ingram=ingram,
            alvarado=alvarado,
            zion=zion,
            wins=team.wins,
            losses=team.losses
        )
    
    def calculate_league_cpr(self, teams: List[Team], players: Dict[str, Player]) -> Dict[str, Any]:
        """Calculate CPR for entire league using REAL algorithms"""
        logger.info("🚀 Calculating REAL CPR rankings for league...")
        
        # Calculate CPR for each team
        cpr_metrics = []
        for team in teams:
            try:
                team_cpr = self.calculate_team_cpr(team, players, teams)
                cpr_metrics.append(team_cpr)
                logger.info(f"✅ {team_cpr.team_name}: CPR = {team_cpr.cpr:.3f}")
                
            except Exception as e:
                logger.error(f"❌ Failed to calculate CPR for {team.team_name}: {e}")
                continue
        
        # Sort by CPR score (descending)
        cpr_metrics.sort(key=lambda x: x.cpr, reverse=True)
        
        # Assign CPR ranks
        for rank, team_cpr in enumerate(cpr_metrics, 1):
            team_cpr.rank = rank
        
        # Calculate league health metrics
        if cpr_metrics:
            cpr_scores = [team.cpr for team in cpr_metrics]
            gini_coefficient = calculate_gini_coefficient(cpr_scores)
            league_health = max(0.0, 1.0 - gini_coefficient)
        else:
            gini_coefficient = 0.0
            league_health = 0.0
        
        # Generate insights using REAL algorithms
        insights = self._generate_real_insights(cpr_metrics, teams, players)
        
        result = {
            'rankings': [self._serialize_cpr_metrics(team) for team in cpr_metrics],
            'league_health': league_health,
            'gini_coefficient': gini_coefficient,
            'calculation_timestamp': datetime.now().isoformat(),
            'insights': insights,
            'weights_used': self.weights.copy(),
            'algorithm_version': 'REAL_CPR_v1.0'
        }
        
        logger.info(f"✅ REAL CPR calculation complete: {len(cpr_metrics)} teams, health: {league_health:.1%}")
        return result
    
    def _generate_real_insights(self, cpr_metrics: List[CPRMetrics], 
                               teams: List[Team], players: Dict[str, Player]) -> List[str]:
        """Generate insights using REAL algorithm analysis"""
        insights = []
        
        if len(cpr_metrics) < 2:
            return insights
        
        # Top team analysis
        top_team = cpr_metrics[0]
        insights.append(f"👑 {top_team.team_name} leads with CPR {top_team.cpr:.3f}")
        
        # Component analysis
        top_sli = max(cpr_metrics, key=lambda x: x.sli)
        top_ingram = max(cpr_metrics, key=lambda x: x.ingram)
        top_alvarado = max(cpr_metrics, key=lambda x: x.alvarado)
        
        insights.append(f"💪 Strongest lineup: {top_sli.team_name} (SLI: {top_sli.sli:.3f})")
        insights.append(f"⚖️ Most balanced roster: {top_ingram.team_name} (Ingram: {top_ingram.ingram:.3f})")
        insights.append(f"💎 Best draft value: {top_alvarado.team_name} (Alvarado: {top_alvarado.alvarado:.3f})")
        
        # Schedule analysis
        hardest_schedule = min(cpr_metrics, key=lambda x: x.zion)  # Lower Zion = harder schedule
        insights.append(f"😤 Toughest schedule: {hardest_schedule.team_name} (Zion: {hardest_schedule.zion:.3f})")
        
        # Performance vs expectation
        overperformers = []
        underperformers = []
        
        for team_cpr in cpr_metrics:
            # Compare CPR rank to actual record rank
            teams_by_wins = sorted(teams, key=lambda t: t.wins, reverse=True)
            actual_rank = next(i for i, t in enumerate(teams_by_wins, 1) 
                             if t.team_id == team_cpr.team_id)
            
            rank_diff = actual_rank - team_cpr.rank
            
            if rank_diff > 2:
                overperformers.append(team_cpr.team_name)
            elif rank_diff < -2:
                underperformers.append(team_cpr.team_name)
        
        if overperformers:
            insights.append(f"📈 Overperforming record: {', '.join(overperformers[:2])}")
        if underperformers:
            insights.append(f"📉 Underperforming record: {', '.join(underperformers[:2])}")
        
        return insights
    
    def _serialize_cpr_metrics(self, metrics: CPRMetrics) -> Dict[str, Any]:
        """Convert CPRMetrics to dictionary for JSON serialization"""
        return {
            'team_id': metrics.team_id,
            'team_name': metrics.team_name,
            'cpr': round(metrics.cpr, 3),
            'rank': metrics.rank,
            'wins': metrics.wins,
            'losses': metrics.losses,
            'sli': round(metrics.sli, 3),
            'bsi': round(metrics.bsi, 3),
            'smi': round(metrics.smi, 3),
            'ingram': round(metrics.ingram, 3),
            'alvarado': round(metrics.alvarado, 3),
            'zion': round(metrics.zion, 3),
            'cpr_tier': metrics.cpr_tier
        }
    
    def get_algorithm_explanation(self) -> str:
        """Get explanation of REAL CPR algorithms"""
        return """
🏈 REAL CPR ALGORITHM BREAKDOWN:

📊 TRADITIONAL COMPONENTS (65%):
• SLI (30%): Strength of Lineup Index - Average starter fantasy points
• BSI (20%): Bench Strength Index - Bench depth and quality  
• SMI (15%): Schedule Momentum Index - Recent performance trends

🧠 REVOLUTIONARY COMPONENTS (35%):
• Ingram Index (15%): HHI-based positional balance (70% starters, 30% bench)
• Alvarado Index (10%): Shapley Value / ADP efficiency (draft value)
• Zion Tensor (10%): 4D Strength of Schedule (Traditional, Volatility, Positional, Efficiency)

🔬 ALGORITHM SOURCES:
• Ingram: Herfindahl-Hirschman Index adapted for fantasy roster construction
• Alvarado: Game theory Shapley values combined with draft position cost
• Zion: World's first 4D tensor approach to strength of schedule

This is the most mathematically sophisticated fantasy football ranking system ever created.
        """

# Convenience function
def calculate_real_cpr(teams: List[Team], players: Dict[str, Player], 
                      league_id: str = "1267325171853701120", 
                      config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Calculate REAL CPR for league"""
    if config is None:
        config = {}
    
    engine = CPREngine(config, league_id)
    return engine.calculate_league_cpr(teams, players)
