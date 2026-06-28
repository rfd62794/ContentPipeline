#!/usr/bin/env python3
"""
Simple OAuth authentication test using different port.
"""

import sys
from pathlib import Path

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import CLIENT_SECRET_FILE, TOKEN_FILE
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate_with_port(port=8081):
    """Authenticate using specified port."""
    scopes = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    
    if not CLIENT_SECRET_FILE.exists():
        print(f"Client secret not found: {CLIENT_SECRET_FILE}")
        return None
    
    print(f"Starting OAuth flow on port {port}...")
    print("Please open your browser and complete the authentication.")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), scopes)
        credentials = flow.run_local_server(port=port)
        
        # Save credentials
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
        print(f"Authentication successful! Token saved to {TOKEN_FILE}")
        return credentials
        
    except Exception as e:
        print(f"Authentication failed on port {port}: {e}")
        return None

if __name__ == "__main__":
    # Try different ports
    for port in [8081, 8082, 8083, 8888, 9000]:
        print(f"\nTrying port {port}...")
        creds = authenticate_with_port(port)
        if creds:
            print("Success!")
            break
    else:
        print("All ports failed. You may need to:")
        print("1. Run as administrator")
        print("2. Check firewall settings")
        print("3. Use gcloud auth application-default login instead")
