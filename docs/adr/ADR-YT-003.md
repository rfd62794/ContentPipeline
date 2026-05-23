# ADR-YT-003: YouTube Library Data Authentication

## Status
Accepted

## Context
YouTube Library Data Client needs to pull channel metadata, video libraries, and playlist data from YouTube Data API v3. This includes private data such as subscriber counts, private video status, and scheduled videos. gcloud ADC authentication proved unreliable due to scope configuration issues and quota restrictions during testing.

## Decision
YouTube Library Data Client will use OAuth 2.0 with refresh token for persistent access to user channel data.

## Implementation Details

### Authentication Flow
```python
class YouTubeLibrary:
    SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
    TOKEN_FILE = ".youtube_token.json"
    CLIENT_SECRET_FILE = "client_secret.json"
    
    def __init__(self, client_secret_path: Optional[str] = None):
        # Load existing credentials or run OAuth flow
        self._load_credentials()
        
    def _load_credentials(self):
        # Check for existing token
        if os.path.exists(self.TOKEN_FILE):
            self.credentials = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
        
        # If no valid credentials, run OAuth flow
        if not self.credentials or not self.credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, self.SCOPES)
            self.credentials = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(self.TOKEN_FILE, 'w') as token:
                token.write(self.credentials)
```

### Setup
1. **Create OAuth 2.0 credentials in Google Cloud Console:**
   - Go to console.cloud.google.com → youtubeauto-497203
   - APIs & Services → Credentials
   - Create credentials → OAuth client ID
   - Application type: Desktop application
   - Download client_secret.json

2. **First-time authentication:**
```bash
python youtube_library.py --channel
```
- Browser opens for OAuth consent
- Grant YouTube readonly access
- Token saved to .youtube_token.json

3. **Subsequent usage:**
- Token automatically refreshed when expired
- No manual re-authentication required

### Usage
```python
library = YouTubeLibrary()
channel = library.get_channel_metadata()  # Authenticated user's channel
videos = library.get_video_library()      # All videos including private/scheduled
playlists = library.get_playlists()       # All playlists including private
```

## Rationale
- **Persistent Access**: Refresh token provides indefinite access until revoked
- **User Data Access**: OAuth provides access to private channel data, scheduled videos, subscriber counts
- **Reliability**: More reliable than gcloud ADC which had scope configuration issues
- **Standard Pattern**: OAuth with refresh token is the standard pattern for YouTube user data access
- **Consistency**: Similar to original youtube_upload.py design before ADC switch

## Consequences
- Positive: Persistent access to user channel data without daily re-authentication
- Positive: Access to private data including scheduled videos and subscriber counts
- Positive: Standard OAuth pattern, well-documented and reliable
- Positive: Token refresh handled automatically
- Negative: Requires one-time OAuth setup (client_secret.json from Google Cloud Console)
- Negative: First-time use requires browser-based OAuth consent

## Alternatives Considered
1. **gcloud ADC**: Rejected due to scope configuration issues and unreliable authentication
2. **API Key**: Rejected because API keys only access public data, not private/scheduled videos or subscriber counts
3. **Service Account**: Rejected because service accounts cannot access user YouTube data (server-to-server only)

## Related Decisions
- ADR-YT-002: YouTube Upload Authentication (gcloud ADC for upload operations)
