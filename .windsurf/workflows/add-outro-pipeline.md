---
description: Add add_outro config flag to produce_short.py to auto-append Like & Subscribe beat
---

## Context

Currently the "Like and subscribe if you're enjoying the ride." CTA beat is manually added to each YAML as the final beat entry. This is error-prone and creates unnecessary YAML clutter.

## Directive

Add an `add_outro` flag to the short YAML schema and `produce_short.py` pipeline so that setting `add_outro: true` automatically appends the CTA beat without requiring a manual beat entry.

## Requirements

1. **YAML schema** — add optional field `add_outro: bool` (default: `false`)
2. **Outro beat construction** — when `add_outro: true`, derive the outro beat from the last beat in the list:
   - `clip_start`: last beat's `clip_end`
   - `clip_end`: last beat's `clip_end` + `outro_duration` seconds (default: 4)
   - `clip_end` must be clamped to the actual source video duration — do not crash or produce corrupt output if the extension exceeds file length
   - `line`: "Like and subscribe if you're enjoying the ride."
   - No separate timestamp config needed — works with any source video automatically
3. **Pipeline injection** — after loading beats from YAML, if `add_outro: true`, append the constructed outro beat to the beat list before processing
4. **Per-game outro override** — optional `outro_clip` field on the short YAML overrides the auto-constructed outro with an explicit `clip_start`/`clip_end`/`line`, for cases where a specific gameplay moment is preferred for the CTA
5. **Tests** — add unit tests in `tests/test_shorts_voice.py` or a new `tests/test_shorts_outro.py` covering:
   - `add_outro: false` leaves beat list unchanged
   - `add_outro: true` appends the outro beat as the final entry with correct `clip_start` derived from last beat's `clip_end`
   - Outro beat inherits voice settings from the short config
   - When `clip_end + outro_duration` exceeds source video length, `clip_end` is clamped to file duration rather than crashing

## Acceptance Criteria

- All existing YAMLs with manual outro beats continue to work unchanged
- New YAMLs with `add_outro: true` produce identical output to manually-added outro beats
- `add_outro` is optional and defaults to `false` (no breaking change)
