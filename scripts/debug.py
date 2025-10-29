import sys
from pathlib import Path
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import Database

def inspect_data():
    """Fetches and inspects the latest CPR and NIV data from Firestore."""
    db = Database()
    if not db.is_connected:
        print("Could not connect to Firestore.")
        return

    print("--- inspecting niv_rankings ---")
    niv_data = db.get_niv_data("1267325171853701120")
    if niv_data:
        print(json.dumps(niv_data, indent=2))
    else:
        print("No NIV data found.")

    print("\n--- inspecting cpr_rankings ---")
    cpr_data = db.get_cpr_rankings("1267325171853701120")
    if cpr_data:
        print(json.dumps(cpr_data, indent=2))
    else:
        print("No CPR data found.")

if __name__ == "__main__":
    inspect_data()
