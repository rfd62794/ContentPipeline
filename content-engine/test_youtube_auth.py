"""
Temporary script to test YouTube API with manual OAuth token
Use OAuth 2.0 Playground: https://developers.google.com/oauthplayground
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import sys

def test_youtube_with_token():
    print("Get OAuth token from: https://developers.google.com/oauthplayground")
    print("1. Select: YouTube Data API v3 -> https://www.googleapis.com/auth/youtube.readonly")
    print("2. Click 'Authorize APIs'")
    print("3. Click 'Exchange authorization code for tokens'")
    print("4. Copy the access token")
    
    token = input("\nPaste your OAuth 2.0 access token: ").strip()
    
    if not token:
        print("No token provided")
        sys.exit(1)
    
    try:
        credentials = Credentials(token)
        service = build('youtube', 'v3', credentials=credentials)
        
        # Test with minimal quota usage
        print("\nTesting authentication with minimal query...")
        # Just test if we can make any authenticated call
        response = service.channels().list(
            part='id',
            mine=True
        ).execute()
        
        if response.get('items'):
            channel = response['items'][0]
            print(f"✓ Authentication successful!")
            print(f"✓ Channel ID: {channel['id']}")
            
            # Now try to get full channel data
            print("\nTesting full channel metadata...")
            full_response = service.channels().list(
                part='snippet,statistics',
                id=channel['id']
            ).execute()
            
            if full_response.get('items'):
                full_channel = full_response['items'][0]
                print(f"✓ Channel: {full_channel['snippet']['title']}")
                print(f"✓ Subscribers: {full_channel['statistics']['subscriberCount']}")
                print(f"✓ Total Videos: {full_channel['statistics']['videoCount']}")
            else:
                print("✗ No full channel data found")
        else:
            print("✗ No channel found")
        
        # Test video library (skip for now due to quota)
        print("\nSkipping video library test due to quota limits...")
        print("✓ Authentication verified - YouTube API integration working")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    test_youtube_with_token()