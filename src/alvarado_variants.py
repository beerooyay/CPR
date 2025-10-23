"""
Alvarado Index - Value Efficiency Metric
"""
import statistics as stats

def get_current_mode():
    """get current alvarado mode"""
    return "hybrid"  # default to hybrid mode

def calculate_alvarado_salary(players, shapley_values=None):
    """
    Option A: Salary-based Alvarado Index
    Formula: AI = shapley_value / (salary / league_avg_salary)²
    """
    league_avg_salary = stats.mean([p["salary"] for p in players if p["salary"] > 0])
    
    results = []
    for p in players:
        if p["salary"] > 0:
            salary_multiplier = p["salary"] / league_avg_salary
            
            # Use Shapley if available, otherwise use NIV as proxy
            impact = shapley_values.get(p["name"], p["NIV"]) if shapley_values else p["NIV"]
            
            if salary_multiplier > 0:
                alvarado = impact / (salary_multiplier ** 2)
                results.append({"player": p["name"], "alvarado": alvarado})
    
    return results

def calculate_alvarado_performance(players, shapley_values=None):
    """
    Option B: Performance-based Alvarado Index
    Formula: AI = shapley_value / (NIV / league_avg_NIV)²
    """
    league_avg_niv = stats.mean([p["NIV"] for p in players])
    
    results = []
    for p in players:
        if p["NIV"] > 0:
            niv_multiplier = p["NIV"] / league_avg_niv
            
            # Use Shapley if available, otherwise use NIV as proxy
            impact = shapley_values.get(p["name"], p["NIV"]) if shapley_values else p["NIV"]
            
            if niv_multiplier > 0:
                alvarado = impact / (niv_multiplier ** 2)
                results.append({"player": p["name"], "alvarado": alvarado})
    
    return results

def calculate_alvarado_hybrid(players, shapley_values=None):
    """
    Option C: Hybrid Alvarado Index (RECOMMENDED)
    Formula: AI = shapley_value / [(NIV_z + salary_z) / 2]²
    
    This is the killer: combines both statistical output and economic cost
    """
    # Calculate z-scores for NIV
    niv_values = [p["NIV"] for p in players]
    niv_mean = stats.mean(niv_values)
    niv_std = stats.pstdev(niv_values) or 1.0
    
    # Calculate z-scores for salary
    salary_values = [p["salary"] for p in players if p["salary"] > 0]
    salary_mean = stats.mean(salary_values)
    salary_std = stats.pstdev(salary_values) or 1.0
    
    results = []
    for p in players:
        if p["salary"] > 0 and p["NIV"] > 0:
            # Z-score normalization
            niv_z = (p["NIV"] - niv_mean) / niv_std
            salary_z = (p["salary"] - salary_mean) / salary_std
            
            # Combined z-score
            combined_z = (niv_z + salary_z) / 2
            
            # Use Shapley if available, otherwise use NIV as proxy
            impact = shapley_values.get(p["name"], p["NIV"]) if shapley_values else p["NIV"]
            
            # Alvarado = impact / (combined_z)²
            # Add small epsilon to avoid division by zero
            denominator = (combined_z ** 2) if abs(combined_z) > 0.1 else 0.01
            alvarado = impact / denominator
            
            results.append({"player": p["name"], "alvarado": alvarado, "niv_z": niv_z, "salary_z": salary_z})
    
    return results

def calculate_team_alvarado(team_players, mode="hybrid", shapley_values=None):
    """calculate team-level alvarado index"""
    if mode == "salary":
        results = calculate_alvarado_salary(team_players, shapley_values)
    elif mode == "performance":
        results = calculate_alvarado_performance(team_players, shapley_values)
    else:  # hybrid default
        results = calculate_alvarado_hybrid(team_players, shapley_values)
    
    return stats.mean([r["alvarado"] for r in results]) if results else 0.0


