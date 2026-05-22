# ADR-RS-004: Timestamp alignment via additive offset

## Status
Accepted

## Context
Whisper produces timestamps relative to audio start — always from `0.0`. The tool starts recording simultaneously with VLC at a known `--start-time` offset. The alignment guarantee is: `video_position = whisper_segment.start + start_time_offset`. This arithmetic is the entire alignment mechanism. It assumes VLC and sounddevice both start within the same Python call's latency window (~100–300ms), which is acceptable for editorial annotation use (not frame-precise).

## Decision
All `segment["start"]` values are offset by `args.start_time` before writing. The raw audio timestamps are never written to the session file — only video-aligned timestamps appear.

## Consequences
Sub-second alignment drift is possible (~100–300ms). This is acceptable for spoken annotation. Not acceptable for subtitle burn-in. Subtitle use requires a different approach and is explicitly deferred.
