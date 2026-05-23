# ADR-YT-003: YouTube Library Data Authentication

## Status
Accepted

## Context
YouTube Library Data Client needs to pull channel metadata, video libraries, and playlist data from YouTube Data API v3. This includes private data such as subscriber counts, private video status, and scheduled videos.

## Decision
YouTube Library Data Client will use gcloud Application Default Credentials (ADC) for authentication, consistent with youtube_upload.py.

## Implementation Details

### Authentication
```python
class YouTubeLibrary:
    def __init__(self):
        credentials, project = default(scopes=["https://www.googleapis.com/auth/youtube.readonly"])
        self.service = build('youtube', 'v3', credentials=credentials)
```

### Setup
```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/youtube.readonly
```

### Usage
```python
library = YouTubeLibrary()
channel = library.get_channel_metadata()  # Authenticated user's channel
videos = library.get_video_library()      # All videos including private/scheduled
playlists = library.get_playlists()       # All playlists including private
```

## Rationale
- **Consistency**: Same authentication pattern as youtube_upload.py
- **Private Data Access**: ADC provides access to private video data, scheduled videos, and subscriber counts
- **Simplicity**: Single authentication mode, no API key management required
- **Scope Alignment**: Read-only scope matches the library data use case

## Consequences
- Positive: Consistent with existing youtube_upload.py authentication
- Positive: Access to private data including scheduled videos and subscriber counts
- Positive: Single authentication mode reduces complexity
- Negative: Requires gcloud CLI setup
- Negative: Cannot access public channel data without authentication

## Alternatives Considered
1. **API Key Mode**: Rejected because API keys only access public data, not private/scheduled videos or subscriber counts
2. **OAuth Flow**: Rejected because gcloud ADC provides the same access with simpler setup
3. **Service Account**: Rejected due to complexity and overkill for read-only operations

## Related Decisions
- ADR-YT-002: YouTube Upload Authentication (gcloud ADC for upload operations)
