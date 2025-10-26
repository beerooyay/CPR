"""Shared utilities for CPR-NFL system"""
import statistics
import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def calculate_gini_coefficient(values: List[float]) -> float:
    """Calculate Gini coefficient for measuring inequality"""
    if not values:
        return 0.0
    
    # Sort values
    sorted_values = sorted(values)
    n = len(values)
    
    # Calculate Gini coefficient
    cumulative_sum = 0
    for i, value in enumerate(sorted_values, 1):
        cumulative_sum += (n + 1 - i) * value
    
    sum_values = sum(sorted_values)
    if sum_values == 0:
        return 0.0
    
    gini = (2 * cumulative_sum) / (n * sum_values) - (n + 1) / n
    return max(0.0, min(gini, 1.0))

def calculate_percentile(values: List[float], target_value: float) -> float:
    """Calculate percentile rank of target value in list"""
    if not values:
        return 50.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    # Find rank of target value
    rank = sum(1 for v in sorted_values if v < target_value)
    
    # Handle ties
    ties = sum(1 for v in sorted_values if v == target_value)
    
    percentile = (rank + 0.5 * ties) / n * 100
    return max(0.0, min(percentile, 100.0))

def normalize_values(values: List[float], min_val: float = 0.0, max_val: float = 1.0) -> List[float]:
    """Normalize values to specified range"""
    if not values:
        return []
    
    actual_min = min(values)
    actual_max = max(values)
    
    if actual_max == actual_min:
        return [min_val] * len(values)
    
    normalized = []
    for value in values:
        norm_val = (value - actual_min) / (actual_max - actual_min)
        scaled_val = min_val + norm_val * (max_val - min_val)
        normalized.append(scaled_val)
    
    return normalized

def calculate_moving_average(values: List[float], window_size: int) -> List[float]:
    """Calculate moving average for values"""
    if not values or window_size <= 0:
        return []
    
    moving_averages = []
    for i in range(len(values)):
        start_idx = max(0, i - window_size + 1)
        window = values[start_idx:i + 1]
        avg = statistics.mean(window)
        moving_averages.append(avg)
    
    return moving_averages

def calculate_trend(values: List[float]) -> str:
    """Calculate trend direction from values"""
    if len(values) < 2:
        return "stable"
    
    # Simple linear regression to determine trend
    n = len(values)
    x_values = list(range(n))
    
    # Calculate slope
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(values)
    
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    
    if denominator == 0:
        return "stable"
    
    slope = numerator / denominator
    
    # Determine trend based on slope
    if slope > 0.1:
        return "rising"
    elif slope < -0.1:
        return "falling"
    else:
        return "stable"

def format_number(value: float, decimal_places: int = 2) -> str:
    """Format number with specified decimal places"""
    if value is None:
        return "N/A"
    
    if abs(value) >= 1000000:
        return f"{value/1000000:.{decimal_places}f}M"
    elif abs(value) >= 1000:
        return f"{value/1000:.{decimal_places}f}K"
    else:
        return f"{value:.{decimal_places}f}"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    if denominator == 0:
        return default
    return numerator / denominator

def calculate_z_score(value: float, mean: float, std_dev: float) -> float:
    """Calculate z-score for value"""
    if std_dev == 0:
        return 0.0
    return (value - mean) / std_dev

def get_outlier_bounds(values: List[float], multiplier: float = 1.5) -> tuple[float, float]:
    """Calculate outlier bounds using IQR method"""
    if not values:
        return (0.0, 0.0)
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    # Calculate quartiles
    q1_idx = n // 4
    q3_idx = 3 * n // 4
    
    q1 = sorted_values[q1_idx]
    q3 = sorted_values[q3_idx]
    
    iqr = q3 - q1
    
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    
    return (lower_bound, upper_bound)

def remove_outliers(values: List[float], multiplier: float = 1.5) -> List[float]:
    """Remove outliers from values list"""
    if not values:
        return []
    
    lower_bound, upper_bound = get_outlier_bounds(values, multiplier)
    
    filtered_values = [v for v in values if lower_bound <= v <= upper_bound]
    return filtered_values

def calculate_correlation(x_values: List[float], y_values: List[float]) -> float:
    """Calculate Pearson correlation coefficient"""
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return 0.0
    
    n = len(x_values)
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)
    
    # Calculate covariance and variances
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    x_variance = sum((x - x_mean) ** 2 for x in x_values)
    y_variance = sum((y - y_mean) ** 2 for y in y_values)
    
    if x_variance == 0 or y_variance == 0:
        return 0.0
    
    correlation = covariance / math.sqrt(x_variance * y_variance)
    return max(-1.0, min(correlation, 1.0))

def rank_values(values: List[float], descending: bool = True) -> List[int]:
    """Rank values in list"""
    if not values:
        return []
    
    # Create list of (value, original_index) tuples
    indexed_values = [(value, i) for i, value in enumerate(values)]
    
    # Sort by value
    sorted_values = sorted(indexed_values, key=lambda x: x[0], reverse=descending)
    
    # Assign ranks
    ranks = [0] * len(values)
    for rank, (_, original_index) in enumerate(sorted_values, 1):
        ranks[original_index] = rank
    
    return ranks

def calculate_percent_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change"""
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    
    return ((new_value - old_value) / old_value) * 100

def round_to_nearest(value: float, nearest: float = 0.1) -> float:
    """Round value to nearest specified increment"""
    if nearest == 0:
        return value
    
    return round(value / nearest) * nearest

def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to specified range"""
    return max(min_val, min(value, max_val))

def weighted_average(values: List[float], weights: List[float]) -> float:
    """Calculate weighted average"""
    if not values or not weights or len(values) != len(weights):
        return 0.0
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight

def exponential_smoothing(values: List[float], alpha: float = 0.3) -> List[float]:
    """Apply exponential smoothing to values"""
    if not values:
        return []
    
    if not 0 <= alpha <= 1:
        raise ValueError("Alpha must be between 0 and 1")
    
    smoothed = [values[0]]  # Start with first value
    
    for i in range(1, len(values)):
        smoothed_value = alpha * values[i] + (1 - alpha) * smoothed[i - 1]
        smoothed.append(smoothed_value)
    
    return smoothed

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def get_time_ago(timestamp: datetime) -> str:
    """Get human readable time ago string"""
    now = datetime.now()
    delta = now - timestamp
    
    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes}m ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    elif delta < timedelta(weeks=1):
        days = delta.days
        return f"{days}d ago"
    else:
        weeks = delta.days // 7
        return f"{weeks}w ago"

def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """Validate configuration has required keys"""
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        logger.error(f"Missing required config keys: {missing_keys}")
        return False
    
    return True

def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two configuration dictionaries"""
    merged = base_config.copy()
    merged.update(override_config)
    return merged

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying functions on failure"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator

def cache_result(ttl_seconds: int = 300):
    """Decorator for caching function results"""
    cache = {}
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = str(args) + str(sorted(kwargs.items()))
            current_time = datetime.now().timestamp()
            
            # Check cache
            if cache_key in cache:
                timestamp, result = cache[cache_key]
                if current_time - timestamp < ttl_seconds:
                    return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (current_time, result)
            
            return result
        return wrapper
    return decorator

def sanitize_string(text: str) -> str:
    """Sanitize string for safe storage/display"""
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'", '/', '\\']
    sanitized = text
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Remove extra whitespace
    sanitized = ' '.join(sanitized.split())
    
    return sanitized.strip()

def generate_id() -> str:
    """Generate unique ID"""
    import uuid
    return str(uuid.uuid4())[:8]

def deep_merge_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result
