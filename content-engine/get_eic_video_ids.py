from core.youtube_auth import build_service

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
service = build_service('youtube', 'v3', SCOPES)

# EIC videos to find
titles = [
    "Everything is Crab — that was a lethal mushroom",
    "Everything is Crab — just absolute mutant massive belly thing",
    "Everything is Crab — I don't know what to call that. you pulled on my nose.",
    "Everything is Crab — I want reach so bad. spines level 5.",
    "Everything is Crab — I can hide in a hole. good to know.",
    "Everything is Crab — look at the antenna. moss growing on me. very snail."
]

print("Searching for EIC video IDs:")
for title in titles:
    try:
        search_response = service.search().list(
            part='snippet',
            q=title,
            type='video',
            maxResults=5
        ).execute()
        
        for item in search_response.get('items', []):
            if item['snippet']['title'] == title:
                video_id = item['id']['videoId']
                print(f"  {title}")
                print(f"    Video ID: {video_id}")
                break
        else:
            print(f"  {title} - NOT FOUND")
    except Exception as e:
        print(f"  {title} - ERROR: {e}")
