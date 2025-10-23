"""
NIV-V (Entropy/Consistency) Calculator
The final piece of the Player Index puzzle
"""
import numpy as np
import statistics as stats
from nba_api.stats.endpoints import playergamelog

def calculate_game_niv(game_stats, league_means, league_stds):
    """
    Calculate NIV for a single game
    
    Args:
        game_stats: dict with FGM, FGA, FTM, FTA, 3PM, REB, AST, STL, BLK, TO, PTS
        league_means: dict of season average means
        league_stds: dict of season average stds
    
    Returns:
        float: NIV for this game
    """
    # Calculate FG/FT impact
    fg_avg = league_means.get('FG_PCT', 0.45)
    ft_avg = league_means.get('FT_PCT', 0.75)

    fg_imp = game_stats['FGM'] - fg_avg * game_stats['FGA']
    ft_imp = game_stats['FTM'] - ft_avg * game_stats['FTA']

    # Categories for z-scoring
    cats = {
        'FG_imp': fg_imp,
        'FT_imp': ft_imp,
        '3PM': game_stats['FG3M'],
        'REB': game_stats['REB'],
        'AST': game_stats['AST'],
        'STL': game_stats['STL'],
        'BLK': game_stats['BLK'],
        'TO': game_stats['TOV'],
        'PTS': game_stats['PTS']
    }

    # Calculate z-scores
    zsum = 0.0
    for cat, value in cats.items():
        if cat in league_means and cat in league_stds:
            mean = league_means[cat]
            std = league_stds[cat]
            if std > 0:
                z = (value - mean) / std
                if cat == 'TO':
                    zsum += -1.5 * z  # Penalty for turnovers
                else:
                    zsum += z

    return zsum

def calculate_niv_volatility(player_id, season='2024-25', league_means=None, league_stds=None, n_games=20):
    """
    Calculate NIV-V (Volatility Score) for a player
    
    This is the ENTROPY component!
    
    Args:
    player_id: NBA player ID
    season: Season (e.g., '2024-25')
    league_means: dict of league average stats
    league_stds: dict of league std devs
    n_games: Number of recent games to analyze
    
    Returns:
    dict with:
    - niv_v: volatility score (stdev of game NIVs)
    - ci: consistency index (-niv_v)
    - game_nivs: list of game NIVs
    """
    # Get player game log
    try:
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            timeout=30
        )
        
        df = gamelog.get_data_frames()[0]
        
        if df.empty or len(df) < 5:
            return None
        
        # Take last N games
        recent_games = df.head(n_games)
        
        # Calculate NIV for each game
        game_nivs = []
        for _, game in recent_games.iterrows():
            game_stats = {
                'FGM': game['FGM'],
                'FGA': game['FGA'],
                'FTM': game['FTM'],
                'FTA': game['FTA'],
                'FG3M': game['FG3M'],
                'REB': game['REB'],
                'AST': game['AST'],
                'STL': game['STL'],
                'BLK': game['BLK'],
                'TOV': game['TOV'],
                'PTS': game['PTS']
            }
            
            game_niv = calculate_game_niv(game_stats, league_means, league_stds)
            game_nivs.append(game_niv)
        
        # Calculate volatility (NIV-V)
        if len(game_nivs) < 5:
            return None
        
        niv_v = np.std(game_nivs)  # Standard deviation = volatility
        ci = -niv_v  # Consistency Index (inverse of volatility)
        
        return {
            'niv_v': niv_v,
            'ci': ci,
            'game_nivs': game_nivs,
            'avg_game_niv': np.mean(game_nivs),
            'n_games': len(game_nivs)
        }
    
    except Exception as e:
        print(f"Error calculating NIV-V for player {player_id}: {e}")
        return None

def calculate_consistency_index_z(all_player_cis):
    """
    Z-score the Consistency Index across all players
    
    Args:
    all_player_cis: list of CI values for all players
    
    Returns:
    dict mapping player_id to ci_z
    """
    if not all_player_cis:
        return {}
    
    # Calculate league mean and std
    ci_values = [p['ci'] for p in all_player_cis if p['ci'] is not None]
    
    if len(ci_values) < 2:
        return {}
    
    mean_ci = stats.mean(ci_values)
    std_ci = stats.pstdev(ci_values)
    
    if std_ci == 0:
        std_ci = 1.0
    
    # Z-score each player's CI
    ci_z_map = {}
    for p in all_player_cis:
        if p['ci'] is not None:
            ci_z = (p['ci'] - mean_ci) / std_ci
            ci_z_map[p['player_id']] = ci_z
    
    return ci_z_map

def apply_consistency_to_niv(niv_raw, ci_z, weight=0.1):
    """
    Apply consistency adjustment to NIV
    
    Formula: NIV_final = NIV_raw × (1 + weight × ci_z)
    
    Args:
    niv_raw: Raw NIV (sum of z-scores)
    ci_z: Z-scored consistency index
    weight: Multiplier weight (default 0.1 = ±10% adjustment)
    
    Returns:
    float: Adjusted NIV
    """
    return niv_raw * (1 + weight * ci_z)

# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("NIV-V (ENTROPY) CALCULATOR")
    print("=" * 70)

    # Example league averages (would come from season data)
    league_means = {
        'FG_PCT': 0.45,
        'FT_PCT': 0.75,
        'FG_imp': 0.0,
        'FT_imp': 0.0,
        '3PM': 1.5,
        'REB': 4.5,
        'AST': 2.5,
        'STL': 0.8,
        'BLK': 0.5,
        'TO': 1.5,
        'PTS': 11.0
    }

    league_stds = {
        'FG_imp': 2.0,
        'FT_imp': 1.0,
        '3PM': 1.2,
        'REB': 2.5,
        'AST': 2.0,
        'STL': 0.6,
        'BLK': 0.5,
        'TO': 1.0,
        'PTS': 6.0
    }

    # Test with Stephen Curry
    print("\n Testing with Stephen Curry (player_id: 201939)")

    result = calculate_niv_volatility(
        player_id='201939',
        season='2024-25',
        league_means=league_means,
        league_stds=league_stds,
        n_games=20
    )

    if result:
        print(f"\n Results:")
        print(f" Games analyzed: {result['n_games']}")
        print(f" Average game NIV: {result['avg_game_niv']:.2f}")
        print(f" NIV-V (volatility): {result['niv_v']:.3f}")
        print(f" CI (consistency): {result['ci']:.3f}")
        print(f"\n Game NIVs: {[f'{x:.2f}' for x in result['game_nivs'][:5]]}...")

        # Example: Apply to NIV
        niv_raw = 5.2  # Example raw NIV
        ci_z = 1.5  # Example z-scored CI (very consistent)

        niv_final = apply_consistency_to_niv(niv_raw, ci_z)

        print(f"\n NIV Adjustment Example:")
        print(f" NIV_raw: {niv_raw:.2f}")
        print(f" CI_z: {ci_z:.2f} (very consistent)")
        print(f" NIV_final: {niv_final:.2f} (+{((niv_final/niv_raw - 1) * 100):.1f}% boost)")
    else:
        print(" Could not calculate NIV-V (insufficient data or API error)")

    print("\n" + "=" * 70)
    print(" ENTROPY LAYER READY")
    print("=" * 70)
    print("\nThis is the first mathematically rigorous consistency metric")
    print("in fantasy basketball history.")
