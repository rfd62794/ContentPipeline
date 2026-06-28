#!/usr/bin/env python3
"""
Debug script to check exact title matching.
"""

import sys
from pathlib import Path
import yaml

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import build_service

def debug_title_matching():
    """Debug title matching against plan."""
    scopes = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    service = build_service('youtube', 'v3', scopes)
    
    # Load plan
    with open('reschedule_jun28_replan.yaml', 'r') as f:
        plan = yaml.safe_load(f)
    
    plan_titles = [item['title'] for item in plan['reschedules']]
    
    print("=== Title Matching Debug ===")
    print("Plan titles:")
    for title in plan_titles:
        print(f"  '{title}'")
    print()
    
    try:
        # Get channel's uploads playlist
        channel_response = service.channels().list(
            part='contentDetails',
            mine=True
        ).execute()
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get all private videos
        next_page_token = None
        private_videos = []
        
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
                        title = snippet.get('title', '')
                        private_videos.append({
                            'title': title,
                            'id': video_data['id'],
                            'publishAt': snippet.get('publishAt', '')
                        })
            
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f"Found {len(private_videos)} private videos")
        print()
        
        # Check for exact matches
        for plan_title in plan_titles:
            found = False
            for video in private_videos:
                if video['title'] == plan_title:
                    found = True
                    print(f"✅ MATCH: '{plan_title}'")
                    print(f"   Video ID: {video['id']}")
                    print(f"   PublishAt: {video['publishAt']}")
                    break
            
            if not found:
                print(f"❌ NO MATCH: '{plan_title}'")
                # Show similar titles
                print("   Similar private titles:")
                for video in private_videos:
                    if any(word.lower() in video['title'].lower() for word in plan_title.split()[:3]):
                        print(f"     - '{video['title']}'")
            print()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_title_matching()
