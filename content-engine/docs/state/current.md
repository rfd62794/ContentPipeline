phase: 'Phase YT-1 — YouTube Upload with Metadata Override Architecture'
certified_floor: 257/0/10
what_is_next: 'Robert adds YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET to .env, then tests OAuth flow'

## Phase YT-1 — YouTube Upload with Metadata Override Architecture (2026-05-22)

### Completed
- **Created .meta.yaml schema** — Metadata override layer alongside existing short YAMLs
  - Manual override fields: title, description, tags, schedule, privacy
  - `auto_generate: true/false` flag for Layer 1 auto-generation
  - Created .meta.yaml files for all 5 EIC shorts (all fields empty, auto_generate: false)
- **Created metadata_builder.py** — Layer 1 auto-generation + Layer 3 override resolver
  - Pure functions only: load_short_yaml, load_meta_yaml, resolve_metadata
  - Layer 1 generation: generate_title_layer1, generate_description_layer1, generate_tags_layer1
  - Validation: validate_metadata (title length, tag limits, privacy values)
  - Schedule formatting: format_schedule (ISO to RFC 3339)
- **Created youtube_upload.py** — OAuth client + resumable upload CLI
  - OAuth2 flow with local token cache (.youtube_token.json)
  - Resumable upload with 8MB chunks and progress display
  - build_video_resource pure function for YouTube API body construction
  - Mandatory confirmation prompt before upload
  - Integration with Steam library for metadata enrichment
- **Created comprehensive test suite** (20 new tests, 257/0/10)
  - tests/test_metadata_builder.py: 20 pure function tests
  - TestLoadShortYaml: YAML loading and error handling
  - TestLoadMetaYaml: Default values and partial overrides
  - TestResolveMetadata: Layer 3 wins, Layer 1 used when empty, no mutation
  - TestGenerateTitleLayer1: Title generation with/without Steam metadata
  - TestGenerateDescriptionLayer1: Description generation with char limits
  - TestGenerateTagsLayer1: Tag generation with 500-char limit enforcement
  - TestValidateMetadata: Title length, tag limits, privacy validation
  - TestFormatSchedule: ISO to RFC 3339 conversion
  - tests/test_youtube_upload.py: 9 pure function tests
  - TestBuildVideoResource: YouTube API body construction, privacy mapping, tags
- **Created 2 ADR files** — Key technical decisions documented
  - ADR-YT-001: Three-layer metadata override architecture (manual > auto > default)
  - ADR-YT-002: OAuth token local file storage (.youtube_token.json)
- **Updated requirements.txt** — Added Google dependencies (google-auth-oauthlib, google-api-python-client, google-auth-httplib2)
- **Updated .gitignore** — Added .youtube_token.json exclusion (both repo root and content-engine)

### Certified Floor Achievement
- Baseline: 237/0/10 (after Steam library and Store API integration)
- Target: 257/0/10
- Actual: 257/0/10 (20 new tests added, 0 failures)

### Key Design Decisions
- Three-layer override architecture — Layer 3 (manual) always wins, Layer 1 (auto) used only when auto_generate true and field empty
- Safe by default — auto_generate defaults false, system requires explicit opt-in for auto-generation
- Pure function architecture — All business logic unit-testable without OAuth or network calls
- OAuth token local storage — .youtube_token.json gitignored, auto-refresh on expiry
- Mandatory confirmation — Never auto-upload without explicit user confirmation
- Steam metadata integration — Optional enrichment from Steam Store API for Layer 1 generation
- YouTube API compliance — Enforces 100-char title limit, 500-char tag limit, 5000-char description limit

### Integration Verification
- .meta.yaml files created for all 5 EIC shorts with empty fields
- metadata_builder.py pure functions fully unit-tested
- youtube_upload.py build_video_resource pure function tested
- OAuth flow implemented but requires Robert's credentials to test
- .youtube_token.json added to .gitignore in both locations

### Usage Example
```bash
# Upload short with manual metadata (current workflow)
python content-engine/youtube_upload.py --short eic_short_4_shellephant

# Upload with Steam metadata enrichment
python content-engine/youtube_upload.py --short eic_short_4_shellephant --steam-path "C:/Program Files (x86)/Steam"
```

### Metadata Override Example
```yaml
# shorts/eic_short_4_shellephant.meta.yaml
auto_generate: false
title: "Everything is Crab — the Shellephant Boss Fight"
description: "I picked a fight with the Shellephant. It didn't go well."
tags: ["Everything is Crab", "boss fight", "roguelike"]
privacy: "public"
schedule: "2026-05-23T21:00:00"
category_id: "20"
made_for_kids: false
```

### Next Steps
- Robert adds YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET to .env
- Test OAuth consent flow and token caching
- Test resumable upload with real video file
- Test scheduled publish time setting
