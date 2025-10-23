"""Unified Field Mapping System
Solves the field name chaos between ESPN, NBA API, and CPR
"""

# master field mapping
FIELD_MAP = {
    # stats fields
    'points': ['PTS', 'pts', 'points', 'POINTS'],
    'rebounds': ['REB', 'reb', 'rebounds', 'TRB', 'REBOUNDS'],
    'assists': ['AST', 'ast', 'assists', 'ASSISTS'],
    'steals': ['STL', 'stl', 'steals', 'STEALS'],
    'blocks': ['BLK', 'blk', 'blocks', 'BLOCKS'],
    'turnovers': ['TO', 'TOV', 'tov', 'turnovers', 'TURNOVERS'],
    'threes': ['3PM', '3M', 'TPM', 'tpm', 'three_pm', 'FG3M'],
    'fgm': ['FGM', 'fgm', 'field_goals_made'],
    'fga': ['FGA', 'fga', 'field_goals_attempted'],
    'ftm': ['FTM', 'ftm', 'free_throws_made'],
    'fta': ['FTA', 'fta', 'free_throws_attempted'],
    
    # team fields
    'fantasy_team': ['team', 'TEAM', 'team_name', 'fantasy_team'],
    'nba_team': ['nba_team', 'proTeam', 'TEAM_ABBREVIATION', 'real_team'],
    
    # player fields
    'name': ['player_name', 'name', 'NAME', 'player'],
    'position': ['position', 'pos', 'POS', 'player_position'],
    'injury': ['injuryStatus', 'injury_status', 'status', 'injured']
}

def normalize_data(raw_data):
    """normalize raw data to standard CPR format"""
    normalized = {}
    
    # map all fields to standard names
    for std_field, variants in FIELD_MAP.items():
        for variant in variants:
            if variant in raw_data:
                normalized[std_field] = raw_data[variant]
                break
    
    # ensure all required fields exist
    required = ['points', 'rebounds', 'assists', 'steals', 'blocks', 
                'turnovers', 'threes', 'fgm', 'fga', 'ftm', 'fta']
    for field in required:
        if field not in normalized:
            normalized[field] = 0
    
    return normalized

def espn_to_cpr(espn_data):
    """convert ESPN data format to CPR format"""
    return {
        'player_name': espn_data.get('name', ''),
        'team': espn_data.get('team', ''),
        'nba_team': espn_data.get('proTeam', ''),
        'player_info': espn_data.get('position', '') + '/' + espn_data.get('injuryStatus', 'HEALTHY'),
        'PTS': espn_data.get('PTS', 0),
        'REB': espn_data.get('REB', 0),
        'AST': espn_data.get('AST', 0),
        'STL': espn_data.get('STL', 0),
        'BLK': espn_data.get('BLK', 0),
        'TO': espn_data.get('TO', 0),
        '3PM': espn_data.get('TPM', 0),
        'FGM': espn_data.get('FGM', 0),
        'FGA': espn_data.get('FGA', 0),
        'FTM': espn_data.get('FTM', 0),
        'FTA': espn_data.get('FTA', 0),
        'salary': 10000000  # default $10M
    }

def cpr_to_db(cpr_data):
    """convert CPR format to database format"""
    return {
        'player_name': cpr_data.get('name', ''),
        'fgm': cpr_data.get('FGM', 0),
        'fga': cpr_data.get('FGA', 0),
        'ftm': cpr_data.get('FTM', 0),
        'fta': cpr_data.get('FTA', 0),
        'tpm': cpr_data.get('3PM', 0),
        'reb': cpr_data.get('REB', 0),
        'ast': cpr_data.get('AST', 0),
        'stl': cpr_data.get('STL', 0),
        'blk': cpr_data.get('BLK', 0),
        'tov': cpr_data.get('TO', 0),
        'pts': cpr_data.get('PTS', 0)
    }
