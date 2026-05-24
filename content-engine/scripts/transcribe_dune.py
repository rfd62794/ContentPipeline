#!/usr/bin/env python3
"""
Transcribe video/audio file using Whisper with GPU acceleration.

Usage:
    python scripts/transcribe_dune.py <video_path> [--model medium] [--device cuda]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from review_session import transcribe


def extract_audio(video_path: str, wav_path: str) -> None:
    """Extract audio from video file using FFmpeg."""
    print(f"Extracting audio from {video_path}...")
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        wav_path
    ], check=True)
    print(f"Audio extracted to {wav_path}")


def main():
    parser = argparse.ArgumentParser(description="Transcribe video/audio file using Whisper")
    parser.add_argument("video_path", help="Path to video or audio file")
    parser.add_argument("--model", default="medium", choices=["base", "small", "medium", "large"],
                        help="Whisper model size (default: medium)")
    parser.add_argument("--device", default="cuda", choices=["cpu", "cuda"],
                        help="Device for Whisper (default: cuda)")
    args = parser.parse_args()

    # Validate video path exists
    if not os.path.exists(args.video_path):
        print(f"Error: File not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    # Create temp WAV path
    wav_path = os.path.join(os.path.dirname(args.video_path), "temp_whisper.wav")

    try:
        # Extract audio
        extract_audio(args.video_path, wav_path)

        # Transcribe
        print(f"Transcribing with Whisper {args.model} model on {args.device}...")
        segments = transcribe(wav_path, args.model, device=args.device)

        # Output timestamped transcription
        print("\n" + "="*80)
        print("TRANSCRIPTION")
        print("="*80 + "\n")
        for seg in segments:
            print(f"[{seg['start']:.2f}] {seg['text']}")

    finally:
        # Cleanup temp file
        if os.path.exists(wav_path):
            os.remove(wav_path)
            print(f"\nCleaned up {wav_path}")


if __name__ == "__main__":
    main()
