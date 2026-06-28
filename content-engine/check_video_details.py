#!/usr/bin/env python3
"""
Check full video details for the 4 specific videos.
"""

import sys
from pathlib import Path

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import build_service

def check_video_details():
    """Check full details for specific videos."""
    scopes = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    service = build_service('youtube', 'v3', scopes)
    
    # The 4 video IDs we found
    video_ids = [
        "uqiMev4e6R8",  # Everything is Crab — I'm fully yellow with a trunk coming off. what am I.
        "LaEhjvir8ww",  # Everything is Crab — look at the antenna. moss growing on me. very snail.
        "iCRGt-hpI-Y",  # Fishing Inc — unlock the fishing license so you're legally allowed to fish
        "766q-6rr16I"   # Everything is Crab — I'm weaker but I also do more damage. we will try that.
    ]
    
    print("=== Full Video Details ===")
    
    try:
        # Get full video details
        videos_response = service.videos().list(
            part='snippet,status,contentDetails,recordingDetails',
            id=','.join(video_ids)
        ).execute()
        
        for video_data in videos_response.get('items', []):
            print(f"\nVideo ID: {video_data['id']}")
            print(f"Title: {video_data['snippet']['title']}")
            
            snippet = video_data['snippet']
            status = video_data['status']
            
            print(f"Privacy Status: {status.get('privacyStatus', '')}")
            print(f"Publish At: {snippet.get('publishAt', 'NONE')}")
            print(f"Published At: {snippet.get('publishedAt', 'NONE')}")
            
            # Check all snippet fields
            print("All snippet fields:")
            for key, value in snippet.items():
                if key not in ['title', 'description', 'tags']:
                    print(f"  {key}: {value}")
            
            # Check all status fields
            print("All status fields:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            print("-" * 60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_video_details()
