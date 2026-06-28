from core.youtube_auth import build_service

SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]
service = build_service('youtube', 'v3', SCOPES)

# Search for MLU videos with partial matches
search_terms = [
    "cheesing this boss",
    "it just picks the right tool",
    "resources respawn fast enough",
    "purple crystal is the next barrier"
]

for term in search_terms:
    print(f"\nSearching for: {term}")
    try:
        search_response = service.search().list(
            part='snippet',
            q=f"My Little Universe {term}",
            type='video',
            maxResults=5
        ).execute()
        
        for item in search_response.get('items', []):
            print(f"  Found: {item['snippet']['title']}")
            print(f"    Video ID: {item['id']['videoId']}")
    except Exception as e:
        print(f"  Error: {e}")
