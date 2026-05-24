# ADR-REF-001: Strangler Fig Pattern for Audio/Video Refactoring

**Status:** Proposed  
**Date:** May 2026  
**Context:** Audio/Video Pipeline Refactoring

## Context

The current `assembler.py` and `produce_short.py` have significant technical debt:
- Audio mixing logic embedded in `assembler.py` with minimal test coverage
- FFmpeg command construction mixed with business logic
- Text stacking has pure function tests, but audio mixing has almost none
- Production sequence is largely integration-tested, not unit-tested

Direct refactoring ("big bang") is risky without a safety net. Breaking behavior in audio mixing or FFmpeg commands would corrupt short production.

## Decision

Adopt the **Strangler Fig pattern** (Martin Fowler) for safe, incremental refactoring:

### Phase REF-1: Test Coverage Extension

**Goal:** Lock current behavior with comprehensive tests before touching production code.

**Scope:**
- **`assembler.py`** — FFmpeg command construction
  - FFmpeg audio mixing commands
  - FFmpeg video scaling commands
  - FFmpeg text overlay commands
  - FFmpeg scene transitions
  - Command parameter validation

- **`produce_short.py`** — Full production sequence
  - Audio mixing orchestration
  - FFmpeg pipeline orchestration
  - File path handling
  - Error handling and recovery

- **Audio mixing equivalents** — Current embedded logic
  - Volume adjustment logic
  - Audio stream mixing
  - Format conversion parameters

**Test Strategy:**
- Pure function tests for FFmpeg command construction
- Mock subprocess calls for integration testing
- Snapshot testing for command line equivalence
- Parameter validation tests
- Error path testing

**Success Criteria:**
- 80%+ coverage on identified functions
- All FFmpeg command variants tested
- Production sequence end-to-end tests
- No behavior changes during this phase

### Phase REF-2: Strangler Fig

**Goal:** Build new modules alongside old ones, route traffic incrementally, strangle old code when proven.

**New Modules:**
- **`core/audio_mixer.py`** — Extracted audio mixing logic
  - Pure functions for audio mixing operations
  - Volume adjustment utilities
  - Format conversion helpers
  - Stream mixing orchestration

- **`core/ffmpeg.py`** — Extracted FFmpeg operations
  - FFmpeg command builders
  - Parameter validation
  - Common operation patterns (scaling, mixing, overlays)
  - Error handling and retry logic

**Migration Strategy:**
1. Create new modules with comprehensive tests
2. Add feature flags to route between old and new implementations
3. Route 10% of traffic to new implementation
4. Monitor for behavior equivalence
5. Incrementally increase traffic to new implementation
6. When new implementation is proven, remove old code

**Feature Flag Example:**
```python
USE_NEW_AUDIO_MIXER = os.getenv("USE_NEW_AUDIO_MIXER", "false") == "true"

if USE_NEW_AUDIO_MIXER:
    from core.audio_mixer import mix_audio_streams
else:
    # Old embedded logic
    pass
```

**Success Criteria:**
- New modules have 90%+ test coverage
- Feature flags allow A/B testing
- Production metrics show equivalence
- Old code removed when new is proven

## Consequences

### Positive
- **Safe refactoring** — Test coverage prevents regression
- **Incremental risk** — Feature flags allow rollback
- **Proven migration** — Industry-standard pattern
- **Parallel development** — New modules can be developed alongside old code
- **Clear rollback path** — Disable feature flag if issues arise

### Negative
- **Two-phase approach** — Requires upfront investment in tests
- **Temporary complexity** — Feature flags add conditional logic
- **Longer timeline** — Not immediate gratification
- **Maintenance burden** — Two code paths during transition

### Mitigations
- **Phase REF-1** investment provides immediate safety net
- **Feature flags** are temporary, removed after migration
- **Test coverage** makes future changes safer
- **Industry pattern** — well-documented approach with known benefits

## Alternatives Considered

1. **Big Bang Refactoring** — Rejected due to high risk without test coverage
2. **Complete Rewrite** — Rejected due to time and complexity
3. **Ignore Technical Debt** — Rejected as it will compound over time

## References

- Martin Fowler: "Strangler Fig Pattern" - https://martinfowler.com/bliki/StranglerFig
- Current test floor: 542/0/10/3
- Target test floor for REF-1: 600+ passing tests

## Timeline

- **Current:** Live session tool complete, OBS setup complete, stream launcher with dynamic game capture
- **Tonight:** Live gameplay session (Dorfromantik)
- **Tomorrow:** Phase REF-1 — Test Coverage Extension
- **Future:** Phase REF-2 — Strangler Fig migration