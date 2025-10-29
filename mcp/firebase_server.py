#!/usr/bin/env python3
"""
Firebase MCP Server Wrapper for CPR-NFL
Uses official Firebase MCP server + our Database class
"""

import sys
from pathlib import Path
import logging
from typing import Dict, Any, List

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseMCPServer:
    """
    Firebase MCP Server Wrapper for CPR-NFL
    
    IMPORTANT: This uses the official Firebase MCP server via:
    npx firebase-tools@latest mcp
    
    MCP Client Configuration:
    {
        "mcpServers": {
            "firebase": {
                "command": "npx",
                "args": ["-y", "firebase-tools@latest", "mcp"]
            }
        }
    }
    
    Official Firebase MCP Tools Available:
    - firebase_deploy: Deploy Firebase project
    - firebase_init: Initialize Firebase project  
    - firebase_get_environment: Get Firebase environment info
    - firestore_get: Get Firestore documents
    - firestore_set: Set Firestore documents
    - And many more Firebase operations
    
    CPR-NFL Specific Operations:
    This wrapper provides CPR-specific database operations using our Database class
    """
    
    def __init__(self):
        self.database = Database()
        logger.info("Firebase MCP Server Wrapper initialized")
        logger.info("Use official Firebase MCP: npx firebase-tools@latest mcp")
        logger.info("CPR-NFL database operations available via Database class")
    
    def get_cpr_rankings(self, league_id: str = "1267325171853701120") -> Dict[str, Any]:
        """Get REAL CPR rankings from Firebase"""
        logger.info(f"Getting REAL CPR rankings for league {league_id}")
        return self.database.get_cpr_rankings(league_id, latest_only=True)
    
    def save_cpr_rankings(self, league_id: str, rankings: List[Dict]) -> bool:
        """Save REAL CPR rankings to Firebase"""
        logger.info(f"Saving REAL CPR rankings for league {league_id}")
        return self.database.save_cpr_rankings(league_id, rankings)
    
    def get_niv_data(self, league_id: str = "1267325171853701120") -> Dict[str, Any]:
        """Get NIV data from Firebase"""
        logger.info(f"TARGET Getting NIV data for league {league_id}")
        return self.database.get_niv_data(league_id, latest_only=True)
    
    def save_niv_data(self, league_id: str, niv_data: List[Dict]) -> bool:
        """Save NIV data to Firebase"""
        logger.info(f"SAVE Saving NIV data for league {league_id}")
        return self.database.save_niv_data(league_id, niv_data)
    
    def get_league_data(self, league_id: str = "1267325171853701120") -> Dict[str, Any]:
        """Get complete league analysis data"""
        logger.info(f"NFL Getting complete league data for {league_id}")
        
        cpr_data = self.get_cpr_rankings(league_id)
        niv_data = self.get_niv_data(league_id)
        
        return {
            "league_id": league_id,
            "cpr_rankings": cpr_data,
            "niv_data": niv_data,
            "timestamp": self.database._get_timestamp()
        }

# Create singleton instance
firebase_server = FirebaseMCPServer()

# Configuration helper
def get_mcp_config() -> Dict[str, Any]:
    """Get MCP configuration for Firebase server"""
    return {
        "mcpServers": {
            "firebase": {
                "command": "npx",
                "args": ["-y", "firebase-tools@latest", "mcp"]
            }
        }
    }

if __name__ == "__main__":
    # Test the Firebase MCP server wrapper
    server = FirebaseMCPServer()
    
    print("Firebase MCP Server Wrapper Test")
    print("=" * 40)
    print("Configuration:")
    print(f"  Command: npx -y firebase-tools@latest mcp")
    print("  Available: Official Firebase MCP tools")
    print("  CPR-NFL: Database operations via wrapper")
    print("=" * 40)
    
    # Test database connection
    try:
        if server.database.is_connected:
            print("PASS Database connection: OK")
        else:
            print("WARN Database connection: Not available (local mode)")
    except Exception as e:
        print(f"FAIL Database connection: Error - {e}")
