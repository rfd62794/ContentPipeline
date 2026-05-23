# ADR-YT-001: Three-Layer Metadata Override Architecture

## Status
Accepted

## Context
ContentPipeline needs to support both manual director control and future autonomous operation. Neither pure manual nor pure auto serves the journey from manual to autonomous.

The pipeline currently produces Short MP4s and metadata packages manually. Upload to YouTube is done by hand. Automating upload is necessary for scaling, but the creative metadata (titles, descriptions, tags) requires director curation.

Pure manual upload doesn't scale. Pure auto-generated metadata lacks the creative quality of manual curation. A middle ground is needed that allows gradual transition from manual to autonomous.

## Decision
Three-layer metadata override architecture:

- **Layer 3 (Manual Override)**: Director-provided fields in `.meta.yaml` sidecar files. Always wins if non-empty.
- **Layer 1 (Auto-Generation)**: Generated from Steam Store API + short YAML content. Used only when `auto_generate: true` and field is empty.
- **Layer 2 (Templates)**: Deferred until patterns solidify across 10+ Shorts.

### Resolution Rules
1. If Layer 3 field is non-empty → use Layer 3 value
2. If Layer 3 field is empty AND `auto_generate: true` → use Layer 1 value
3. If Layer 3 field is empty AND `auto_generate: false` → use empty/default value

### Implementation
- `.meta.yaml` sidecar required per short
- `auto_generate` defaults to `false` — system is safe by default
- Director can flip `auto_generate: true` when Layer 1 output is trusted
- Layer 1 generation uses Steam genres/tags for auto-tagging
- Layer 1 generation uses Steam description + segment count for auto-description

## Consequences
- `.meta.yaml` sidecar required per short
- `auto_generate` defaults false — system is safe by default
- Director maintains full control until explicitly enabling auto-generation
- Gradual transition path from manual to autonomous
- Additional file management overhead (sidecar files)
- Layer 2 templates deferred until patterns established

## Alternatives Considered
- **Pure Manual**: No auto-generation, all fields manual. Rejected — doesn't scale.
- **Pure Auto**: All fields auto-generated. Rejected — lacks creative quality.
- **Two-Layer (Manual + Auto)**: No template layer. Rejected — templates useful for series patterns.
- **Single Config File**: All metadata in main short YAML. Rejected — separates creative from technical config.
