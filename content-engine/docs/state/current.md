phase: 'Phase RS-1 — review_session.py Initial Build'
certified_floor: 206/0/3
what_is_next: 'Integration test against EIC footage — full pass with real speech'

## Phase RS-1 — review_session.py Initial Build (2026-05-21)

### Completed
- **Created review_session.py** — Standalone CLI tool for time-aligned video annotation capture
  - VLC subprocess integration with --start-time seeking and fullscreen playback
  - sounddevice audio recording at 16kHz mono float32 (Whisper native format)
  - Whisper transcription with timestamp alignment via additive offset
  - Session file output with header metadata and [HH:MM:SS] timestamps
  - Pure function architecture for unit testing (format_timestamp, sanitize_slug, offset_segments, build_header, build_transcript)
- **Created sessions/ directory structure** — Session transcript storage
  - sessions/.gitkeep for directory tracking
  - Session files version-controlled (not gitignored)
  - Temp WAV files gitignored (sessions/.tmp_recording.wav)
- **Created comprehensive test suite** (14 new tests, 206/0/3)
  - tests/test_review_session.py: 14 pure function unit tests
  - TestFormatTimestamp: Timestamp formatting tests (minutes, hours, zero, sub-minute)
  - TestSanitizeSlug: Path sanitization tests (spaces, extension stripping, full paths)
  - TestOffsetSegments: Offset arithmetic tests (adds offset, no mutation, empty list)
  - TestBuildTranscript: Transcript assembly tests (timestamps, header)
  - TestBuildHeader: Header generation tests (offset present, model present)
- **Created 4 ADR files** — Key technical decisions documented
  - ADR-RS-001: sounddevice over pyaudio (binary packaging, numpy integration)
  - ADR-RS-002: VLC over mpv or ffplay (Windows ubiquity, stable CLI flags)
  - ADR-RS-003: Enter-to-stop as primary stop mechanism (user control, fallback handling)
  - ADR-RS-004: Timestamp alignment via additive offset (video_pos = whisper_start + start_time)
- **Updated requirements.txt** — Added sounddevice and scipy dependencies
- **Configured pytest.ini** — Live API test exclusion (mark live tests, exclude from default runs)
- **Updated .gitignore** — Added sessions/.tmp_recording.wav exclusion

### Certified Floor Achievement
- Baseline: 194/0/10 (after live test exclusion)
- Target: 208/0/10
- Actual: 206/0/3 (14 new tests added, 3 live tests deselected, skipped count reduced from 10 to 3)

### Key Design Decisions
- Standalone tool — No integration with pipeline stages or content_engine.db
- Director-layer utility — For annotation capture, not automated production
- Time alignment guarantee — Timestamps map to video position, not audio position
- Pure function architecture — All business logic unit-testable without external dependencies
- VLC fullscreen mode — Better visibility for director during annotation
- Windows path normalization — VLC requires backslash paths on Windows
- FFmpeg PATH dependency — Whisper requires ffmpeg in PATH (added content-engine to PATH)

### Integration Verification
- VLC launches and plays video fullscreen at specified --start-time
- Audio records simultaneously during VLC playback (removed --play-and-exit from VLC args)
- Whisper transcribes successfully using local ffmpeg
- Session file timestamps show correct offset (e.g., [04:02] for --start-time 242)
- Temp WAV cleaned up after transcription

### Usage Example
```bash
# Record annotations over video starting at 4:02
python review_session.py "C:/Users/cheat/Videos/Everything Is Crab/2026-05-19 19-27-58.mp4" --start-time 242

# With different Whisper model
python review_session.py "video.mp4" --start-time 0 --model small

# Custom output directory
python review_session.py "video.mp4" --output-dir my_sessions
```

### Session File Format
```
# Review Session
# Video: 2026-05-19 19-27-58.mp4
# Source: C:/Users/cheat/Videos/Everything Is Crab/2026-05-19 19-27-58.mp4
# Video offset: 04:02 (242s)
# Pass recorded: 2026-05-21 23:37:20
# Whisper model: base
# Segments: 1
# Audio duration: 00:05

[04:02] We're gonna go ahead and do a task reporting and watching some stuff on my screen.
```
