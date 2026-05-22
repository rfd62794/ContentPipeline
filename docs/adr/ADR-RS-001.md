# ADR-RS-001: sounddevice over pyaudio

## Status
Accepted

## Context
Two Python mic recording options in common use on Windows: `sounddevice` and `pyaudio`. `pyaudio` requires a separate PortAudio DLL on Windows that frequently mismatches with Python version and causes silent failures. `sounddevice` wraps the same PortAudio but ships its own binary, handles device enumeration cleanly, and returns `numpy` arrays directly — which is already Whisper's expected input format.

## Decision
`sounddevice`. Add to `requirements.txt`. Record at 16 kHz mono float32 — Whisper's native sample rate. No resampling needed.

## Consequences
Adds `sounddevice` and `numpy` to requirements. Locks recording at 16kHz/mono. No stereo, no multi-device.
