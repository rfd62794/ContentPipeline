"""
YouTube Upload Client

Implements OAuth2 authentication and resumable video upload for YouTube Data API v3.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import json

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Run: pip install google-auth-oauthlib google-api-python-client google-auth-httplib2")
    sys.exit(1)

from metadata_builder import (
    load_short_yaml,
    load_meta_yaml,
    resolve_metadata,
    validate_metadata,
    format_schedule
)


# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_authenticated_service(client_id: str, client_secret: str, token_path: str):
    """
    OAuth2 flow. Load token from token_path if exists and valid.
    Run browser consent flow if token missing or expired.
    Save refreshed token to token_path.
    Returns authenticated YouTube service object.
    
    Args:
        client_id: OAuth client ID from Google Cloud Console.
        client_secret: OAuth client secret from Google Cloud Console.
        token_path: Path to store OAuth token JSON.
    
    Returns:
        Authenticated YouTube service object.
    """
    credentials = None
    
    # Load existing token if available
    if os.path.exists(token_path):
        with open(token_path, 'r', encoding='utf-8') as f:
            token_data = json.load(f)
            credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
    
    # Refresh or obtain new credentials
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # Create OAuth flow with client credentials
            client_config = {
                'installed': {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob', 'http://localhost']
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            credentials = flow.run_local_server(port=0)
        
        # Save credentials
        with open(token_path, 'w', encoding='utf-8') as f:
            json.dump(credentials.to_json(), f)
    
    return build('youtube', 'v3', credentials=credentials)


def build_video_resource(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure function. Build YouTube API video resource body from resolved metadata dict.
    Returns dict matching YouTube Data API v3 insert body schema.
    
    Args:
        metadata: Resolved metadata dict from metadata_builder.
    
    Returns:
        YouTube API video resource dict.
    """
    # Map privacy to YouTube status
    privacy_map = {
        'public': 'public',
        'unlisted': 'unlisted',
        'private': 'private'
    }
    privacy = privacy_map.get(metadata.get('privacy', 'public'), 'public')
    
    # Build snippet
    snippet = {
        'title': metadata.get('title', ''),
        'description': metadata.get('description', ''),
        'tags': metadata.get('tags', []),
        'categoryId': metadata.get('category_id', '20')
    }
    
    # Build status
    status = {
        'privacyStatus': privacy,
        'selfDeclaredMadeForKids': metadata.get('made_for_kids', False)
    }
    
    return {
        'snippet': snippet,
        'status': status
    }


def upload_video(service, video_path: str, metadata: Dict[str, Any]) -> str:
    """
    Resumable upload. Chunk size: 8MB.
    Print progress to terminal: 'Uploading... X%'
    Returns YouTube video ID on success.
    Raises on failure after 3 retries.
    
    Args:
        service: Authenticated YouTube service object.
        video_path: Path to video file to upload.
        metadata: Resolved metadata dict.
    
    Returns:
        YouTube video ID.
    
    Raises:
        HttpError: If upload fails after retries.
    """
    body = build_video_resource(metadata)
    
    # Create media upload object
    media = MediaFileUpload(
        video_path,
        chunksize=8 * 1024 * 1024,  # 8MB chunks
        resumable=True
    )
    
    # Insert request
    request = service.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    # Upload with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f'Uploading... {progress}%')
            
            return response['id']
        
        except HttpError as e:
            if attempt < max_retries - 1:
                print(f'Upload failed (attempt {attempt + 1}/{max_retries}), retrying...')
                continue
            raise


def set_schedule(service, video_id: str, schedule_iso: str) -> None:
    """
    Set video publish time. Called after upload if schedule present.
    
    Args:
        service: Authenticated YouTube service object.
        video_id: YouTube video ID.
        schedule_iso: RFC 3339 formatted datetime string.
    """
    body = {
        'id': video_id,
        'snippet': {
            'scheduledPublishTime': schedule_iso
        },
        'status': {
            'privacyStatus': 'private',  # Must be private before scheduling
            'publishAt': schedule_iso
        }
    }
    
    service.videos().update(
        part='snippet,status',
        body=body
    ).execute()


def print_metadata_table(metadata: Dict[str, Any], meta_source: Dict[str, str]) -> None:
    """
    Print resolved metadata table showing which layer provided each field.
    
    Args:
        metadata: Resolved metadata dict.
        meta_source: Dict mapping field names to source ('manual', 'auto', 'default').
    """
    print("\n=== Resolved Metadata ===\n")
    
    print(f"Title: {metadata.get('title', '')}")
    print(f"  Source: {meta_source.get('title', 'unknown')}\n")
    
    print(f"Description: {metadata.get('description', '')[:100]}...")
    print(f"  Source: {meta_source.get('description', 'unknown')}\n")
    
    print(f"Tags: {', '.join(metadata.get('tags', []))}")
    print(f"  Source: {meta_source.get('tags', 'unknown')}\n")
    
    print(f"Privacy: {metadata.get('privacy', '')}")
    print(f"  Source: {meta_source.get('privacy', 'unknown')}\n")
    
    schedule = metadata.get('schedule', '')
    if schedule:
        print(f"Schedule: {schedule}")
        print(f"  Source: {meta_source.get('schedule', 'unknown')}\n")
    else:
        print("Schedule: Publish immediately")
        print(f"  Source: {meta_source.get('schedule', 'unknown')}\n")
    
    print(f"Category ID: {metadata.get('category_id', '')}")
    print(f"  Source: {meta_source.get('category_id', 'unknown')}\n")


def determine_source(meta: Dict[str, Any], field: str, resolved_value: Any) -> str:
    """
    Determine which layer provided a field value.
    
    Args:
        meta: .meta.yaml configuration dict.
        field: Field name.
        resolved_value: Resolved field value.
    
    Returns:
        Source string: 'manual', 'auto', or 'default'.
    """
    meta_value = meta.get(field, '')
    
    # Check if manual override provided value
    if meta_value:
        if isinstance(meta_value, list) and meta_value:
            return 'manual'
        elif isinstance(meta_value, str) and meta_value:
            return 'manual'
        elif meta_value is True or meta_value is False:
            return 'manual'
    
    # Check if auto-generated
    if meta.get('auto_generate', False) and resolved_value:
        return 'auto'
    
    return 'default'


def main() -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Upload with Metadata Override")
    parser.add_argument(
        '--short',
        type=str,
        required=True,
        help='Short ID (e.g., eic_short_4_shellephant)'
    )
    parser.add_argument(
        '--steam-path',
        type=str,
        default=None,
        help='Path to Steam installation for metadata enrichment'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    client_id = os.getenv('YOUTUBE_CLIENT_ID')
    client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Error: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in .env")
        sys.exit(1)
    
    # Load short and meta YAMLs
    short_path = f"shorts/{args.short}.yaml"
    meta_path = f"shorts/{args.short}.meta.yaml"
    
    try:
        short = load_short_yaml(short_path)
        meta = load_meta_yaml(meta_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Optionally load Steam metadata
    steam_metadata = None
    if args.steam_path:
        try:
            from steam_library import SteamLibrary
            library = SteamLibrary(steam_path=Path(args.steam_path))
            # Try to find game by name from short
            # This is a simple heuristic - could be improved
            games = library.get_library()
            for game in games:
                if game.installed:
                    # Get full metadata for installed games
                    full_lib = library.get_library_with_metadata(limit=10)
                    for full_game in full_lib:
                        if full_game.installed:
                            steam_metadata = {
                                'name': full_game.name,
                                'description': full_game.description,
                                'genres': full_game.genres,
                                'tags': full_game.tags
                            }
                            break
                    break
        except Exception as e:
            print(f"Warning: Could not load Steam metadata: {e}")
    
    # Resolve metadata
    resolved = resolve_metadata(short, meta, steam_metadata)
    
    # Determine sources for display
    meta_source = {
        'title': determine_source(meta, 'title', resolved.get('title')),
        'description': determine_source(meta, 'description', resolved.get('description')),
        'tags': determine_source(meta, 'tags', resolved.get('tags')),
        'privacy': determine_source(meta, 'privacy', resolved.get('privacy')),
        'schedule': determine_source(meta, 'schedule', resolved.get('schedule')),
        'category_id': determine_source(meta, 'category_id', resolved.get('category_id'))
    }
    
    # Print metadata table
    print_metadata_table(resolved, meta_source)
    
    # Validate metadata
    errors = validate_metadata(resolved)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    # Find video file
    video_path = f"output/{args.short}.mp4"
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Confirmation prompt (mandatory)
    print(f"\nVideo file: {video_path}")
    response = input("Proceed with upload? [y/N]: ")
    if response.lower() != 'y':
        print("Upload cancelled.")
        sys.exit(0)
    
    # Authenticate
    token_path = ".youtube_token.json"
    try:
        service = get_authenticated_service(client_id, client_secret, token_path)
    except Exception as e:
        print(f"Error during authentication: {e}")
        sys.exit(1)
    
    # Upload
    try:
        video_id = upload_video(service, video_path, resolved)
        print(f"\nUpload successful!")
        print(f"Video ID: {video_id}")
        print(f"URL: https://www.youtube.com/watch?v={video_id}")
        
        # Set schedule if provided
        schedule = resolved.get('schedule', '')
        if schedule:
            schedule_iso = format_schedule(schedule)
            if schedule_iso:
                set_schedule(service, video_id, schedule_iso)
                print(f"Scheduled for: {schedule}")
    
    except HttpError as e:
        print(f"Error during upload: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
