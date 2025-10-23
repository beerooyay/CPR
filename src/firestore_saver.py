import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firestore():
    """Initialize Firestore connection using application default credentials."""
    if not firebase_admin._apps:
        # Use application default credentials (works in Docker/Cloud Run)
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': 'cpr-app-54c15',
        })
    return firestore.client()

def save_cpr_data(cpr_data, season='2025'):
    """Save team-level CPR metrics to Firestore."""
    db = initialize_firestore()
    print(f"🔥 Saving CPR data for {len(cpr_data)} teams to Firestore...")
    batch = db.batch()

    for team_metrics in cpr_data:
        team_id = team_metrics['team_key']
        team_ref = db.collection('teams').document(team_id)
        season_ref = team_ref.collection('seasons').document(f'season_{season}')
        
        # Set team name on the main document
        batch.set(team_ref, {'team_name': team_metrics['team']}, merge=True)
        
        # Set season-specific metrics
        batch.set(season_ref, team_metrics, merge=True)

    batch.commit()
    print(f"  -> ✅ Successfully saved CPR data.")

def save_player_data(player_data, season='2025'):
    """Save player-level data to Firestore."""
    db = initialize_firestore()
    print(f"🔥 Saving data for {len(player_data)} players to Firestore...")
    batch = db.batch()

    for player in player_data:
        player_name = player.pop('player_name')
        player_ref = db.collection('players').document(player_name)
        season_ref = player_ref.collection('seasons').document(f'season_{season}')
        batch.set(season_ref, player, merge=True)

    batch.commit()
    print(f"  -> ✅ Successfully saved player data.")

def save_league_metrics(metrics, season='2025'):
    """Save league-wide metrics to Firestore."""
    db = initialize_firestore()
    print(f"🔥 Saving league metrics to Firestore...")
    doc_ref = db.collection('league_metrics').document(f'season_{season}')
    doc_ref.set(metrics, merge=True)
    print(f"  -> ✅ Successfully saved league metrics.")
