# ContentPipeline — Sprint Directive: OBSManager Refactor

*May 2026 | Read fully before executing anything.*

---

> ⛔ **STOP:** Run `uv run pytest` before touching any file.
> Must report **566 passed, 10 skipped, 3 deselected**.
> If count differs, stop and report — do not proceed.

---

## §0 Context

`core/obs_manager.py` is a 667-line monolithic `OBSManager` class covering
connection management, process launching, recording, streaming, scene switching,
and source management. This sprint splits it into four scoped classes with a
shared base.

**This sprint delivers:**
- `OBSManager` — connection base only (keep existing, strip non-connection methods)
- `OBSBoot` — OBS process launching
- `OBSCapture` — recording and streaming
- `OBSScenes` — scene management
- `OBSSources` — source management
- All four classes in `core/obs_manager.py` (single file, four classes)
- All import sites updated to use new classes

**This is pure refactoring. Zero new functionality.**

**Not in scope:**
- FFmpegManager (next sprint)
- Any new OBS features or methods
- Changes to `live_session.py` logic beyond import updates
- Changes to `stream_launcher.py` logic beyond import updates
- Changes to `pipeline_watch.py` logic beyond import updates

---

## §1 Scope Statement

| File | Status | Action |
|------|--------|--------|
| `core/obs_manager.py` | Modify | Split monolith into four classes + base |
| `content-engine/live_session.py` | Modify | Update imports and call sites |
| `content-engine/stream_launcher.py` | Modify | Update imports and call sites |
| `pipeline_watch.py` | Modify | Update imports and call sites |
| `content-engine/tests/test_obs_manager.py` | Modify | Update imports, add class-specific tests |

**Read-only — do not touch:**
`produce_short.py`, `core/assembler.py`, `stage_p7_assemble.py`, `sale_checker.py`,
`live_session.py` (logic only — imports may change), all files not listed above.

> ⚠️ RULE: Do not touch any file not listed in the scope table.
> If a bug is found in a read-only file, report it — do not fix it.

---

## §2 Implementation

### `core/obs_manager.py`

Split into five classes in this single file. Order in file:
1. `OBSManager` (base — connection only)
2. `OBSBoot`
3. `OBSCapture`
4. `OBSScenes`
5. `OBSSources`

Keep existing data classes `RecordingStatus` and `StreamStats` at the top of the file,
before any class definitions. Keep `build_obs_recording_path`, `format_recording_note`,
and `parse_stream_stats` module-level functions — do not move them.

---

#### `OBSManager` (connection base)

Retains only connection management. All recording/scene/source methods are removed
and live in their respective classes.

```python
class OBSManager:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = "") -> None
    def connect(self) -> bool
    def disconnect(self) -> None
    def is_connected(self) -> bool
    def __enter__(self) -> "OBSManager"
    def __exit__(self, *args) -> None
```

> ⚠️ RULE: `OBSManager` must contain zero recording, streaming, scene,
> or source methods after this refactor. Connection only.

---

#### `OBSBoot`

No OBSManager dependency. Process launching only.

```python
class OBSBoot:
    @staticmethod
    def ensure_obs_running(obs_exe_path: str) -> bool
```

> ⚠️ RULE: `OBSBoot` must not import or depend on `OBSManager`.
> It has no websocket connection — it manages the OS process only.

---

#### `OBSCapture`

Takes an `OBSManager` instance. Delegates all websocket calls through it.

```python
class OBSCapture:
    def __init__(self, obs: OBSManager) -> None
    def start_recording(self) -> bool
    def stop_recording(self) -> Optional[str]
    def pause_recording(self) -> bool
    def resume_recording(self) -> bool
    def is_recording(self) -> bool
    def get_recording_status(self) -> Optional[RecordingStatus]
    def start_stream(self) -> bool
    def stop_stream(self) -> bool
    def get_stream_stats(self) -> Optional[StreamStats]
```

> ⚠️ RULE: `OBSCapture` must not call `obsws_python` directly.
> All websocket access goes through the `OBSManager` instance passed at init.

---

#### `OBSScenes`

Takes an `OBSManager` instance.

```python
class OBSScenes:
    def __init__(self, obs: OBSManager) -> None
    def switch_scene(self, scene_name: str) -> bool
    def list_scenes(self) -> List[str]
```

> ⚠️ RULE: Same constraint as `OBSCapture` — no direct websocket calls.

---

#### `OBSSources`

Takes an `OBSManager` instance.

```python
class OBSSources:
    def __init__(self, obs: OBSManager) -> None
    def add_game_capture(self, scene_name: str, window_title: str, source_name: str) -> bool
    def remove_game_capture(self, scene_name: str, source_name: str) -> bool
    def mute_source(self, source_name: str) -> bool
    def unmute_source(self, source_name: str) -> bool
```

> ⚠️ RULE: Same constraint as `OBSCapture` — no direct websocket calls.

---

### Import site updates

All three caller files follow the same pattern. Update imports only —
do not change any logic, method calls, or control flow.

**`content-engine/live_session.py`**
```python
# Before
from core.obs_manager import OBSManager, build_obs_recording_path, format_recording_note

# After
from core.obs_manager import (
    OBSManager, OBSBoot, OBSCapture, OBSScenes, OBSSources,
    build_obs_recording_path, format_recording_note
)
```

Update every call site to use the appropriate class. Example pattern:
```python
obs = OBSManager()
capture = OBSCapture(obs)
scenes = OBSScenes(obs)
# capture.start_recording() instead of obs.start_recording()
```

> ⚠️ RULE: Do not restructure logic in caller files. One-to-one replacement
> of method calls only. If a caller does `obs.start_recording()`,
> it becomes `capture.start_recording()` with a `capture = OBSCapture(obs)`
> line added. Nothing else changes.

**`content-engine/stream_launcher.py`** — same pattern as above.

**`pipeline_watch.py`** — same pattern as above.

---

### `content-engine/tests/test_obs_manager.py`

Update imports to match new class structure. Add at minimum one test per new class
confirming the class instantiates and its methods exist. All existing tests must
continue to pass — do not delete any existing test.

> ⚠️ RULE: Mock all websocket calls. No real OBS connection during tests.
> Tests must pass with OBS not running.

---

## §3 Test Anchors

| Test name | Target | Behaviour |
|-----------|--------|-----------|
| `test_obs_boot_instantiates` | `OBSBoot` | Class exists, `ensure_obs_running` is callable |
| `test_obs_capture_instantiates` | `OBSCapture` | Takes mock OBSManager, all methods callable |
| `test_obs_scenes_instantiates` | `OBSScenes` | Takes mock OBSManager, all methods callable |
| `test_obs_sources_instantiates` | `OBSSources` | Takes mock OBSManager, all methods callable |
| `test_obs_manager_has_no_recording_methods` | `OBSManager` | `hasattr(obs, 'start_recording')` is False |
| `test_obs_manager_connection_methods_present` | `OBSManager` | connect, disconnect, is_connected all present |
| All existing tests | `test_obs_manager.py` | Must continue to pass unchanged |

**Target floor: 572+ passed, 0 failing, 10 skipped, 3 deselected**

(566 existing + minimum 6 new anchors)

---

## §4 Completion Criteria

- [ ] `uv run pytest` reports 572+ passed, 0 failing before marking complete
- [ ] `core/obs_manager.py` contains exactly five classes: `OBSManager`, `OBSBoot`, `OBSCapture`, `OBSScenes`, `OBSSources`
- [ ] `OBSManager` contains zero recording, streaming, scene, or source methods
- [ ] `OBSBoot` has zero dependency on `OBSManager`
- [ ] `OBSCapture`, `OBSScenes`, `OBSSources` each receive `OBSManager` at init
- [ ] All three import sites updated and functional
- [ ] No logic changes in any caller file — imports and call sites only
- [ ] All existing tests pass without modification
- [ ] No files outside the scope table were touched
- [ ] Agent provides raw `uv run pytest` terminal output as proof — summaries not accepted

---

## §5 Quick Reference

| Key | Value |
|-----|-------|
| Pre-flight floor | 566 passed, 10 skipped, 3 deselected |
| Target floor | 572+ passed, 0 failing |
| Run command | `cd C:/Github/GameReviewAgent && uv run pytest` |
| Primary file | `core/obs_manager.py` |
| Caller files | `live_session.py`, `stream_launcher.py`, `pipeline_watch.py` |
| Test file | `content-engine/tests/test_obs_manager.py` |
| New functionality | None — pure refactor |
| Module-level functions | Keep in place: `build_obs_recording_path`, `format_recording_note`, `parse_stream_stats` |
| Data classes | Keep in place: `RecordingStatus`, `StreamStats` |
| OBS WebSocket port | 4455, no password |
