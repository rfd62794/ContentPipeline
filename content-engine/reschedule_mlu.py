#!/usr/bin/env python3
"""
Reschedule 6 displaced MLU videos to after Jul 23
"""
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from reschedule_calendar import CalendarRescheduler

def reschedule_mlu_videos():
    """Reschedule 6 MLU videos to new dates"""
    
    # MLU videos to reschedule
    mlu_videos = [
        {
            "title": "My Little Universe — the resources respawn fast enough to never run out",
            "new_date": "2026-07-24T22:00:00-04:00"
        },
        {
            "title": "My Little Universe — geez. this opened up.",
            "new_date": "2026-07-25T22:00:00-04:00"
        },
        {
            "title": "My Little Universe — purple crystal is the next barrier for everything",
            "new_date": "2026-07-26T22:00:00-04:00"
        },
        {
            "title": "My Little Universe — God, I just unlocked a spacesuit",
            "new_date": "2026-07-27T22:00:00-04:00"
        },
        {
            "title": "My Little Universe — and then lava just surrounded me",
            "new_date": "2026-07-28T22:00:00-04:00"
        },
        {
            "title": "My Little Universe — nine rings. and also nine planets.",
            "new_date": "2026-07-29T22:00:00-04:00"
        }
    ]
    
    try:
        # Use existing CalendarRescheduler
        rescheduler = CalendarRescheduler()
        print("YouTube service built successfully")
        
        # Get all scheduled videos using existing method
        print("Fetching scheduled videos...")
        scheduled_videos = rescheduler.get_scheduled_videos()
        print(f"Found {len(scheduled_videos)} scheduled videos")
        
        # Match MLU videos and reschedule
        matched_videos = []
        for mlu in mlu_videos:
            found = False
            for video in scheduled_videos:
                if video['title'] == mlu['title']:
                    matched_videos.append({
                        'video_id': video['video_id'],
                        'title': video['title'],
                        'new_date': mlu['new_date']
                    })
                    found = True
                    break
            
            if not found:
                print(f"ERROR: Video not found: {mlu['title']}")
                return False
        
        print(f"Matched {len(matched_videos)} MLU videos")
        
        # Confirm all videos found before updating
        if len(matched_videos) != len(mlu_videos):
            print("ERROR: Not all MLU videos found. Aborting.")
            return False
        
        # Reschedule each video
        print("\n=== RESCHEDULING MLU VIDEOS ===")
        success_count = 0
        
        for video in matched_videos:
            try:
                print(f"\nRescheduling: {video['title']}")
                print(f"  New date: {video['new_date']}")
                
                # Update video
                body = {
                    'id': video['video_id'],
                    'status': {
                        'publishAt': video['new_date'],
                        'privacyStatus': 'private'
                    }
                }
                
                response = rescheduler.service.videos().update(
                    part='status',
                    body=body
                ).execute()
                
                print(f"  ✅ Success - Video ID: {video['video_id']}")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Failed: {e}")
        
        print(f"\n=== SUMMARY ===")
        print(f"Successfully rescheduled: {success_count}/{len(matched_videos)} videos")
        
        return success_count == len(matched_videos)
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = reschedule_mlu_videos()
    sys.exit(0 if success else 1)
