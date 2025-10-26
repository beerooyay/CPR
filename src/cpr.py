"""CPR calculation engine for NFL fantasy teams"""
import statistics
import math
from typing import Dict, List, Any, Optional
import logging

from models import Team, Player, CPRMetrics, LeagueAnalysis
from utils import calculate_gini_coefficient

logger = logging.getLogger(__name__)

class CPREngine:
    """CPR (Commissioner's Power Rankings) calculation engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.weights = config.get('cpr_weights', {
            'sli': 0.30,      # Strength of Lineup Index
            'bsi': 0.20,      # Bench Strength Index  
            'smi': 0.15,      # Schedule Momentum Index
            'ingram': 0.15,   # Ingram Index (injury/availability)
            'alvarado': 0.10, # Alvarado Index (performance consistency)
            'zion': 0.10      # Zion Index (explosive plays)
        })
        self.bench_multiplier = config.get('bench_multiplier', 0.3)
        
        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"CPR weights sum to {total_weight}, normalizing to 1.0")
            for key in self.weights:
                self.weights[key] = self.weights[key] / total_weight
    
    def calculate_sli(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Strength of Lineup Index (SLI)"""
        if not team.starters:
            return 0.0
        
        total_fantasy_points = 0.0
        healthy_starters = 0
        
        for player_id in team.starters:
            player = players.get(player_id)
            if player:
                # Get current season stats (2024 or 2025)
                current_season = 2024  # Default to 2024 for historical data
                stats = player.get_season_stats(current_season)
                
                if stats and player.is_healthy():
                    total_fantasy_points += stats.fantasy_points_per_game
                    healthy_starters += 1
                else:
                    # Penalize for injured players
                    total_fantasy_points += 0.0
        
        # Normalize by number of healthy starters
        if healthy_starters == 0:
            return 0.0
        
        avg_starter_points = total_fantasy_points / len(team.starters)
        
        # Scale to 0-2 range (higher is better)
        sli = min(avg_starter_points / 10.0, 2.0)
        return max(sli, 0.0)
    
    def calculate_bsi(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Bench Strength Index (BSI)"""
        if not team.bench:
            return 0.0
        
        total_bench_points = 0.0
        healthy_bench = 0
        
        for player_id in team.bench:
            player = players.get(player_id)
            if player:
                current_season = 2024
                stats = player.get_season_stats(current_season)
                
                if stats and player.is_healthy():
                    total_bench_points += stats.fantasy_points_per_game
                    healthy_bench += 1
        
        if healthy_bench == 0:
            return 0.0
        
        avg_bench_points = total_bench_points / len(team.bench)
        
        # Apply bench multiplier and scale to 0-2 range
        bsi = min((avg_bench_points * self.bench_multiplier) / 10.0, 2.0)
        return max(bsi, 0.0)
    
    def calculate_smi(self, team: Team, league_analysis: LeagueAnalysis) -> float:
        """Calculate Schedule Momentum Index (SMI)"""
        # For NFL, schedule strength is based on recent performance
        # We'll use win streak and points for/against trends
        
        # Calculate points differential trend
        points_diff = team.fpts - team.fpts_against
        
        # Normalize points differential to 0-2 scale
        # Assume average differential of ±50 points as max
        smi = max(min((points_diff + 50) / 50.0, 2.0), 0.0)
        
        # Bonus for win percentage
        win_bonus = team.win_percentage * 0.5
        smi = min(smi + win_bonus, 2.0)
        
        return max(smi, 0.0)
    
    def calculate_ingram(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Ingram Index (injury/availability)"""
        if not team.roster:
            return 1.0  # Neutral score
        
        healthy_players = 0
        total_players = len(team.roster)
        
        for player_id in team.roster:
            player = players.get(player_id)
            if player and player.is_healthy():
                healthy_players += 1
        
        if total_players == 0:
            return 1.0
        
        availability_ratio = healthy_players / total_players
        
        # Scale to 0-2 range (higher is better)
        ingram = availability_ratio * 2.0
        return max(ingram, 0.0)
    
    def calculate_alvarado(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Alvarado Index (performance consistency)"""
        if not team.starters:
            return 0.0
        
        consistency_scores = []
        
        for player_id in team.starters:
            player = players.get(player_id)
            if player:
                current_season = 2024
                stats = player.get_season_stats(current_season)
                
                if stats and stats.games_played > 0:
                    # Consistency based on games played and steady performance
                    # Higher games played = more consistent
                    consistency = min(stats.games_played / 17.0, 1.0)  # 17 games in NFL season
                    
                    # Bonus for consistent fantasy scoring (low variance proxy)
                    if stats.fantasy_points_per_game > 10:
                        consistency += 0.2
                    
                    consistency_scores.append(min(consistency, 2.0))
        
        if not consistency_scores:
            return 0.0
        
        alvarado = statistics.mean(consistency_scores)
        return max(alvarado, 0.0)
    
    def calculate_zion(self, team: Team, players: Dict[str, Player]) -> float:
        """Calculate Zion Index (explosive plays)"""
        if not team.roster:
            return 0.0
        
        explosive_scores = []
        
        for player_id in team.roster:
            player = players.get(player_id)
            if player:
                current_season = 2024
                stats = player.get_season_stats(current_season)
                
                if stats and stats.games_played > 0:
                    # Calculate explosive potential based on touchdowns
                    total_tds = (stats.passing_tds + stats.rushing_tds + 
                                stats.receiving_tds)
                    
                    tds_per_game = total_tds / max(stats.games_played, 1)
                    
                    # Explosive players score >0.5 TDs per game
                    explosive_score = min(tds_per_game * 2.0, 2.0)
                    explosive_scores.append(explosive_score)
        
        if not explosive_scores:
            return 0.0
        
        zion = statistics.mean(explosive_scores)
        return max(zion, 0.0)
    
    def calculate_team_cpr(self, team: Team, players: Dict[str, Player], 
                          league_analysis: Optional[LeagueAnalysis] = None) -> CPRMetrics:
        """Calculate CPR for a single team"""
        
        # Calculate individual indices
        sli = self.calculate_sli(team, players)
        bsi = self.calculate_bsi(team, players)
        smi = self.calculate_smi(team, league_analysis) if league_analysis else 1.0
        ingram = self.calculate_ingram(team, players)
        alvarado = self.calculate_alvarado(team, players)
        zion = self.calculate_zion(team, players)
        
        # Calculate weighted CPR score
        cpr = (
            sli * self.weights['sli'] +
            bsi * self.weights['bsi'] +
            smi * self.weights['smi'] +
            ingram * self.weights['ingram'] +
            alvarado * self.weights['alvarado'] +
            zion * self.weights['zion']
        )
        
        return CPRMetrics(
            team_id=team.team_id,
            team_name=team.team_name,
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
        """Calculate CPR for entire league"""
        logger.info("Calculating CPR rankings for league")
        
        # Create league analysis for context
        league_analysis = LeagueAnalysis(
            league_info=None,  # Not needed for CPR calculation
            cpr_rankings=[],   # Will be populated
            niv_rankings=[],
            teams=teams,
            players=players
        )
        
        # Calculate CPR for each team
        cpr_metrics = []
        for team in teams:
            team_cpr = self.calculate_team_cpr(team, players, league_analysis)
            team_cpr.actual_rank = team.wins  # Store actual win-based rank
            cpr_metrics.append(team_cpr)
        
        # Sort by CPR score (descending)
        cpr_metrics.sort(key=lambda x: x.cpr, reverse=True)
        
        # Assign CPR ranks
        for rank, team_cpr in enumerate(cpr_metrics, 1):
            team_cpr.rank = rank
        
        # Calculate league health metrics
        cpr_scores = [team.cpr for team in cpr_metrics]
        gini_coefficient = calculate_gini_coefficient(cpr_scores)
        
        # Calculate league health (inverse of Gini coefficient)
        league_health = max(0.0, 1.0 - gini_coefficient)
        
        # Generate insights
        insights = self._generate_insights(cpr_metrics, teams)
        
        result = {
            'rankings': [self._serialize_cpr_metrics(team) for team in cpr_metrics],
            'league_health': league_health,
            'gini_coefficient': gini_coefficient,
            'calculation_timestamp': league_analysis.analysis_timestamp.isoformat(),
            'insights': insights,
            'weights_used': self.weights.copy()
        }
        
        logger.info(f"CPR calculation complete: {len(cpr_metrics)} teams, health: {league_health:.1%}")
        return result
    
    def _serialize_cpr_metrics(self, metrics: CPRMetrics) -> Dict[str, Any]:
        """Convert CPRMetrics to dictionary for JSON serialization"""
        return {
            'team_id': metrics.team_id,
            'team_name': metrics.team_name,
            'cpr': round(metrics.cpr, 3),
            'rank': metrics.rank,
            'actual_rank': metrics.actual_rank,
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
    
    def _generate_insights(self, cpr_metrics: List[CPRMetrics], teams: List[Team]) -> List[str]:
        """Generate insights from CPR calculations"""
        insights = []
        
        if len(cpr_metrics) < 2:
            return insights
        
        # Top team dominance
        top_team = cpr_metrics[0]
        second_team = cpr_metrics[1]
        top_gap = top_team.cpr - second_team.cpr
        
        if top_gap > 0.2:
            insights.append(f"Dominant leader: {top_team.team_name} leads by {top_gap:.3f} CPR points")
        
        # Overperformers vs actual record
        overperformers = []
        underperformers = []
        
        for team_cpr in cpr_metrics:
            actual_wins = team_cpr.wins
            cpr_rank = team_cpr.rank
            
            # Find actual rank based on wins
            teams_by_wins = sorted(teams, key=lambda t: t.wins, reverse=True)
            actual_rank = next(i for i, t in enumerate(teams_by_wins, 1) 
                             if t.team_id == team_cpr.team_id)
            
            if actual_rank < cpr_rank - 2:
                overperformers.append(team_cpr.team_name)
            elif actual_rank > cpr_rank + 2:
                underperformers.append(team_cpr.team_name)
        
        if overperformers:
            insights.append(f"Overperformers: {', '.join(overperformers[:3])}")
        if underperformers:
            insights.append(f"Underperformers: {', '.join(underperformers[:3])}")
        
        # Index analysis
        top_sli = max(cpr_metrics, key=lambda x: x.sli)
        top_bsi = max(cpr_metrics, key=lambda x: x.bsi)
        top_ingram = max(cpr_metrics, key=lambda x: x.ingram)
        
        insights.append(f"Strongest lineup: {top_sli.team_name} (SLI: {top_sli.sli:.3f})")
        insights.append(f"Deepest bench: {top_bsi.team_name} (BSI: {top_bsi.sli:.3f})")
        insights.append(f"Healthiest roster: {top_ingram.team_name} (Ingram: {top_ingram.ingram:.3f})")
        
        return insights
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update CPR weights"""
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"New weights sum to {total_weight}, normalizing to 1.0")
            for key in new_weights:
                new_weights[key] = new_weights[key] / total_weight
        
        self.weights.update(new_weights)
        logger.info(f"CPR weights updated: {self.weights}")
    
    def get_weight_explanation(self) -> str:
        """Get explanation of current CPR weights"""
        explanations = {
            'sli': 'Strength of Lineup Index - Starter performance and scoring',
            'bsi': 'Bench Strength Index - Depth and backup quality',
            'smi': 'Schedule Momentum Index - Recent performance trends',
            'ingram': 'Ingram Index - Player health and availability',
            'alvarado': 'Alvarado Index - Performance consistency',
            'zion': 'Zion Index - Explosive play potential'
        }
        
        explanation = "CPR Components:\n"
        for component, weight in self.weights.items():
            desc = explanations.get(component, component.upper())
            explanation += f"  {desc}: {weight:.0%}\n"
        
        return explanation
