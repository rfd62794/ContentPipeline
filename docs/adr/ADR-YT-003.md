# ADR-YT-003: YouTube Library Data Authentication

## Status
Accepted

## Context
YouTube Library Data Client needs to pull public channel metadata, video libraries, and playlist data from YouTube Data API v3. This is read-only access to public data, not authenticated user data.

## Decision
YouTube Library Data Client will support dual authentication modes:

1. **API Key Mode (Primary)**: Use YouTube Data API v3 API key for public data access
   - Requires Google Cloud project with YouTube Data API v3 enabled
   - API key stored in environment variable `YOUTUBE_API_KEY` or passed via `--api-key` CLI flag
   - Suitable for public channel data, video libraries, playlists
   - No OAuth flow required, simpler for read-only operations

2. **gcloud ADC Mode (Fallback)**: Use gcloud Application Default Credentials
   - Requires `gcloud auth application-default login` with YouTube read scope
   - Used when API key is not provided
   - Maintains consistency with youtube_upload.py authentication pattern
   - Required for authenticated user data (e.g., `mine=True` queries)

## Implementation Details

### API Key Configuration
```python
# CLI usage
python youtube_library.py --channel --channel-id UCXuqSBlHAE6Xw-yeJA0Tunw --api-key YOUR_API_KEY

# Environment variable
export YOUTUBE_API_KEY=YOUR_API_KEY
python youtube_library.py --channel --channel-id UCXuqSBlHAE6Xw-yeJA0Tunw
```

### Dual Mode Support
```python
class YouTubeLibrary:
    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.service = build('youtube', 'v3', developerKey=api_key)
        else:
            credentials, project = default(scopes=["https://www.googleapis.com/auth/youtube.readonly"])
            self.service = build('youtube', 'v3', credentials=credentials)
```

### Channel ID Support
- Public channels: Use `--channel-id` flag with API key
- Authenticated user: Use `--channel` without channel ID (requires gcloud ADC)

## Rationale
- **API Key Mode**: Simpler for public data access, no OAuth overhead, aligns with YouTube Data API v3 best practices for read-only operations
- **gcloud ADC Mode**: Maintains consistency with existing youtube_upload.py pattern, provides fallback for authenticated operations
- **Dual Mode**: Flexibility to support both public and authenticated data access patterns

## Consequences
- Positive: Simpler authentication for public data, no OAuth flow required for most use cases
- Positive: Consistent with youtube_upload.py when using gcloud ADC mode
- Positive: Flexibility to support both public and authenticated data access
- Negative: Requires Google Cloud project setup for API key generation
- Negative: API key management required (environment variable or CLI flag)

## Alternatives Considered
1. **OAuth-only**: Rejected due to complexity for read-only public data access
2. **API Key-only**: Rejected to maintain consistency with youtube_upload.py and support authenticated operations
3. **Service Account**: Rejected due to complexity and overkill for read-only operations

## Related Decisions
- ADR-YT-002: YouTube Upload Authentication (gcloud ADC for upload operations)
