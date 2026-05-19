# GameReviewAgent SDD v1.0

**Version:** 1.0  
**Status:** Active  
**Date:** 2026-05-19  

## §1 Purpose

GameReviewAgent is a Video to YouTube pipeline. Given a game analysis observation — a named concept, a system breakdown, a builder's autopsy — it sources relevant gameplay clips, assembles a YouTube Short with lower third text analysis and background music, and publishes to YouTube. The pipeline runs on a local tower. No face, no voice, no live presence required.

## §2 Primary Loop

```
Observation (text)
    ↓
Script segmentation (P3b)
    ↓
Clip sourcing — yt-dlp (P4c / clip_sourcer.py)
    ↓
Assembly — shorts_mode 1080x1920 (P7)
    ↓
Review / approval
    ↓
YouTube publish (P9 — planned)
```

## §3 Production Paths

Two paths. Both use the same core infrastructure.

**Path A — Analysis (primary):**
- Input: text observation, YouTube clip timestamps
- Visual: sourced gameplay clips, muted
- Text: lower third, monospace, reading-speed timed
- Music: ambient background track at 0.25 volume
- Output: 1080x1920 MP4 → YouTube Shorts

**Path B — Own-game (secondary):**
- Input: running game, OBS capture
- Visual: OBS recording of own software
- Text: same lower third system
- Capture: obs_capture.py → screen_recorder.py
- Output: 1080x1920 MP4 → YouTube Shorts

## §4 Core Infrastructure

| Module | Purpose | Status |
|---|---|---|
| core/db.py | SQLite state | Complete |
| core/llm_client.py | OpenRouter adapter | Complete |
| core/logger.py | Stage logging | Complete |
| core/assembler.py | FFmpeg + shorts_mode | Complete |
| core/obs_capture.py | OBS WebSocket | Complete |
| core/screen_recorder.py | FFmpeg capture | Complete |
| core/clip_sourcer.py | yt-dlp sourcing | Needs extraction |
| core/model_router.py | Model routing | Complete |
| core/scanner.py | Repo scanning | Dormant |
| core/repo_assessor.py | Directive gen | Dormant |

## §5 Certified Floor

128/0/10 — Phase E1 complete.

## §6 Phase Map

| Phase | Name | Status |
|---|---|---|
| S1 | Shorts Mode Formalization | Complete |
| E1 | OpenAgent Legacy Extraction | Complete (dormant) |
| S2 | Dave Shorts Production Run | Next |
| S3 | YouTube Publish (P9) | Planned |
| S4 | Telegram Trigger Layer | Deferred |

## §7 Deferred

- Aider integration — separate project
- Telegram bot trigger — separate project
- Long-form AI voice path — P6 intact but inactive
- OpenAgent scanner/assessor — dormant, future use