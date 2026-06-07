---
description: Add add_outro config flag to produce_short.py to auto-append Like & Subscribe beat
---

## Context

Currently the "Like and subscribe if you're enjoying the ride." CTA beat is manually added to each YAML as the final beat entry. This is error-prone and creates unnecessary YAML clutter.

## Directive

Add an `add_outro` flag to the short YAML schema and `produce_short.py` pipeline so that setting `add_outro: true` automatically appends the CTA beat without requiring a manual beat entry.

## Requirements

1. **YAML schema** — add optional field `add_outro: bool` (default: `false`)
2. **Outro config** — add an `OUTRO_CONFIG` block in `produce_short.py` (or a shared config file) containing:
   - `clip_source`: the source video path (same as the short's `source`)
   - `clip_start` / `clip_end`: timestamp of the CTA clip in the recording
   - `duration`: beat duration in seconds
   - `line`: "Like and subscribe if you're enjoying the ride."
3. **Pipeline injection** — after loading beats from YAML, if `add_outro: true`, append the outro beat to the beat list before processing
4. **Per-game outro support** — consider a `outro_clip` field that overrides the default outro, allowing different CTA clips per game session
5. **Tests** — add unit tests in `tests/test_shorts_voice.py` or a new `tests/test_shorts_outro.py` covering:
   - `add_outro: false` leaves beat list unchanged
   - `add_outro: true` appends the outro beat as the final entry
   - Outro beat inherits voice settings from the short config

## Acceptance Criteria

- All existing YAMLs with manual outro beats continue to work unchanged
- New YAMLs with `add_outro: true` produce identical output to manually-added outro beats
- `add_outro` is optional and defaults to `false` (no breaking change)
