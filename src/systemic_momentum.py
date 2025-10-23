"""
SMI (Systemic Momentum Index)
Novel metric for fantasy basketball: measures momentum propagation through teammate networks
"""
import numpy as np
from collections import defaultdict

def detect_teammate_pairs(players):
    """
    Detect which players on a fantasy roster are real-life teammates

    Args:
        players: list of player dicts with 'name' and 'nba_team' (real NBA team)

    Returns:
        list of teammate pairs: [(player1, player2, nba_team), ...]
    """
    # Group players by real NBA team
    nba_teams = defaultdict(list)

    for player in players:
        nba_team = player.get('nba_team') # e.g., "GSW", "NOP", "SAS"
        if nba_team:
            nba_teams[nba_team].append(player)

    # Find pairs
    pairs = []
    for nba_team, teammates in nba_teams.items():
        if len(teammates) >= 2:
            # All combinations of teammates
            for i in range(len(teammates)):
                for j in range(i + 1, len(teammates)):
                    pairs.append((teammates[i], teammates[j], nba_team))

    return pairs

def calculate_correlation_risk(player1_game_nivs, player2_game_nivs):
    """
    Calculate correlation between two teammates' game-by-game NIVs

    High correlation = high risk (both fail together)
    Low correlation = diversification

    Args:
        player1_game_nivs: list of NIVs for player 1
        player2_game_nivs: list of NIVs for player 2

    Returns:
        float: correlation coefficient (-1 to 1)
    """
    if len(player1_game_nivs) < 5 or len(player2_game_nivs) < 5:
        return 0.0 # Not enough data

    # Match up games (take minimum length)
    n = min(len(player1_game_nivs), len(player2_game_nivs))
    p1_nivs = player1_game_nivs[:n]
    p2_nivs = player2_game_nivs[:n]

    # Calculate Pearson correlation
    correlation = np.corrcoef(p1_nivs, p2_nivs)[0, 1]

    return correlation if not np.isnan(correlation) else 0.0

def calculate_smi_score(players, use_entropy=False):
    """
    Calculate Systemic Momentum Index for a fantasy roster

    This is the NOVEL metric that no fantasy platform uses!

    Logic:
    - If you have 2+ players from same NBA team, their stats are correlated
    - High correlation = concentration risk (both bad when team is bad)
    - Low correlation = diversification benefit

    Args:
        players: list of player dicts with 'nba_team' and optionally 'game_nivs'
        use_entropy: if True, use game-by-game NIVs to calculate correlation

    Returns:
        float: SMI score (positive = benefit, negative = risk)
    """
    pairs = detect_teammate_pairs(players)

    if not pairs:
        return 0.0 # No teammate pairs = no correlation risk

    if not use_entropy:
        # Simple version: just count pairs and apply small penalty
        # More pairs = more concentration risk
        num_pairs = len(pairs)
        return -0.05 * num_pairs # Small penalty per pair

    # Advanced version: calculate actual correlation from game-by-game data
    total_correlation = 0.0
    valid_pairs = 0

    for player1, player2, nba_team in pairs:
        p1_game_nivs = player1.get('game_nivs', [])
        p2_game_nivs = player2.get('game_nivs', [])

        if len(p1_game_nivs) >= 5 and len(p2_game_nivs) >= 5:
            correlation = calculate_correlation_risk(p1_game_nivs, p2_game_nivs)
            total_correlation += correlation
            valid_pairs += 1

    if valid_pairs == 0:
        return -0.05 * len(pairs) # Fallback to simple version

    # Average correlation across all pairs
    avg_correlation = total_correlation / valid_pairs

    # Convert to SMI score
    # High positive correlation = risk (penalty)
    # Low/negative correlation = diversification (bonus)
    if avg_correlation > 0.5:
        # High correlation = concentration risk
        smi_score = -avg_correlation * 0.15 # Up to -15% penalty
    elif avg_correlation < -0.2:
        # Negative correlation = diversification benefit (rare but valuable)
        smi_score = abs(avg_correlation) * 0.10 # Up to +10% bonus
    else:
        # Moderate correlation = neutral
        smi_score = 0.0

    return smi_score

def get_teammate_pairs_summary(players):
    """
    Get a human-readable summary of teammate pairs on roster

    Args:
        players: list of player dicts

    Returns:
        dict with summary info
    """
    pairs = detect_teammate_pairs(players)

    if not pairs:
        return {
            'num_pairs': 0,
            'pairs': [],
            'message': 'No real-life teammates on roster (fully diversified)'
        }

    pair_summaries = []
    for p1, p2, nba_team in pairs:
        pair_summaries.append({
            'player1': p1.get('name'),
            'player2': p2.get('name'),
            'nba_team': nba_team
        })

    return {
        'num_pairs': len(pairs),
        'pairs': pair_summaries,
        'message': f'{len(pairs)} teammate pair(s) detected'
    }

# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("SMI (Systemic Momentum Index)")
    print("Novel Fantasy Basketball Metric")
    print("=" * 70)

    # Example fantasy roster
    players = [
        {'name': 'Stephen Curry', 'nba_team': 'GSW', 'NIV': 5.2},
        {'name': 'Trey Murphy III', 'nba_team': 'NOP', 'NIV': 3.1},
        {'name': 'Zion Williamson', 'nba_team': 'NOP', 'NIV': 4.8}, # Teammate with Trey!
        {'name': 'Victor Wembanyama', 'nba_team': 'SAS', 'NIV': 5.5},
        {'name': 'Jamal Murray', 'nba_team': 'DEN', 'NIV': 3.9},
    ]

    # Detect pairs
    pairs = detect_teammate_pairs(players)
    print(f"\nTeammate Pairs Detected: {len(pairs)}")
    for p1, p2, team in pairs:
        print(f"- {p1['name']} + {p2['name']} (both {team})")

    # Calculate SMI
    smi_score = calculate_smi_score(players, use_entropy=False)
    print(f"\nSMI Score: {smi_score:.3f}")

    if smi_score < 0:
        print(f"Concentration risk: {abs(smi_score)*100:.1f}% penalty")
        print(f"(Having teammates increases correlation risk)")
    elif smi_score > 0:
        print(f"Diversification benefit: {smi_score*100:.1f}% bonus")
        print(f"(Negative correlation = hedge)")
    else:
        print(f"Neutral (no significant correlation)")

    # Get summary
    summary = get_teammate_pairs_summary(players)
    print(f"\nSummary: {summary['message']}")

    print("\n" + "=" * 70)
    print("SMI READY")
    print("=" * 70)
    print("\nThis is a NOVEL metric - no fantasy platform measures this!")
    print("It captures the momentum propagation through teammate networks.")
