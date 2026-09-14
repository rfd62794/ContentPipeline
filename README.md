# ContentPipeline (retired)

> **Retired and archived (13 September 2026).** ContentPipeline (developed
> locally as GameReviewAgent) has been replaced by its successor,
> **RFD_YT_Engine** ([project page](https://rfditservices.com/projects/rfd-yt-engine/)).
> This repository is read-only. Nothing here is maintained; use the engine.

## Where each capability went

Commands in the engine are run from the RFD_YT_Engine folder as
`uv run python -m pipeline.interface <command>`.

| GameReviewAgent | RFD_YT_Engine |
|---|---|
| `content-engine/produce_short.py`, `core/assembler.py` (beat YAML → Short, voice_delay, attribution, music_start/volume, voice_name, outro_clip) | `produce-short <yaml>` — `pipeline/interface/short_producer.py`, `pipeline/ingest/beat_yaml.py`, `pipeline/production/{voice,assembler}.py` |
| `overlay_voice_to_mp4.py` (re-voice a rendered MP4) | `voice-over <yaml> <video>` |
| `youtube_upload.py`, `metadata_builder.py` (publish from `.meta.yaml`) | `publish-short <name>` (dry run by default) — `pipeline/distribution/{video_resource,upload}.py` |
| `upload_session.py` | `upload-session <yaml>` (dry run by default) |
| `reweave_calendar.py` (re-date all private Shorts round-robin) | `redate-private-shorts` (preview by default) and MCP `redate_private_shorts` — `pipeline/scheduling/redate.py`; verified identical on the live channel |
| `pipeline_watch.py` (record while the game runs) | `watch --game X.exe --scene S` — `pipeline/capture/` |
| Transcription in `review_session.py` | `transcribe <video>` — `pipeline/ingest/transcription.py` |
| `mcp_server.py` (`content-pipeline` MCP server) | `rfd-yt-engine` MCP server (`pipeline/interface/mcp_server.py`): `get_channel_summary` → `get_channel_analytics`, `get_youtube_analytics` → `get_youtube_analytics`, `get_installed_games`, `get_game_metrics`, `get_sale_info` → `detect_sale` |
| `core/youtube_auth.py` | `infra/youtube.py` (one OAuth client) |
| `youtube_library.py`, `youtube_analytics.py` | `pipeline/catalog/{youtube_data,youtube_metrics}.py` |
| `steam_library.py`, `game_metrics.py` | `pipeline/catalog/{steam_data,game_metrics}.py` |
| `core/obs_manager.py` | `infra/obs.py` |
| `content-engine/overlays/*.html` (OBS browser sources) | `overlays/`, served by `run_overlay_server.py` at `http://127.0.0.1:8765/<file>.html` |
| `content-engine/shorts/`, `sessions/`, `streams/`, `config/game_folders.json` | same folders in the engine |
| `content-engine/assets/music/` | `assets/music/` (copied, gitignored) |
| Local data: `game_registry.json`, `metrics_history.db`, `playtime_overrides.json`, `sessions/` transcripts, un-uploaded `output/shorts/*.mp4` | engine `data/gamereviewagent/` (gitignored) |

**Not carried over** (unused since May–June 2026 or superseded):
live commentary sessions (`live_session.py`), VLC review sessions
(`review_session.py`), the full stream launcher and MCP `start_stream`
(`stream_launcher.py`), yt-dlp clip sourcing (`core/clip_sourcer.py`,
`core/clip_orchestrator.py`), metrics history and MCP
`get_content_recommendations`, the P1–P7 AI long-form pipeline, and the
one-off batch/check/debug scripts. They remain in this repository's history.

## Portfolio notes

| | |
|---|---|
| **Status** | Retired into RFD_YT_Engine; archived |
| **Built** | April – September 2026 · 513 commits |
| **Size** | 139 Python files · 603 pytest test functions in 41 test files · ADRs in `content-engine/docs/adr/` |
| **Successor** | [RFD_YT_Engine](https://rfditservices.com/projects/rfd-yt-engine/) |

**What it demonstrates**
- Turning a manual creative chore into a pipeline: a YAML beat sheet plus footage becomes a finished YouTube Short with timed text overlays and music, assembled with FFmpeg.
- Automation around real tools: OBS WebSocket recording control with game-focus detection, and YouTube Data API clients for upload, channel library and analytics.
- Design decisions recorded as ADRs and backed by tests.

## License

MIT License

Copyright (c) 2026 Robert Dugger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
