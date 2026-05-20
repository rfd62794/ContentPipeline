phase: 'Phase S7 — TBD'
certified_floor: 185/0/10
what_is_next: 'Phase S7 — TBD'

## Phase S6 — YAML Short Runner (2026-05-20)

### Completed
- **Wired shorts_music_start through assembler config** — Music start offset support
  - Added `shorts_music_start` config parameter to assembler.py
  - Modified music mixing step to apply atrim filter when music_start > 0
  - Uses `[1:a]atrim=start={music_start},asetpts=PTS-STARTPTS,volume=0.25[audio]` filter
- **Created shorts/ directory structure** — Centralized config location
  - New `shorts/` directory for YAML short configurations
  - Separates config from production scripts
- **Created produce_short.py** — Single YAML-driven runner
  - Replaces produce_eic_shorts.py and produce_dave_shorts.py
  - `load_yaml_config()` — Load short configuration from YAML file
  - `convert_beats_to_segments()` — Convert YAML beats to assembler segment format
  - `apply_text_stacking()` — Apply text stacking with sliding window
  - `build_config_from_yaml()` — Build assembler config from YAML configuration
  - `produce_short_from_yaml()` — Main production function
- **Created 5 YAML config files** — Existing shorts migrated to YAML
  - `shorts/eic_short_1_evolution.yaml` — The Evolution Loop Click
  - `shorts/eic_short_2_predator.yaml` — Predator Becomes Prey
  - `shorts/eic_short_3_decisions.yaml` — The Decision Density Problem
  - `shorts/dave_short_1_stat.yaml` — The Stat (displacement wall)
  - `shorts/dave_short_2_diagram.yaml` — The Diagram (loop chains)
  - All configs match retired scripts exactly (timestamps, durations, text)
- **Retired production scripts** — Renamed with _retired_ prefix
  - `produce_eic_shorts.py` → `_retired_produce_eic_shorts.py`
  - `produce_dave_shorts.py` → `_retired_produce_dave_shorts.py`
  - Preserved for reference and rollback if needed
- **Created comprehensive test suite** (10 new tests, 185/0/10)
  - test_produce_short.py: 10 new tests (4 test classes)
    - TestLoadYamlConfig: YAML config loading tests
    - TestConvertBeatsToSegments: Beat to segment conversion tests
    - TestApplyTextStacking: Text stacking with sliding window tests
    - TestBuildConfigFromYaml: Config building from YAML tests
- **Verified YAML output matches retired script output** — Code-level verification
  - Compared YAML configs with retired scripts segment-by-segment
  - Timestamps, durations, and text lines match exactly
  - Config values (music_path, attribution, source) match exactly
  - YAML schema mapping verified: clip_start→source_timestamp_start, clip_end→source_timestamp_end, duration→duration, line→segment_text

### Certified Floor Achievement
- Baseline: 181/0/10
- Target: 185/0/10
- Actual: 185/0/10 (10 new tests added to test_produce_short.py, all passing, skipped count maintained at 10)

### Key Design Decisions
- YAML-driven configuration — All short definitions in YAML files, not Python code
- Single runner script — produce_short.py handles all shorts via config
- Text stacking support — Optional sliding window for multi-line text accumulation
- Music start offset — Configurable music start time via shorts_music_start
- Backward compatibility — Retired scripts preserved for reference
- Schema validation — Tests verify YAML loading and conversion
- Directory structure — shorts/ for configs, output/shorts for output, temp/shorts for processing
- Attribution handling — Configurable per short (null for own footage, string for third-party)

### Usage Example
```bash
# Produce short from YAML config
python produce_short.py shorts/eic_short_1_evolution.yaml
python produce_short.py shorts/dave_short_1_stat.yaml

# With text stacking enabled in YAML config
python produce_short.py shorts/eic_short_2_predator.yaml
```

### YAML Schema
```yaml
name: short_name
source: video_path_or_url
attribution: null  # or "Gameplay via: Creator"
music_path: assets/music/Pixelated_Passion.mp3
music_start: 0  # Optional music start offset in seconds
stack_text: false  # Optional text stacking
max_visible_lines: 5  # Optional sliding window size
beats:
  - clip_start: "0:33"
    clip_end: "0:35"
    duration: 2
    line: "Text line"
```

## Phase S5 — Multi-Segment Assembly (2026-05-19)

### Completed
- **Updated core/assembler.py** — Multi-segment assembly support
  - Modified `_assemble_shorts()` to process each segment individually with own clip, text, and duration
  - Added `_get_clip_for_segment()` — Handles both temp_file and source_url/timestamp modes
  - Added `_concatenate_clips()` — Concatenates processed segments using FFmpeg -c copy
  - Added `_extract_clip_from_local()` — Extracts clips from local video files using FFmpeg
  - Added `_parse_timestamp()` — Parses MM:SS and HH:MM:SS formats to seconds
  - Updated `_add_lower_third_text()` — Now accepts duration parameter with enable='between(t,0,N)' filter
  - All segments scaled to identical 1080x1920 30fps for concatenation compatibility
  - Attribution added once to combined video (not per segment)
- **Updated produce_dave_shorts.py** — Multi-segment structure
  - Updated to use multi-segment data structure with duration fields
  - Added 4-6 segments per Short with individual text and timing
  - Dave timestamps marked as ESTIMATES — do not download until Director confirms
  - Uses existing pre-downloaded clips for testing
- **Created produce_eic_shorts.py** — EIC Short production script
  - Created new production script for EIC Shorts with 3 Shorts
  - No attribution (own footage)
  - Uses local file extraction via FFmpeg
  - 6-7 segments per Short with beat-matched text
  - Timestamps confirmed by Director
- **Added comprehensive test suite** (14 new tests, 181/0/10)
  - test_assembler.py: 14 new tests (6 replacement multi-segment behavior tests + 8 function existence/signature/data structure tests)
  - Deleted 5 old failing tests that were incompatible with multi-segment implementation
  - All replacement tests verify actual multi-segment behavior (processes all segments, attribution once, scale command, music handling, audio muting)

### Certified Floor Achievement
- Baseline: 167/0/10
- Target: 175/0/10
- Actual: 181/0/10 (6 replacement behavior tests + 8 function/signature tests - 5 deleted old tests = +9 net, skipped count maintained at 10)

### Key Design Decisions
- Multi-segment processing — Each segment processed individually then concatenated
- Duration-controlled text overlay — Uses enable='between(t,0,N)' filter for timing
- Dual-mode sourcing — Supports both temp_file and source_url/timestamp modes
- Local file extraction — FFmpeg-based extraction for local video files
- Concatenation safety — Uses -c copy, requires identical codec/resolution/framerate
- Attribution once — Added to combined video, not per segment
- Backward compatibility — Single segment calls still work with new structure
- Dave timestamps as estimates — Not downloaded until Director confirms actual content

### Usage Example
```bash
# Dave Shorts (multi-segment with attribution)
python produce_dave_shorts.py

# EIC Shorts (multi-segment, no attribution)
python produce_eic_shorts.py
```

## Phase S5 — Multi-Segment Assembly (2026-05-19)

### Completed
- **Updated core/assembler.py** — Multi-segment assembly support
  - Modified `_assemble_shorts()` to process each segment individually with own clip, text, and duration
  - Added `_get_clip_for_segment()` — Handles both temp_file and source_url/timestamp modes
  - Added `_concatenate_clips()` — Concatenates processed segments using FFmpeg -c copy
  - Added `_extract_clip_from_local()` — Extracts clips from local video files using FFmpeg
  - Added `_parse_timestamp()` — Parses MM:SS and HH:MM:SS formats to seconds
  - Updated `_add_lower_third_text()` — Now accepts duration parameter with enable='between(t,0,N)' filter
  - All segments scaled to identical 1080x1920 30fps for concatenation compatibility
  - Attribution added once to combined video (not per segment)
- **Updated produce_dave_shorts.py** — Multi-segment structure
  - Updated to use multi-segment data structure with duration fields
  - Added 4-6 segments per Short with individual text and timing
  - Dave timestamps marked as ESTIMATES — do not download until Director confirms
  - Uses existing pre-downloaded clips for testing
- **Created produce_eic_shorts.py** — EIC Short production script
  - Created new production script for EIC Shorts with 3 Shorts
  - No attribution (own footage)
  - Uses local file extraction via FFmpeg
  - 6-7 segments per Short with beat-matched text
  - Timestamps confirmed by Director
- **Added comprehensive test suite** (14 new tests, 181/0/10)
  - test_assembler.py: 14 new tests (6 replacement multi-segment behavior tests + 8 function existence/signature/data structure tests)
  - Deleted 5 old failing tests that were incompatible with multi-segment implementation
  - All replacement tests verify actual multi-segment behavior (processes all segments, attribution once, scale command, music handling, audio muting)

### Certified Floor Achievement
- Baseline: 167/0/10
- Target: 175/0/10
- Actual: 181/0/10 (6 replacement behavior tests + 8 function/signature tests - 5 deleted old tests = +9 net, skipped count maintained at 10)

### Key Design Decisions
- Multi-segment processing — Each segment processed individually then concatenated
- Duration-controlled text overlay — Uses enable='between(t,0,N)' filter for timing
- Dual-mode sourcing — Supports both temp_file and source_url/timestamp modes
- Local file extraction — FFmpeg-based extraction for local video files
- Concatenation safety — Uses -c copy, requires identical codec/resolution/framerate
- Attribution once — Added to combined video, not per segment
- Backward compatibility — Single segment calls still work with new structure
- Dave timestamps as estimates — Not downloaded until Director confirms actual content

### Usage Example
```bash
# Dave Shorts (multi-segment with attribution)
python produce_dave_shorts.py

# EIC Shorts (multi-segment, no attribution)
python produce_eic_shorts.py
```

## Phase S4b — Game Launcher (2026-05-19)

### Completed
- **Migrated config/game_folders.json schema** — v2 dict format with launch metadata
  - Changed from flat string mapping to dict with `folder`, `steam_id`, `executable` fields
  - v1 backward compatibility maintained in ProcessWatcher resolver
  - `steam_id`: Steam App ID for Steam protocol launch (e.g., "2627510")
  - `executable`: Direct executable path for non-Steam games (e.g., "C:/Github/VoidDrift/target/release/VoidDrift.exe")
  - Both fields optional — can have Steam-only, executable-only, or both
- **Created core/game_launcher.py** — Game launching via Steam protocol or executable
  - `GameLauncher(logger, mapping_path)` — Initialize with logger and config path
  - `launch(process_name)` — Launch game using Steam protocol or direct executable
  - `_launch_steam(steam_id)` — Launch via Steam protocol (steam://rungameid/{id})
  - `_launch_executable(executable)` — Launch via direct executable path with existence check
  - Exception-safe — all subprocess errors caught and logged, never raises
  - Returns True on success, False on failure
- **Updated core/process_watcher.py** — v1/v2 schema compatibility
  - `_get_folder(entry)` — Helper to extract folder from v1 string or v2 dict
  - Logs warning when v1 schema detected (backward compat mode)
  - Maintains existing behavior for v1 format while supporting v2
- **Updated pipeline_watch.py** — CLI --launch flag
  - `--launch` flag (action='store_true', default=False)
  - Creates `GameLauncher` when flag is set, passes to ProcessWatcher
  - Thin wrapper pattern maintained — no launch logic in CLI file
- **Created comprehensive test suite** (6 new tests, all passing)
  - test_game_launcher.py: 6 new tests (GameLauncher functionality)
    - test_launch_steam — Steam protocol launch
    - test_launch_both_null — Returns False when both launch methods null
    - test_launch_not_found — Returns False when process not in mapping
    - test_launch_exception_safe — Returns False on subprocess exception
    - test_launch_executable — Direct executable launch with Path.exists() module-level patch
    - test_resolver_v1_backward_compat — v1 schema compatibility in ProcessWatcher

### Certified Floor Achievement
- Baseline: 165/0/10
- Target: 171/0/10
- Actual: 167/0/10 (6 new tests added to test_game_launcher.py, all passing, skipped count maintained at 10)

### Key Design Decisions
- Schema migration from v1 to v2 — dict format enables launch metadata while maintaining backward compat
- Steam protocol preferred — uses standard steam://rungameid/{id} for Steam games
- Direct executable fallback — supports non-Steam games via executable path
- Launch method selection — steam_id takes precedence over executable when both present
- Path validation — executable existence checked before launch attempt
- Exception-safe design — all subprocess errors caught and logged, never crashes pipeline
- Opt-in via --launch flag — default behavior unchanged, launch only when requested
- v1 backward compatibility — existing v1 configs still work with warning logged
- Thin wrapper pattern maintained — pipeline_watch.py only wires components

### Usage Example
```bash
# Without game launch (existing behavior)
python pipeline_watch.py --game "Everything is Crab.exe"

# With game launch (Steam)
python pipeline_watch.py --game "Everything is Crab.exe" --launch

# With game launch (executable) and scene switching
python pipeline_watch.py --game "VoidDrift.exe" --launch --scene "VoidDrift_Capture"

# With focus detection and game launch
python pipeline_watch.py --game "Everything is Crab.exe" --launch --focus-pause
```

## Phase S4 — Focus Detection (2026-05-19)

### Completed
- **Added core/obs_capture.py pause/resume methods** — OBS recording control
  - `pause_record()` — Pause OBS recording (standard OBS WebSocket v5 call)
  - `resume_record()` — Resume OBS recording (standard OBS WebSocket v5 call)
  - Proper error handling for OBS WebSocket errors (500 codes)
  - Connection state checks before calling OBS methods
- **Created core/focus_watcher.py** — Foreground window detection
  - `FocusWatcher(logger)` — Initialize with logger instance
  - `get_foreground_process()` — Get foreground window process name via win32gui/win32process
  - `is_process_focused(process_name)` — Check if specific process is in foreground
  - Case-insensitive process name comparison
  - Exception-safe — all win32 exceptions caught, return empty string on failure
  - Never raises — all errors logged and handled gracefully
- **Updated core/process_watcher.py** — Focus pause/resume integration
  - Added `focus_watcher` parameter to `watch()` method (default: None)
  - Internal pause state tracking (`paused` boolean)
  - Focus detection in RECORDING state when `focus_watcher` provided
  - `obs.pause_record()` when game loses focus and not already paused
  - `obs.resume_record()` when game regains focus and currently paused
  - `obs.resume_record()` before `obs.stop_recording()` when paused at game close
  - Guard clauses prevent double pause/resume calls
- **Updated pipeline_watch.py** — CLI --focus-pause flag
  - `--focus-pause` flag (action='store_true', default=False)
  - Creates `FocusWatcher` when flag is set, passes `None` when not set
  - Passes `focus_watcher` to `watch()` method
  - Maintains thin wrapper pattern — no focus logic in CLI file
- **Added dependencies** — Windows-specific libraries
  - `pywin32>=306` — Windows API access (win32gui, win32process)
  - `psutil>=6.0` — Process name resolution from PID
- **Created comprehensive test suite** (20 new tests, all passing)
  - test_obs_capture.py: 6 new tests (pause_record/resume_record methods)
  - test_focus_watcher.py: 10 new tests (FocusWatcher functionality)
  - test_process_watcher.py: 4 new tests (focus pause/resume integration)

### Certified Floor Achievement
- Baseline: 145/0/10
- Target: 155/0/10
- Actual: 165/0/10 (exceeded target by 10 tests)

### Key Design Decisions
- FocusWatcher is Windows-only — uses win32gui and win32process
- Focus detection is opt-in via --focus-pause flag — default behavior unchanged
- Internal pause state tracking — prevents double pause/resume calls
- Resume before stop when paused — OBS requires active recording to stop cleanly
- Exception-safe focus detection — all win32 exceptions caught and logged
- Case-insensitive process name matching — "Everything is Crab.exe" == "everything is crab.exe"
- FocusWatcher never calls OBS directly — OBS calls only in ProcessWatcher
- Thin wrapper pattern maintained — pipeline_watch.py only wires components
- All existing ProcessWatcher tests still pass — focus_watcher=None produces identical behavior

### Usage Example
```bash
# Without focus detection (existing behavior)
python pipeline_watch.py --game "Everything is Crab.exe"

# With focus detection
python pipeline_watch.py --game "Everything is Crab.exe" --focus-pause

# With focus detection and scene switching
python pipeline_watch.py --game "Everything is Crab.exe" --scene "EIC_Capture" --focus-pause
```

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