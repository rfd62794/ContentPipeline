"""
upload_session.py — Upload a raw long-form session video to YouTube.

Usage:
    python upload_session.py sessions/af_session_1.yaml
    python upload_session.py sessions/af_session_1.yaml --yes
"""

import sys
import argparse
from pathlib import Path

import yaml
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from core.youtube_auth import build_service

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def load_session_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def build_video_resource(cfg: dict) -> dict:
    scheduled = cfg.get('schedule')
    privacy = 'private' if scheduled else cfg.get('privacy', 'public')

    snippet = {
        'title': cfg['title'],
        'description': cfg.get('description', ''),
        'tags': cfg.get('tags', []),
        'categoryId': str(cfg.get('category_id', '20')),
    }

    status = {
        'privacyStatus': privacy,
        'selfDeclaredMadeForKids': cfg.get('made_for_kids', False),
    }
    if scheduled:
        status['publishAt'] = scheduled

    return {'snippet': snippet, 'status': status}


def upload_video(service, video_path: str, body: dict) -> str:
    media = MediaFileUpload(video_path, chunksize=8 * 1024 * 1024, resumable=True)
    request = service.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f'\rUploading... {int(status.progress() * 100)}%', end='', flush=True)
            print()
            return response['id']
        except HttpError as e:
            if attempt < max_retries - 1:
                print(f'\nUpload error (attempt {attempt + 1}/{max_retries}), retrying...')
            else:
                raise


def main():
    parser = argparse.ArgumentParser(description='Upload a long-form session video to YouTube')
    parser.add_argument('yaml', help='Path to session YAML file')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    cfg = load_session_yaml(args.yaml)

    source = cfg['source']
    if not Path(source).exists():
        print(f'Error: Source file not found: {source}')
        sys.exit(1)

    file_size_mb = Path(source).stat().st_size / (1024 * 1024)

    print(f'\nSession upload')
    print(f'  File   : {source}')
    print(f'  Size   : {file_size_mb:.1f} MB')
    print(f'  Title  : {cfg["title"]}')
    print(f'  Privacy: {cfg.get("privacy", "public")}')
    print(f'  Schedule: {cfg.get("schedule", "immediate")}')

    if not args.yes:
        confirm = input('\nProceed with upload? [y/N]: ').strip().lower()
        if confirm != 'y':
            print('Cancelled.')
            sys.exit(0)

    service = build_service('youtube', 'v3', SCOPES)
    body = build_video_resource(cfg)

    print('\nStarting upload...')
    video_id = upload_video(service, source, body)

    print(f'\nUpload successful!')
    print(f'Video ID: {video_id}')
    print(f'URL: https://www.youtube.com/watch?v={video_id}')
    if cfg.get('schedule'):
        print(f'Scheduled for: {cfg["schedule"]}')


if __name__ == '__main__':
    main()
