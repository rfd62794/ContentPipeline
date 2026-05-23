# ADR-YT-002: OAuth Token Management via gcloud ADC

## Status
Accepted (Superseded)

## Context
YouTube Data API v3 requires OAuth2 for video upload. Token must persist between runs without requiring re-consent each time.

Options for token storage:
1. **Environment Variables**: Token stored in `.env`. Rejected — tokens are large JSON objects, not suitable for env vars.
2. **Database**: Token stored in content-engine.db. Rejected — overkill, adds database dependency for simple auth.
3. **Cloud Storage**: Token stored in cloud service. Rejected — adds external dependency, network latency.
4. **Local File**: Token stored in local JSON file. Rejected — manual token management required.
5. **gcloud ADC**: Application Default Credentials managed by gcloud. Accepted — standard pattern, no secrets in repo.

## Decision
Use gcloud Application Default Credentials (ADC) for authentication. Token management handled by gcloud auth layer.

### Implementation
- Authentication: `google.auth.default()` with YouTube upload scope
- Credential setup: `gcloud auth application-default login` with YouTube upload scope
- Token management: Handled automatically by gcloud auth layer
- No local token file: gcloud manages credentials in system ADC location
- No secrets in `.env`: All credential management via gcloud CLI
- First run: Browser consent flow via gcloud CLI
- Subsequent runs: Credentials loaded from ADC, no consent required

## Consequences
- gcloud must be installed and authenticated on any machine running uploads
- Tower deployment requires one-time `gcloud auth application-default login` per machine
- No secrets in repository or `.env` file
- Standard Google Cloud authentication pattern
- Automatic token refresh handled by gcloud auth layer

## Security Considerations
- Credentials managed by gcloud in system ADC location
- No secrets in repository or environment variables
- Credentials follow system user permissions
- Token refresh handled automatically by gcloud
- Credentials can be revoked via Google Cloud Console

## Alternatives Considered
- **Environment Variables**: Rejected — tokens are large JSON objects.
- **Database Storage**: Rejected — overkill, adds database dependency.
- **Cloud Storage**: Rejected — adds external dependency, network latency.
- **Local File**: Rejected — manual token management required.
- **In-Memory Only**: Rejected — would require consent every run.

## Amendment (2026-05-22)
Superseded by gcloud ADC. Token management handled by gcloud auth layer. Local file storage approach was replaced due to gcloud availability and security benefits.
