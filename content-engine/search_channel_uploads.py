from core.youtube_auth import build_service

SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
service = build_service('youtube', 'v3', SCOPES)

# Get channel's uploads playlist
channel_response = service.channels().list(
    part='contentDetails',
    mine=True
).execute()

uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

print("Searching channel uploads for MLU videos...")

# Get all videos from uploads playlist
next_page_token = None
mlu_videos = []

while True:
    playlist_response = service.playlistItems().list(
        part='snippet,contentDetails',
        playlistId=uploads_playlist_id,
        maxResults=50,
        pageToken=next_page_token
    ).execute()
    
    for item in playlist_response.get('items', []):
        title = item['snippet']['title']
        video_id = item.get('contentDetails', {}).get('videoId')
        if video_id and 'My Little Universe' in title:
            mlu_videos.append({
                'title': title,
                'video_id': video_id
            })
    
    next_page_token = playlist_response.get('nextPageToken')
    if not next_page_token:
        break

print(f"\nFound {len(mlu_videos)} MLU videos in channel uploads:")
for video in mlu_videos:
    print(f"  - {video['title']}")
    print(f"    ID: {video['video_id']}")
