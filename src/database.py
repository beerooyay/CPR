"""Database operations for CPR-NFL system"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    from google.cloud.firestore import Client as FirestoreClient
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase Admin SDK not available")

from models import CPRMetrics, NIVMetrics, Team, Player, LeagueAnalysis

logger = logging.getLogger(__name__)

class Database:
    """Database interface for CPR-NFL system"""
    
    def __init__(self, project_id: str = None, credentials_path: str = None):
        self.project_id = project_id or os.getenv('FIREBASE_PROJECT_ID', 'cpr-nfl')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.db = None
        self._initialized = False
        
        if FIREBASE_AVAILABLE:
            self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                if self.credentials_path and os.path.exists(self.credentials_path):
                    cred = credentials.Certificate(self.credentials_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': self.project_id
                    })
                    logger.info(f"Firebase initialized with credentials file: {self.credentials_path}")
                else:
                    # Try application default credentials
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred, {
                        'projectId': self.project_id
                    })
                    logger.info("Firebase initialized with application default credentials")
            
            self.db = firestore.client()
            self._initialized = True
            logger.info(f"Connected to Firestore database: {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self._initialized = False
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._initialized and self.db is not None
    
    def save_cpr_rankings(self, league_id: str, rankings: List[CPRMetrics]) -> bool:
        """Save CPR rankings to database"""
        if not self.is_connected:
            logger.warning("Database not connected, skipping save")
            return False
        
        try:
            # Save to CPR rankings collection
            rankings_data = {
                'league_id': league_id,
                'rankings': [self._serialize_cpr_metrics(r) for r in rankings],
                'calculation_timestamp': datetime.now().isoformat(),
                'total_teams': len(rankings)
            }
            
            # Save as latest document
            latest_ref = self.db.collection('cpr_rankings').document('latest')
            latest_ref.set(rankings_data)
            
            # Save with timestamp for history
            timestamp_ref = self.db.collection('cpr_rankings').document(
                datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            timestamp_ref.set(rankings_data)
            
            # Save individual team data
            for ranking in rankings:
                team_ref = self.db.collection('teams').document(ranking.team_id)
                team_data = self._serialize_cpr_metrics(ranking)
                team_data.update({
                    'league_id': league_id,
                    'updated_at': datetime.now().isoformat(),
                    'data_source': 'cpr-nfl-engine'
                })
                team_ref.set(team_data, merge=True)
            
            logger.info(f"Saved CPR rankings for {len(rankings)} teams")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save CPR rankings: {e}")
            return False
    
    def get_cpr_rankings(self, league_id: str, latest_only: bool = True) -> Optional[Dict[str, Any]]:
        """Get CPR rankings from database"""
        if not self.is_connected:
            logger.warning("Database not connected")
            return None
        
        try:
            if latest_only:
                doc_ref = self.db.collection('cpr_rankings').document('latest')
                doc = doc_ref.get()
                
                if doc.exists:
                    return doc.to_dict()
                else:
                    logger.warning("No CPR rankings found")
                    return None
            else:
                # Get historical rankings
                docs = self.db.collection('cpr_rankings').order_by(
                    'calculation_timestamp', direction='DESCENDING'
                ).limit(10).get()
                
                return [doc.to_dict() for doc in docs]
                
        except Exception as e:
            logger.error(f"Failed to get CPR rankings: {e}")
            return None
    
    def save_niv_data(self, league_id: str, niv_rankings: List[NIVMetrics]) -> bool:
        """Save NIV data to database"""
        if not self.is_connected:
            logger.warning("Database not connected, skipping save")
            return False
        
        try:
            # Save to NIV collection
            niv_data = {
                'league_id': league_id,
                'player_rankings': [self._serialize_niv_metrics(n) for n in niv_rankings],
                'calculation_timestamp': datetime.now().isoformat(),
                'total_players': len(niv_rankings)
            }
            
            # Save as latest
            latest_ref = self.db.collection('niv_rankings').document('latest')
            latest_ref.set(niv_data)
            
            # Save with timestamp for history
            timestamp_ref = self.db.collection('niv_rankings').document(
                datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            timestamp_ref.set(niv_data)
            
            # Save individual player data
            for niv in niv_rankings:
                player_ref = self.db.collection('players').document(niv.player_id)
                player_data = self._serialize_niv_metrics(niv)
                player_data.update({
                    'league_id': league_id,
                    'updated_at': datetime.now().isoformat(),
                    'data_source': 'cpr-nfl-engine'
                })
                player_ref.set(player_data, merge=True)
            
            logger.info(f"Saved NIV data for {len(niv_rankings)} players")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save NIV data: {e}")
            return False
    
    def get_niv_data(self, league_id: str, latest_only: bool = True) -> Optional[Dict[str, Any]]:
        """Get NIV data from database"""
        if not self.is_connected:
            logger.warning("Database not connected")
            return None
        
        try:
            if latest_only:
                doc_ref = self.db.collection('niv_rankings').document('latest')
                doc = doc_ref.get()
                
                if doc.exists:
                    return doc.to_dict()
                else:
                    logger.warning("No NIV data found")
                    return None
            else:
                # Get historical NIV data
                docs = self.db.collection('niv_rankings').order_by(
                    'calculation_timestamp', direction='DESCENDING'
                ).limit(10).get()
                
                return [doc.to_dict() for doc in docs]
                
        except Exception as e:
            logger.error(f"Failed to get NIV data: {e}")
            return None
    
    def save_league_data(self, league_id: str, league_analysis: LeagueAnalysis) -> bool:
        """Save complete league analysis"""
        if not self.is_connected:
            logger.warning("Database not connected, skipping save")
            return False
        
        try:
            # Save league info
            if league_analysis.league_info:
                league_ref = self.db.collection('leagues').document(league_id)
                league_data = {
                    'league_id': league_analysis.league_info.league_id,
                    'name': league_analysis.league_info.name,
                    'season': league_analysis.league_info.season,
                    'current_week': league_analysis.league_info.current_week,
                    'num_teams': league_analysis.league_info.num_teams,
                    'updated_at': datetime.now().isoformat()
                }
                league_ref.set(league_data, merge=True)
            
            # Save teams
            for team in league_analysis.teams:
                team_ref = self.db.collection('teams').document(team.team_id)
                team_data = {
                    'team_id': team.team_id,
                    'team_name': team.team_name,
                    'owner_name': team.owner_name,
                    'wins': team.wins,
                    'losses': team.losses,
                    'ties': team.ties,
                    'fpts': team.fpts,
                    'fpts_against': team.fpts_against,
                    'roster': team.roster,
                    'starters': team.starters,
                    'bench': team.bench,
                    'league_id': league_id,
                    'updated_at': datetime.now().isoformat()
                }
                team_ref.set(team_data, merge=True)
            
            # Save players
            for player_id, player in league_analysis.players.items():
                player_ref = self.db.collection('players').document(player_id)
                player_data = {
                    'player_id': player.player_id,
                    'name': player.name,
                    'position': player.position.value,
                    'team': player.team,
                    'status': player.status,
                    'injury_status': player.injury_status.value,
                    'league_id': league_id,
                    'updated_at': datetime.now().isoformat()
                }
                player_ref.set(player_data, merge=True)
            
            logger.info(f"Saved league data for {league_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save league data: {e}")
            return False
    
    def get_team_history(self, team_id: str, weeks: int = 8) -> List[Dict[str, Any]]:
        """Get team CPR history"""
        if not self.is_connected:
            return []
        
        try:
            # Get historical CPR data for team
            cutoff_date = datetime.now() - timedelta(weeks=weeks)
            
            docs = self.db.collection('cpr_rankings').where(
                'calculation_timestamp', '>=', cutoff_date.isoformat()
            ).order_by('calculation_timestamp', direction='DESCENDING').get()
            
            team_history = []
            for doc in docs:
                data = doc.to_dict()
                for ranking in data.get('rankings', []):
                    if ranking.get('team_id') == team_id:
                        team_history.append({
                            'timestamp': data.get('calculation_timestamp'),
                            'cpr': ranking.get('cpr'),
                            'rank': ranking.get('rank'),
                            'sli': ranking.get('sli'),
                            'bsi': ranking.get('bsi'),
                            'smi': ranking.get('smi'),
                            'ingram': ranking.get('ingram'),
                            'alvarado': ranking.get('alvarado'),
                            'zion': ranking.get('zion')
                        })
                        break
            
            return team_history
            
        except Exception as e:
            logger.error(f"Failed to get team history: {e}")
            return []
    
    def get_league_standings(self, league_id: str) -> List[Dict[str, Any]]:
        """Get current league standings"""
        if not self.is_connected:
            return []
        
        try:
            docs = self.db.collection('teams').where(
                'league_id', '==', league_id
            ).order_by('wins', direction='DESCENDING').get()
            
            standings = []
            for doc in docs:
                team_data = doc.to_dict()
                standings.append(team_data)
            
            return standings
            
        except Exception as e:
            logger.error(f"Failed to get league standings: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old historical data"""
        if not self.is_connected:
            return False
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean up old CPR rankings
            cpr_docs = self.db.collection('cpr_rankings').where(
                'calculation_timestamp', '<', cutoff_date.isoformat()
            ).get()
            
            deleted_count = 0
            for doc in cpr_docs:
                if doc.id != 'latest':  # Don't delete latest
                    doc.reference.delete()
                    deleted_count += 1
            
            # Clean up old NIV rankings
            niv_docs = self.db.collection('niv_rankings').where(
                'calculation_timestamp', '<', cutoff_date.isoformat()
            ).get()
            
            for doc in niv_docs:
                if doc.id != 'latest':  # Don't delete latest
                    doc.reference.delete()
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    def _serialize_cpr_metrics(self, metrics: CPRMetrics) -> Dict[str, Any]:
        """Convert CPRMetrics to dictionary"""
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
    
    def _serialize_niv_metrics(self, metrics: NIVMetrics) -> Dict[str, Any]:
        """Convert NIVMetrics to dictionary"""
        return {
            'player_id': metrics.player_id,
            'name': metrics.name,
            'position': metrics.position.value,
            'niv': round(metrics.niv, 2),
            'positional_niv': round(metrics.positional_niv, 2),
            'market_niv': round(metrics.market_niv, 2),
            'consistency_niv': round(metrics.consistency_niv, 2),
            'explosive_niv': round(metrics.explosive_niv, 2),
            'team_id': metrics.team_id,
            'rank': metrics.rank,
            'positional_rank': metrics.positional_rank,
            'niv_tier': metrics.niv_tier
        }

class LocalDatabase(Database):
    """Local file-based database for development/testing"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Using local database: {data_dir}")
    
    @property
    def is_connected(self) -> bool:
        return True
    
    def save_cpr_rankings(self, league_id: str, rankings: List[CPRMetrics]) -> bool:
        """Save CPR rankings to local file"""
        try:
            rankings_data = {
                'league_id': league_id,
                'rankings': [self._serialize_cpr_metrics(r) for r in rankings],
                'calculation_timestamp': datetime.now().isoformat(),
                'total_teams': len(rankings)
            }
            
            # Save latest
            latest_path = os.path.join(self.data_dir, 'cpr_rankings_latest.json')
            with open(latest_path, 'w') as f:
                json.dump(rankings_data, f, indent=2)
            
            # Save with timestamp
            timestamp_path = os.path.join(
                self.data_dir, 
                f'cpr_rankings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            with open(timestamp_path, 'w') as f:
                json.dump(rankings_data, f, indent=2)
            
            logger.info(f"Saved CPR rankings to local files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save CPR rankings locally: {e}")
            return False
    
    def get_cpr_rankings(self, league_id: str, latest_only: bool = True) -> Optional[Dict[str, Any]]:
        """Get CPR rankings from local file"""
        try:
            latest_path = os.path.join(self.data_dir, 'cpr_rankings_latest.json')
            
            if os.path.exists(latest_path):
                with open(latest_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("No local CPR rankings found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get local CPR rankings: {e}")
            return None
    
    def save_niv_data(self, league_id: str, niv_rankings: List[NIVMetrics]) -> bool:
        """Save NIV data to local file"""
        try:
            niv_data = {
                'league_id': league_id,
                'player_rankings': [self._serialize_niv_metrics(n) for n in niv_rankings],
                'calculation_timestamp': datetime.now().isoformat(),
                'total_players': len(niv_rankings)
            }
            
            # Save latest
            latest_path = os.path.join(self.data_dir, 'niv_rankings_latest.json')
            with open(latest_path, 'w') as f:
                json.dump(niv_data, f, indent=2)
            
            # Save with timestamp
            timestamp_path = os.path.join(
                self.data_dir, 
                f'niv_rankings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            with open(timestamp_path, 'w') as f:
                json.dump(niv_data, f, indent=2)
            
            logger.info(f"Saved NIV data to local files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save NIV data locally: {e}")
            return False
    
    def get_niv_data(self, league_id: str, latest_only: bool = True) -> Optional[Dict[str, Any]]:
        """Get NIV data from local file"""
        try:
            latest_path = os.path.join(self.data_dir, 'niv_rankings_latest.json')
            
            if os.path.exists(latest_path):
                with open(latest_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("No local NIV data found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get local NIV data: {e}")
            return None
