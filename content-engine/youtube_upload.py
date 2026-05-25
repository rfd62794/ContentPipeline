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
_google_api_available = False
_HttpError = None
_MediaFileUpload = None
try:
    from googleapiclient.http import MediaFileUpload as _MediaFileUpload
    from googleapiclient.errors import HttpError as _HttpError
    from core.youtube_auth import build_service
    _google_api_available = True
except ImportError:
    pass

from metadata_builder import (
    load_short_yaml,
    load_meta_yaml,
    resolve_metadata,
    validate_metadata,
    format_schedule
)


# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_authenticated_service():
    """
    Return an authenticated YouTube service object.

    Returns:
        Authenticated YouTube service object.
    """
    if not _google_api_available:
        return None
    return build_service('youtube', 'v3', SCOPES)


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
    privacy = 'private' if metadata.get('schedule') else privacy_map.get(metadata.get('privacy', 'public'), 'public')
    
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

    # Add schedule to status if present (for scheduling during upload)
    schedule = metadata.get('schedule', '')
    if schedule:
        schedule_iso = format_schedule(schedule)
        if schedule_iso:
            status['publishAt'] = schedule_iso
    
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
    if not _google_api_available or _MediaFileUpload is None:
        return None
    
    body = build_video_resource(metadata)
    
    # Create media upload object
    media = _MediaFileUpload(
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
        
        except Exception as e:
            if _google_api_available and _HttpError and isinstance(e, _HttpError):
                if attempt < max_retries - 1:
                    print(f'Upload failed (attempt {attempt + 1}/{max_retries}), retrying...')
                    continue
                raise
            raise


def print_metadata_table(metadata: Dict[str, Any], meta_source: Dict[str, str]) -> None:
    """
    Print resolved metadata table showing which layer provided each field.

    Args:
        metadata: Resolved metadata dict.
        meta_source: Dict mapping field names to source ('manual', 'auto', 'default').
    """
    pass


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
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt and proceed with upload'
    )
    
    args = parser.parse_args()
    
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
    # print_metadata_table(resolved, meta_source)
    # print()
    
    # Validate metadata
    try:
        errors = validate_metadata(resolved)
        if errors:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        print("Validation passed")
    except Exception as e:
        print(f"Error validating metadata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Find video file
    try:
        video_path = f"output/shorts/{args.short}.mp4"
        print(f"Checking for video file: {video_path}")
        print(f"File exists: {os.path.exists(video_path)}")
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            sys.exit(1)
        print("Video file found")
    except Exception as e:
        print(f"Error checking video file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Confirmation prompt (mandatory unless --yes)
    try:
        print(f"\nVideo file: {video_path}")
        if not args.yes:
            response = input("Proceed with upload? [y/N]: ")
            if response.lower() != 'y':
                print("Upload cancelled.")
                sys.exit(0)
        print("Confirmation complete, proceeding to authentication")
    except Exception as e:
        print(f"Error during confirmation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Authenticate using gcloud ADC
    try:
        print("Starting authentication...")
        service = get_authenticated_service()
        print("Authentication successful")
    except Exception as e:
        print(f"Error during authentication: {e}")
        print("Make sure gcloud auth application-default login has been run with YouTube upload scope.")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Upload
    try:
        print("Starting upload...")
        video_id = upload_video(service, video_path, resolved)
        print(f"\nUpload successful!")
        print(f"Video ID: {video_id}")
        print(f"URL: https://www.youtube.com/watch?v={video_id}")

        # Schedule was set during upload if present
        schedule = resolved.get('schedule', '')
        if schedule:
            print(f"Video scheduled for: {schedule}")
        else:
            print("Video published immediately")
    
    except Exception as e:
        if _google_api_available and _HttpError and isinstance(e, _HttpError):
            print(f"Error during upload: {e}")
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
