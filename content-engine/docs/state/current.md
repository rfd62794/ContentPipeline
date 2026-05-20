phase: 'Phase S3 — Dave the Diver Shorts Production Run'
certified_floor: 145/0/10
what_is_next: 'Phase S4 — YouTube Publish Integration'

## Phase S2 — Process Watcher + Own-Game Capture (2026-05-19)

### Completed
- **Created core/process_watcher.py** — Process detection and OBS trigger
  - `is_running(process_name)` — Uses Windows tasklist via subprocess (no external dependencies)
  - `watch(process_name, scene, poll_interval)` — Blocking call, state machine: WAITING → RECORDING → DONE
  - Detects game process, switches OBS scene (optional), starts recording
  - Stops recording when process exits, returns file path
  - Never hardcodes process name — game-agnostic, caller provides name
  - All OBS calls go through OBSCapture parameter — never imports obsws_python directly
  - Every state transition logged via Logger
  - Exception-safe — subprocess failures return False, never crash
- **Created pipeline_watch.py** — CLI entry point for watch command
  - `--game` (required): Process name to watch for
  - `--scene` (optional): OBS scene to switch to before recording
  - `--poll` (optional): Poll interval in seconds (default: 5)
  - Thin wrapper — argument parsing and wiring only, business logic in ProcessWatcher
  - OBS connection failure exits cleanly with error message (exit code 1)
- **Created comprehensive test suite** (6 new tests, all passing)
  - test_is_running_true — Returns True when process in tasklist output
  - test_is_running_false — Returns False when process not in output
  - test_is_running_exception_safe — Returns False on subprocess exception
  - test_watch_starts_recording — Calls obs.start_recording() when process detected
  - test_watch_stops_recording — Calls obs.stop_recording() when process gone
  - test_watch_returns_filepath — Returns string from obs.stop_recording()

### Certified Floor Achievement
- Baseline: 128/0/10
- Target: 134/0/10
- Actual: 134/0/10 (exactly on target)

### Key Design Decisions
- Pure stdlib implementation — uses subprocess only (tasklist), no psutil or win32api
- Process name never hardcoded in module — caller provides it (e.g., "Everything is Crab.exe")
- watch() is blocking call — documented clearly, does not return until game closes
- All OBS calls go through OBSCapture parameter — loose coupling, testable
- Scene switching optional — caller can trigger OBS recording without scene change
- Exception-safe design — subprocess failures return False, never crash watcher
- CLI entry point is thin wrapper — business logic lives in ProcessWatcher

### Usage Example
```bash
# Basic watch
python pipeline_watch.py --game "Everything is Crab.exe"

# With scene switching
python pipeline_watch.py --game "Everything is Crab.exe" --scene "EIC_Capture"

# Custom poll interval
python pipeline_watch.py --game "Everything is Crab.exe" --poll 10
```

## Phase S3 — Dave the Diver Shorts Production Run (2026-05-19)

### Completed
- **Created config/game_folders.json** — Game process to folder mapping
  - Maps "Everything is Crab.exe" → "Everything Is Crab"
  - Maps "Dave the Diver.exe" → "Dave the Diver"
  - Maps "VoidDrift.exe" → "VoidDrift"
- **Updated process_watcher.py** — Added resolve_recording_path() method
  - Loads game_folders.json mapping
  - Inserts correct subfolder into OBS recording path
  - Falls back to raw path if mapping not found
  - Creates target directory and moves file if source exists
- **Created core/clip_sourcer.py** — YouTube clip download using yt-dlp
  - download_clip(url, start_time, end_time) — Downloads timestamped clip
  - Uses yt-dlp --download-sections for precise segment extraction
  - 5-second buffer around timestamps to ensure complete context
  - Creates output directory if missing
  - Returns filepath on success, empty string on failure
  - clip_exists(filepath) — Check if clip file exists
  - _parse_timestamp(timestamp) — Converts "MM:SS" or "HH:MM:SS" to seconds
- **Updated assembler.py** — Added attribution layer for shorts mode
  - _add_attribution_text() — Burns attribution text into video (top 5% of frame)
  - Attribution styling from config: font_size, color, y_pct, opacity
  - sanitize_drawtext() — Escapes special characters for FFmpeg filter syntax
  - Attribution integrated into _assemble_shorts() pipeline
  - Conditional rendering: only if attribution provided and enabled in config
- **Updated config.yaml** — Added 5 attribution configuration keys
  - shorts_attribution_enabled: Enable/disable attribution overlay
  - shorts_attribution_text: Default attribution text (can be overridden per-call)
  - shorts_attribution_y_pct: Vertical position (0.05 = top 5%)
  - shorts_attribution_font_size: Font size in pixels (default: 30)
  - shorts_attribution_color: Text color (default: white)
  - shorts_attribution_opacity: Text opacity (default: 0.85)
- **Created comprehensive test suite** (10 new tests, all passing)
  - test_process_watcher.py: 3 new tests for resolve_recording_path
    - test_resolver_finds_subfolder — Inserts correct subfolder from mapping
    - test_resolver_fallback_unmapped — Returns raw path if process not in mapping
    - test_resolver_missing_json — Returns raw path if config file missing
  - test_clip_sourcer.py: 5 new tests for clip download functionality
    - test_clip_sourcer_download — Calls yt-dlp with correct parameters
    - test_clip_sourcer_returns_path — Returns filepath on success
    - test_clip_sourcer_failure_safe — Returns empty string on yt-dlp failure
    - test_clip_sourcer_creates_dir — Creates output directory if missing
    - test_clip_sourcer_clip_exists — Checks file existence correctly
  - test_assembler.py: 2 new tests for attribution layer
    - test_assembler_attribution_position — Attribution positioned at top 5%
    - test_assembler_attribution_renders — Attribution text passed to FFmpeg

### Certified Floor Achievement
- Baseline: 134/0/10
- Target: 144/0/10
- Actual: 145/0/10 (exceeded target by 1 test)

### Key Design Decisions
- Game folder mapping in external JSON — easy to update without code changes
- Clip sourcer uses yt-dlp --download-sections — precise timestamp extraction
- 5-second buffer around timestamps — ensures complete context for clips
- Attribution layer uses FFmpeg drawtext filter — no external text rendering dependencies
- Attribution styling configurable — position, size, color, opacity all tunable
- Attribution conditional — only rendered when provided and enabled
- sanitize_drawtext handles Windows path issues — escapes colons, commas, brackets
- All subprocess calls mocked in tests — no actual yt-dlp or FFmpeg calls during testing

### Production Readiness
- Infrastructure complete: clip sourcing, attribution layer, path resolution
- produce_dave_shorts.py script created for production run
- Requires yt-dlp with FFmpeg for clip download (environment dependency)
- Attribution layer tested and functional
- Three Dave the Diver Shorts ready for production (Stat, Diagram, Reveal)
- Source: youtube.com/watch?v=LUTPCMkA7xQ (CohhCarnage Dave the Diver Episode 1)
- Attribution: "Gameplay via: CohhCarnage"

### Usage Example
```bash
# Download clip from YouTube
from core.clip_sourcer import ClipSourcer
sourcer = ClipSourcer("output/clips", logger)
clip_path = sourcer.download_clip(
    "https://www.youtube.com/watch?v=LUTPCMkA7xQ",
    "10:00",
    "10:30"
)

# Assemble short with attribution
from core.assembler import assemble_video
segments = [{"temp_file": clip_path, "segment_text": "Hook text"}]
assemble_video(
    segments,
    audio_path,
    output_path,
    temp_dir,
    config,
    shorts_mode=True,
    attribution="Gameplay via: CohhCarnage"
)

# Resolve recording path with game folder mapping
from core.process_watcher import ProcessWatcher
watcher = ProcessWatcher(obs, logger)
resolved_path = watcher.resolve_recording_path(
    "C:/Videos/2026-05-19 19-27-58.mp4",
    "Dave the Diver.exe",
    "config/game_folders.json"
)
# Returns: "C:/Videos/Dave the Diver/2026-05-19 19-27-58.mp4"
```

## Documentation Reframe (2026-05-19)

### Completed
- **Created SDD v1.0** — Primary project documentation defining GameReviewAgent as a Video to YouTube pipeline
  - Purpose: Given game analysis observation, produce YouTube Short (muted gameplay + lower third text + background music)
  - Primary loop: Observation → Script segmentation → Clip sourcing → Assembly → Review → YouTube publish
  - Two production paths: Analysis (sourced clips) and Own-game (OBS capture)
  - Core infrastructure table with module status
  - Phase map reflecting actual project state
- **ADR-009** — Aider integration deferred to separate project
- **ADR-010** — Two production paths locked (Analysis primary, Own-game secondary)
- **ADR-011** — scanner.py and repo_assessor.py documented as dormant
- **Project scope clarified** — Video to YouTube pipeline only, not Aider bot pipeline

### Key Decisions
- Aider integration is a separate project, not in scope for GameReviewAgent
- scanner.py and repo_assessor.py remain dormant with passing tests (17 tests)
- model_router.py routing logic remains active (used by llm_client.py)
- Next phase is S2 — Dave the Diver Shorts Production Run (3 shorts)
- clip_sourcer.py extraction planned for Phase S2
- P9 YouTube publish planned for Phase S3

### Project Identity
GameReviewAgent is a Video to YouTube pipeline that produces YouTube Shorts from game analysis observations. It runs on a local tower, requires no face/voice/live presence, and has two production paths: Analysis (sourced YouTube clips) and Own-game (OBS capture of running software).

## Phase E1 — OpenAgent Legacy Extraction (2026-05-18)

### Completed
- **Extracted core/scanner.py** from OpenAgent legacy (stdlib only, no external dependencies)
  - File tree scanning with smart truncation (60 file limit)
  - AST extraction for class detection
  - Test collection via pytest
  - Returns dict format: file_tree, ast_summary, test_list
- **Created core/model_router.py** with routing logic from OpenAgent legacy
  - Task type to model mapping: inventory (deepseek), directive (haiku), assembly (sonnet), fallback (free)
  - Pure routing only — no API calls, no business logic
  - llm_client.py receives model string and makes the call
- **Created core/repo_assessor.py** with two-stage pattern from assessor.py + writer.py
  - Stage 1: Cheap model (deepseek) structures assessment from scan result
  - Stage 2: Capable model (haiku) writes directive using assessment
  - Uses llm_client.py instead of raw requests.post
  - Robust JSON parsing with markdown fence stripping and ast.literal_eval fallback
- **Created comprehensive test suite** (17 new tests, all passing)
  - test_scanner.py: 6 tests for scanner functionality
  - test_repo_assessor.py: 6 tests for two-stage assessment pattern
  - test_model_router.py: 5 tests for routing logic

### Certified Floor Achievement
- Baseline: 111/0/10
- Target: 124/0/10
- Actual: 128/0/10 (exceeded target by 4 tests)

### Key Design Decisions
- Pure stdlib for scanner.py — no external dependencies
- Two-stage routing pattern preserved from OpenAgent legacy
- Integration with existing llm_client.py instead of raw HTTP requests
- All API calls mocked in tests — no real LLM calls during test runs
- No google-adk dependency introduced

## Recent Work (Post-S1)

### OBS WebSocket Integration (2026-05-18)
- **Investigated OBS WebSocket API** to enable VoidDrift-style automated production
- **Migrated to UV dependency manager** for faster package installation (10-100x speedup)
- **Switched from obs-websocket-py (v1.0) to obsws_python (v1.8.0)** due to API compatibility issues
- **Implemented core/obs_capture.py** with full contract:
  - `connect(host, port, password)`: Establish WebSocket connection
  - `start_recording()`: Start OBS recording
  - `stop_recording()`: Stop recording and return file path
  - `get_status()`: Get RecordingStatus (active, bytes, duration, timecode)
  - `set_scene(scene_name)`: Switch to specified scene
  - `list_scenes()`: Get list of available scenes
  - `disconnect()`: Close connection
  - Context manager support (`with OBSCapture() as obs:`)
- **API Patterns Discovered**:
  - No authentication required (empty password)
  - Response format: dataclasses with snake_case attributes
  - `get_output_settings('simple_file_output')` returns dict with 'path' key
  - File path updates when recording starts, not when it stops
  - Error 500 indicates recording state issues (already active / not active)
- **Created comprehensive test suite** (19 tests, all passing)
- **Dependency**: obsws_python v1.8.0 installed via UV

### Key Findings
- VoidDrift Short was NOT produced by ContentEngine - separate manual pipeline
- OBS WebSocket already enabled on localhost:4455, no password required
- Current VoidDrift production: Manual OBS recording at 720x1280 + FFmpeg post-processing
- OBS WebSocket integration provides foundation for future automated production

## Phase S1 Summary

### Completed
- Fixed 5 failing mock tests (test_assembler.py, test_clip_orchestrator.py, test_llm_client.py)
- Created core/logger.py with Logger class
- Resolved V-003 (hardcoded visual_type) - modified database schema to allow NULL
- Resolved V-004 (print statements) - replaced with Logger calls in stage runners
- Resolved V-005 (config as global) - modified core/asset_sourcer.py
- Added shorts_mode path to core/assembler.py (1080x1920 vertical output)
- Updated config.yaml with 6 shorts_mode configuration keys
- Created docs/adr/ADR-008.md documenting Shorts Mode decision
- Achieved certified floor: 90+ passed, 0 failed, 10 skipped

### Configuration Added
```yaml
shorts_mode: true
output_resolution_short: 1080x1920
shorts_music_path: assets/music/shorts_bgm.mp3
shorts_text_font: Arial
shorts_text_size: 48
shorts_text_color: "#FFFFFF"
shorts_lower_third_height_pct: 15
```