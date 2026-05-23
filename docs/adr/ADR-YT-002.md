# ADR-YT-002: OAuth Token Local File Storage

## Status
Accepted

## Context
YouTube Data API v3 requires OAuth2 for video upload. Token must persist between runs without requiring re-consent each time.

Options for token storage:
1. **Environment Variables**: Token stored in `.env`. Rejected — tokens are large JSON objects, not suitable for env vars.
2. **Database**: Token stored in content-engine.db. Rejected — overkill, adds database dependency for simple auth.
3. **Cloud Storage**: Token stored in cloud service. Rejected — adds external dependency, network latency.
4. **Local File**: Token stored in local JSON file. Accepted — simple, no external dependencies, works offline.

## Decision
OAuth token stored at `.youtube_token.json` at repo root. Gitignored. Refreshed automatically on expiry.

### Implementation
- Token file path: `.youtube_token.json` (repo root)
- File format: JSON from Google OAuth credentials
- Auto-refresh: Google API library handles token refresh automatically
- Gitignore: Token file added to `.gitignore` to prevent committing credentials
- First run: Browser consent flow required to obtain initial token
- Subsequent runs: Token loaded from file, no consent required

## Consequences
- Token file must exist on any machine running uploads
- Tower deployment requires one-time browser consent per machine
- Token file not version-controlled (security best practice)
- Simple file-based storage, no external dependencies
- Automatic token refresh handled by Google API library

## Security Considerations
- Token file contains OAuth credentials
- Must be gitignored to prevent committing to repo
- File permissions should be restricted (user read/write only)
- Token expires and refreshes automatically
- If token file is compromised, revoke in Google Cloud Console

## Alternatives Considered
- **Environment Variables**: Rejected — tokens are large JSON objects.
- **Database Storage**: Rejected — overkill, adds database dependency.
- **Cloud Storage**: Rejected — adds external dependency, network latency.
- **In-Memory Only**: Rejected — would require consent every run.
