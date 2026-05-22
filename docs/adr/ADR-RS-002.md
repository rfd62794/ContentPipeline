# ADR-RS-002: VLC over mpv or ffplay

## Status
Accepted

## Context
Three options for video playback subprocess: VLC, mpv, ffplay. VLC is universally installed on Windows developer machines and has a stable `--start-time` flag, `--no-loop`, and `--quiet` modes via CLI. mpv is lighter but not guaranteed present. ffplay lacks stable seek-on-open in all configurations.

## Decision
VLC. Binary path resolved at runtime: Windows default `C:\Program Files\VideoLAN\VLC\vlc.exe`, Linux/Mac `vlc`. If not found, tool exits with a clear error — no silent fallback.

## Consequences
VLC must be installed. Tool fails loudly if it isn't. No bundled player.
