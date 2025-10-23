"""
Fantasy Scoring System
Stores and applies league-specific scoring weights to calculate fantasy points
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "cpr_data.db"

# Your league's exact scoring settings
SCORING_WEIGHTS = {
    'FGM': 2,
    'FGA': -1,
    'FTM': 1,
    'FTA': -1,
    'TPM': 1,      # 3PM
    'REB': 1,
    'AST': 1.5,
    'STL': 2,
    'BLK': 2,
    'TO': -2,
    'PTS': 1,
    'DD': 2,       # Double-double
    'TD': 5,       # Triple-double
    'QD': 20       # Quadruple-double
}

def create_scoring_table():
    """Create league_scoring table in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS league_scoring (
        metric TEXT PRIMARY KEY,
        weight REAL NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def load_scoring_weights():
    """Insert scoring weights into database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for metric, weight in SCORING_WEIGHTS.items():
        cursor.execute("""
        INSERT OR REPLACE INTO league_scoring (metric, weight)
        VALUES (?, ?)
        """, (metric, weight))
    
    conn.commit()
    conn.close()

def get_scoring_weights():
    """Retrieve scoring weights from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    results = cursor.execute("SELECT metric, weight FROM league_scoring").fetchall()
    conn.close()
    
    return {metric: weight for metric, weight in results}

def calculate_fantasy_points(stats):
    """
    Calculate fantasy points from raw stats using league scoring
    
    Args:
        stats: dict with keys FGM, FGA, FTM, FTA, TPM, REB, AST, STL, BLK, TO, PTS
    
    Returns:
        float: total fantasy points
    """
    weights = get_scoring_weights()
    
    fantasy_points = 0.0
    
    # Basic stats
    fantasy_points += stats.get('FGM', 0) * weights.get('FGM', 0)
    fantasy_points += stats.get('FGA', 0) * weights.get('FGA', 0)
    fantasy_points += stats.get('FTM', 0) * weights.get('FTM', 0)
    fantasy_points += stats.get('FTA', 0) * weights.get('FTA', 0)
    fantasy_points += stats.get('TPM', 0) * weights.get('TPM', 0)
    fantasy_points += stats.get('REB', 0) * weights.get('REB', 0)
    fantasy_points += stats.get('AST', 0) * weights.get('AST', 0)
    fantasy_points += stats.get('STL', 0) * weights.get('STL', 0)
    fantasy_points += stats.get('BLK', 0) * weights.get('BLK', 0)
    fantasy_points += stats.get('TO', 0) * weights.get('TO', 0)
    fantasy_points += stats.get('PTS', 0) * weights.get('PTS', 0)
    
    # Bonuses (double-double, triple-double, quadruple-double)
    fantasy_points += stats.get('DD', 0) * weights.get('DD', 0)
    fantasy_points += stats.get('TD', 0) * weights.get('TD', 0)
    fantasy_points += stats.get('QD', 0) * weights.get('QD', 0)
    
    return fantasy_points

def detect_double_double(stats):
    """Detect if player achieved double-double"""
    categories = ['PTS', 'REB', 'AST', 'STL', 'BLK']
    double_digit_count = sum(1 for cat in categories if stats.get(cat, 0) >= 10)
    return 1 if double_digit_count >= 2 else 0

def detect_triple_double(stats):
    """Detect if player achieved triple-double"""
    categories = ['PTS', 'REB', 'AST', 'STL', 'BLK']
    double_digit_count = sum(1 for cat in categories if stats.get(cat, 0) >= 10)
    return 1 if double_digit_count >= 3 else 0

def detect_quadruple_double(stats):
    """Detect if player achieved quadruple-double"""
    categories = ['PTS', 'REB', 'AST', 'STL', 'BLK']
    double_digit_count = sum(1 for cat in categories if stats.get(cat, 0) >= 10)
    return 1 if double_digit_count >= 4 else 0

def calculate_fantasy_points_with_bonuses(stats):
    """Calculate fantasy points including detection of DD/TD/QD"""
    stats_copy = stats.copy()
    
    # Detect bonuses
    stats_copy['DD'] = detect_double_double(stats)
    stats_copy['TD'] = detect_triple_double(stats)
    stats_copy['QD'] = detect_quadruple_double(stats)
    
    return calculate_fantasy_points(stats_copy)

def initialize_scoring_system():
    """Setup scoring system in database"""
    print("Initializing scoring system...")
    create_scoring_table()
    load_scoring_weights()
    print("Scoring weights loaded:")
    for metric, weight in SCORING_WEIGHTS.items():
        print(f"  {metric}: {weight}")
    print("Complete.")

if __name__ == "__main__":
    print("=" * 70)
    print("Fantasy Scoring System - Machine Precision")
    print("=" * 70)
    
    # Initialize
    initialize_scoring_system()
    
    # Test calculation
    print("\nTest: Stephen Curry game (30 PTS, 5 REB, 6 AST, 2 STL, 10 FGM, 20 FGA, 8 FTM, 9 FTA, 4 3PM)")
    test_stats = {
        'FGM': 10,
        'FGA': 20,
        'FTM': 8,
        'FTA': 9,
        'TPM': 4,
        'REB': 5,
        'AST': 6,
        'STL': 2,
        'BLK': 0,
        'TO': 3,
        'PTS': 30
    }
    
    fp = calculate_fantasy_points_with_bonuses(test_stats)
    print(f"\nFantasy Points: {fp:.1f}")
    print(f"  (includes DD bonus: {detect_double_double(test_stats)})")
    
    print("\n" + "=" * 70)
    print("Scoring system ready for machine-precision calculation")
    print("=" * 70)
