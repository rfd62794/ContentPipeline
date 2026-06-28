#!/usr/bin/env python3
"""
List all private videos with full details.
"""

import sys
from pathlib import Path

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import build_service

def list_all_private():
    """List all private videos with full details."""
    scopes = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    service = build_service('youtube', 'v3', scopes)
    
    print("=== All Private Videos ===")
    
    try:
        # Get channel's uploads playlist
        channel_response = service.channels().list(
            part='contentDetails',
            mine=True
        ).execute()
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get all private videos
        next_page_token = None
        count = 0
        
        while True:
            playlist_response = service.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            
            video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
            
            if video_ids:
                videos_response = service.videos().list(
                    part='snippet,status',
                    id=','.join(video_ids)
                ).execute()
                
                for video_data in videos_response.get('items', []):
                    snippet = video_data.get('snippet', {})
                    status = video_data.get('status', {})
                    
                    if status.get('privacyStatus') == 'private':
                        count += 1
                        title = snippet.get('title', '')
                        publish_at = snippet.get('publishAt', '')
                        
                        print(f"\n{count}. {title}")
                        print(f"   ID: {video_data['id']}")
                        print(f"   PublishAt: {publish_at}")
                        print(f"   PublishedAt: {snippet.get('publishedAt', '')}")
                        
                        # Check if this matches our plan titles
                        plan_titles = [
                            "Everything is Crab — I'm fully yellow with a trunk coming off. what am I.",
                            "Everything is Crab — look at the antenna. moss growing on me. very snail.",
                            "Fishing Inc — unlock the fishing license so you're legally allowed to fish",
                            "Everything is Crab — I'm weaker but I also do more damage. we will try that."
                        ]
                        
                        if title in plan_titles:
                            print(f"   *** MATCHES PLAN ***")
            
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f"\nTotal private videos: {count}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_all_private()
