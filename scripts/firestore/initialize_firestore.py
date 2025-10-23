#!/usr/bin/env python3
"""
Initialize Firestore with CPR Data Model
"""
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURATION ---
SERVICE_ACCOUNT_KEY_PATH = "../../cpr-app-54c15-firebase-adminsdk-q9h9q-c867298811.json"


def initialize_firestore():
    """Initialize Firestore with the correct data model"""

    print("\n🔥 Initializing Firestore...")

    # Initialize Firebase Admin SDK
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # --- CREATE SEASONS ---
    print("\n📅 Creating seasons...")
    for year in range(2020, 2027):
        season_id = f"season_{year}"
        db.collection("seasons").document(season_id).set({
            "year": year,
            "name": f"{year-1}-{year} Season"
        })
        print(f"  ✓ {season_id}")

    # --- CREATE TEAMS ---
    print("\n🏆 Creating teams...")
    teams = [
        {"name": "Albuquerque Blue Rocks", "owner": "Matthew Webb"},
        {"name": "Austin Bleu's", "owner": "Joshua Musco"},
        {"name": "Normal Normals", "owner": "Grant Daigle"},
        {"name": "Phoenix Pharaohs", "owner": "Cole Spillman"},
        {"name": "Chinatown Emperors", "owner": "John Colletti"},
        {"name": "Los Angeles Ballers", "owner": "Kenny Chism"},
        {"name": "New York Rangers", "owner": "Kelechi Onunka"},
        {"name": "Baton Rouge Association", "owner": "Cody McManus"},
        {"name": "New Orleans Bounce", "owner": "Taylor Mayers"},
        {"name": "Kingston Captains", "owner": "Blaize Rouyea"}
    ]

    for team in teams:
        team_id = team["name"].lower().replace(" ", "-")
        db.collection("teams").document(team_id).set(team)
        print(f"  ✓ {team_id}")

    print("\n✅ Firestore initialized successfully!")


if __name__ == "__main__":
    initialize_firestore()
