#!/usr/bin/env python3
"""
LEGION TEAM EXTRACTION
Production module for extracting team names, logos, and metadata from Sleeper API
"""

import requests
from typing import Dict, List, Optional
import json
import os
try:
    from .utils import make_sleeper_request
except ImportError:
    from utils import make_sleeper_request

class LegionTeamExtractor:
    """Extract Legion Fantasy Football team data from Sleeper API"""
    
    def __init__(self, league_id: str = "1267325171853701120"):
        self.league_id = league_id
        self.avatar_base = "https://sleepercdn.com/avatars"
        self._teams_cache = None
    
    def get_teams(self, force_refresh: bool = False) -> List[Dict]:
        """Get all team data with caching"""
        if self._teams_cache is None or force_refresh:
            self._teams_cache = self._extract_teams()
        return self._teams_cache
    
    def _extract_teams(self) -> List[Dict]:
        """Extract team data from Sleeper API"""
        # Get rosters and users
        rosters = make_sleeper_request(f"league/{self.league_id}/rosters")
        users = make_sleeper_request(f"league/{self.league_id}/users")
        
        if not rosters or not users:
            raise Exception("Failed to fetch league data from Sleeper API")
        
        # Create user lookup
        user_lookup = {user['user_id']: user for user in users}
        
        teams = []
        for roster in rosters:
            roster_id = roster['roster_id']
            user_id = roster['owner_id']
            user_info = user_lookup.get(user_id, {})
            
            # Extract team name from user metadata
            user_metadata = user_info.get('metadata', {})
            team_name = user_metadata.get('team_name', f'Team {roster_id}')
            owner_name = user_info.get('display_name', 'Unknown')
            
            # Get avatar/logo
            avatar_id = user_info.get('avatar')
            logo_url = None
            if avatar_id:
                if avatar_id.startswith('http'):
                    logo_url = avatar_id
                else:
                    logo_url = f"{self.avatar_base}/thumbs/{avatar_id}"
            
            # Build team data
            team_data = {
                'roster_id': roster_id,
                'team_name': team_name,
                'owner_name': owner_name,
                'user_id': user_id,
                'logo_url': logo_url,
                'has_custom_name': not team_name.startswith('Team '),
                'record': {
                    'wins': roster.get('settings', {}).get('wins', 0),
                    'losses': roster.get('settings', {}).get('losses', 0),
                    'points_for': roster.get('settings', {}).get('fpts', 0),
                    'points_against': roster.get('settings', {}).get('fpts_against', 0)
                },
                'players': roster.get('players', []),
                'starters': roster.get('starters', [])
            }
            
            teams.append(team_data)
        
        return teams
    
    def get_team_by_roster_id(self, roster_id: int) -> Optional[Dict]:
        """Get specific team by roster ID"""
        teams = self.get_teams()
        for team in teams:
            if team['roster_id'] == roster_id:
                return team
        return None
    
    def get_team_display_name(self, roster_id: int) -> str:
        """Get display name for team (team name if custom, otherwise team + owner)"""
        team = self.get_team_by_roster_id(roster_id)
        if not team:
            return f"Team {roster_id}"
        
        if team['has_custom_name']:
            return team['team_name']
        else:
            return f"{team['team_name']} ({team['owner_name']})"
    
    def get_standings(self) -> List[Dict]:
        """Get current standings sorted by record"""
        teams = self.get_teams()
        return sorted(teams, 
                     key=lambda x: (x['record']['wins'], x['record']['points_for']), 
                     reverse=True)
    
    def save_teams_data(self, filepath: str = None) -> str:
        """Save teams data to JSON file"""
        if filepath is None:
            filepath = os.path.join(os.path.dirname(__file__), '..', 'data', 'legion_teams.json')
        
        teams = self.get_teams()
        
        # Create config format for easy access
        config = {
            'teams': teams,
            'config': {
                str(team['roster_id']): {
                    'team_name': team['team_name'],
                    'owner_name': team['owner_name'],
                    'logo_url': team['logo_url'],
                    'has_custom_name': team['has_custom_name'],
                    'record': team['record']
                }
                for team in teams
            },
            'metadata': {
                'league_id': self.league_id,
                'total_teams': len(teams),
                'teams_with_custom_names': sum(1 for team in teams if team['has_custom_name']),
                'last_updated': None  # Will be set by calling function
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        return filepath

# Convenience functions for easy import
def get_legion_teams(league_id: str = "1267325171853701120") -> List[Dict]:
    """Get all Legion teams"""
    extractor = LegionTeamExtractor(league_id)
    return extractor.get_teams()

def get_team_display_name(roster_id: int, league_id: str = "1267325171853701120") -> str:
    """Get display name for a team"""
    extractor = LegionTeamExtractor(league_id)
    return extractor.get_team_display_name(roster_id)

def get_legion_standings(league_id: str = "1267325171853701120") -> List[Dict]:
    """Get current Legion standings"""
    extractor = LegionTeamExtractor(league_id)
    return extractor.get_standings()
