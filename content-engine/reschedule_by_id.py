#!/usr/bin/env python3
"""
Reschedule videos by video ID directly.
"""

import sys
from pathlib import Path
from core.youtube_auth import build_service

SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]

def reschedule_by_id(video_id: str, new_schedule: str) -> bool:
    """Reschedule a video by ID to a new publish time."""
    try:
        service = build_service('youtube', 'v3', SCOPES)
        
        body = {
            'id': video_id,
            'status': {
                'publishAt': new_schedule,
                'privacyStatus': 'private'
            }
        }
        
        print(f"Rescheduling {video_id} to {new_schedule}")
        response = service.videos().update(
            part='status',
            body=body
        ).execute()
        
        print(f"  ✅ Success")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Reschedule the 4 MLU videos by ID
    videos = [
        ("sRIWwrCPgwc", "2026-07-19T22:00:00-04:00"),  # MLU "I am okay cheesing this boss"
        ("kipEzC8GifY", "2026-07-23T22:00:00-04:00"),  # MLU "it just picks the right tool automatically"
        ("WWJIlEzlA2A", "2026-07-28T22:00:00-04:00"),  # MLU "the resources respawn fast enough to never run out"
        ("qBqm7nhtk50", "2026-08-01T22:00:00-04:00"),  # MLU "purple crystal is the next barrier for everything"
    ]
    
    success_count = 0
    for video_id, new_schedule in videos:
        if reschedule_by_id(video_id, new_schedule):
            success_count += 1
    
    print(f"\nComplete: {success_count}/{len(videos)} successful")
