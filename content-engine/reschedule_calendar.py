#!/usr/bin/env python3
"""
ContentEngine — Calendar Reschedule Script

Reschedules existing scheduled videos by updating their publishAt via YouTube Data API videos().update().
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.youtube_auth import build_service
from youtube_library import YouTubeLibrary


class CalendarRescheduler:
    """Reschedules YouTube videos based on a plan file."""
    
    # Need write scope for updating video status
    SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
    
    def __init__(self):
        """Initialize rescheduler with YouTube service."""
        self.service = build_service('youtube', 'v3', self.SCOPES)
        if not self.service:
            raise RuntimeError("Failed to build YouTube service - check authentication")
        
        self.library = YouTubeLibrary()
    
    def load_plan(self, plan_path: str) -> List[Dict[str, str]]:
        """Load reschedule plan from YAML file."""
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_data = yaml.safe_load(f)
            
            if 'reschedules' not in plan_data:
                raise ValueError("Plan file must contain 'reschedules' key")
            
            return plan_data['reschedules']
        except Exception as e:
            print(f"Error loading plan file {plan_path}: {e}")
            sys.exit(1)
    
    def get_scheduled_videos(self) -> List[Dict[str, Any]]:
        """Get all scheduled videos from the channel using uploads playlist."""
        scheduled_videos = []
        
        try:
            # Get channel's uploads playlist
            channel_response = self.service.channels().list(
                part='contentDetails',
                mine=True
            ).execute()
            
            if not channel_response.get('items'):
                print("No channel found")
                return scheduled_videos
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get all videos from uploads playlist
            next_page_token = None
            while True:
                playlist_response = self.service.playlistItems().list(
                    part='contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
                
                if video_ids:
                    # Get detailed video info including status
                    videos_response = self.service.videos().list(
                        part='snippet,status',
                        id=','.join(video_ids)
                    ).execute()
                    
                    for video_data in videos_response.get('items', []):
                        snippet = video_data.get('snippet', {})
                        status = video_data.get('status', {})
                        
                        # Check if video is scheduled (private with publishAt)
                        publish_at = status.get('publishAt') or snippet.get('publishAt')
                        if status.get('privacyStatus') == 'private' and publish_at:
                            scheduled_videos.append({
                                'video_id': video_data['id'],
                                'title': snippet.get('title', ''),
                                'current_schedule': publish_at,
                                'status': status.get('privacyStatus')
                            })
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
        
        except Exception as e:
            print(f"Error fetching scheduled videos: {e}")
        
        return scheduled_videos
    
    def find_video_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Find a scheduled video by exact title match."""
        scheduled_videos = self.get_scheduled_videos()
        for video in scheduled_videos:
            if video['title'] == title:
                return video
        
        # If not found in scheduled list, try searching by title
        try:
            search_response = self.service.search().list(
                part='snippet',
                q=title,
                type='video',
                maxResults=5
            ).execute()
            
            for item in search_response.get('items', []):
                if item['snippet']['title'] == title:
                    video_id = item['id']['videoId']
                    # Get video status to confirm it's scheduled
                    video_response = self.service.videos().list(
                        part='status,snippet',
                        id=video_id
                    ).execute()
                    
                    if video_response.get('items'):
                        video_data = video_response['items'][0]
                        status = video_data.get('status', {})
                        snippet = video_data.get('snippet', {})
                        publish_at = status.get('publishAt') or snippet.get('publishAt')
                        
                        return {
                            'video_id': video_id,
                            'title': snippet.get('title', ''),
                            'current_schedule': publish_at,
                            'status': status.get('privacyStatus')
                        }
        except Exception as e:
            print(f"Error searching for video by title: {e}")
        
        return None
    
    def reschedule_video(self, video_id: str, new_schedule: str) -> bool:
        """Reschedule a single video to a new publish time."""
        try:
            # Update video with new publishAt time
            body = {
                'id': video_id,
                'status': {
                    'publishAt': new_schedule,
                    'privacyStatus': 'private'
                }
            }
            
            print(f"API CALL - Video ID: {video_id}")
            print(f"API CALL - publishAt being sent: '{new_schedule}'")
            print(f"API CALL - Full body: {body}")
            
            response = self.service.videos().update(
                part='status',
                body=body
            ).execute()
            
            return True
        except Exception as e:
            print(f"Error rescheduling video {video_id}: {e}")
            return False
    
    def run_dry_run(self, plan: List[Dict[str, str]]) -> None:
        """Print dry-run table showing current → new schedule."""
        print("\n=== DRY RUN - Calendar Reschedule Plan ===\n")
        print(f"{'Title':<60} {'Current Schedule':<25} {'New Schedule':<25}")
        print("-" * 110)
        
        found_count = 0
        not_found_count = 0
        
        for item in plan:
            title = item['title']
            new_schedule = item['new_schedule']
            
            video = self.find_video_by_title(title)
            if video:
                found_count += 1
                current = video['current_schedule'][:19] if video['current_schedule'] else 'Not scheduled'
                new = new_schedule[:19]
                print(f"{title[:58]:<60} {current:<25} {new:<25}")
            else:
                not_found_count += 1
                print(f"{title[:58]:<60} {'NOT FOUND':<25} {new_schedule[:19]:<25}")
        
        print("-" * 110)
        print(f"\nSummary: {found_count} videos found, {not_found_count} videos not found")
        print("\nUse --yes to execute these changes.")
    
    def execute_reschedule(self, plan: List[Dict[str, str]]) -> None:
        """Execute the reschedule plan."""
        print("\n=== EXECUTING - Calendar Reschedule ===\n")
        
        success_count = 0
        failure_count = 0
        
        for item in plan:
            title = item['title']
            new_schedule = item['new_schedule']
            
            video = self.find_video_by_title(title)
            if not video:
                print(f"❌ Video not found: {title}")
                failure_count += 1
                continue
            
            print(f"Rescheduling: {title}")
            print(f"  Current: {video['current_schedule']}")
            print(f"  New: {new_schedule}")
            
            if self.reschedule_video(video['video_id'], new_schedule):
                print(f"  ✅ Success")
                success_count += 1
            else:
                print(f"  ❌ Failed")
                failure_count += 1
            print()
        
        print("=" * 50)
        print(f"Execution complete: {success_count} successful, {failure_count} failed")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Reschedule YouTube videos calendar")
    parser.add_argument('--plan', required=True, help='Path to YAML reschedule plan file')
    parser.add_argument('--yes', action='store_true', help='Execute reschedule (default: dry-run)')
    
    args = parser.parse_args()
    
    # Validate plan file exists
    if not Path(args.plan).exists():
        print(f"Error: Plan file not found: {args.plan}")
        sys.exit(1)
    
    try:
        rescheduler = CalendarRescheduler()
        plan = rescheduler.load_plan(args.plan)
        
        if not plan:
            print("Error: No reschedule items found in plan file")
            sys.exit(1)
        
        print(f"Loaded {len(plan)} reschedule items from {args.plan}")
        
        if args.yes:
            rescheduler.execute_reschedule(plan)
        else:
            rescheduler.run_dry_run(plan)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
