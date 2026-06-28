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
    ], check=True, capture_output=True)
    print(f"Audio extracted to {wav_path}")


def detect_device() -> str:
    """Auto-detect if CUDA is available, default to CPU."""
    try:
        import torch
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            return "cuda"
    except (ImportError, AttributeError):
        pass
    return "cpu"


def main():
    parser = argparse.ArgumentParser(description="Transcribe video/audio file using Whisper")
    parser.add_argument("video_path", help="Path to video or audio file")
    parser.add_argument("--model", default="medium", choices=["base", "small", "medium", "large"],
                        help="Whisper model size (default: medium)")
    parser.add_argument("--device", choices=["cpu", "cuda"],
                        help="Device for Whisper (default: auto-detect)")
    args = parser.parse_args()

    # Validate video path exists
    if not os.path.exists(args.video_path):
        print(f"Error: File not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    # Auto-detect device if not specified
    device = args.device if args.device else detect_device()
    print(f"Using device: {device}")

    # Create temp WAV path
    wav_path = os.path.join(os.path.dirname(args.video_path), "temp_whisper.wav")

    # Create output file paths
    video_stem = Path(args.video_path).stem
    output_timestamped = os.path.join(os.path.dirname(args.video_path), f"{video_stem}_timestamps.txt")
    output_plain = os.path.join(os.path.dirname(args.video_path), f"{video_stem}_plain.txt")

    try:
        # Extract audio
        extract_audio(args.video_path, wav_path)

        # Transcribe with word timestamps enabled by default
        print(f"Transcribing with Whisper {args.model} model on {device}...")
        try:
            segments = transcribe(wav_path, args.model, device=device, word_timestamps=True)
        except Exception as e:
            print(f"Word timestamps failed, falling back to segment-level: {e}")
            segments = transcribe(wav_path, args.model, device=device, word_timestamps=False)

        # Write timestamped transcription (word-level)
        with open(output_timestamped, 'w', encoding='utf-8') as f:
            for seg in segments:
                if 'words' in seg:
                    for word in seg['words']:
                        f.write(f"[{word['start']:.2f}] {word['word']}\n")
                else:
                    # Fallback to segment-level if no word data
                    f.write(f"[{seg['start']:.2f}] {seg['text']}\n")
        print(f"Saved timestamped transcription to {output_timestamped}")

        # Write plain transcription
        with open(output_plain, 'w', encoding='utf-8') as f:
            for seg in segments:
                f.write(f"{seg['text']}\n")
        print(f"Saved plain transcription to {output_plain}")

        # Print preview
        print("\n" + "="*80)
        print("TRANSCRIPTION PREVIEW (first 10 segments)")
        print("="*80 + "\n")
        for seg in segments[:10]:
            print(f"[{seg['start']:.2f}] {seg['text']}")
        if len(segments) > 10:
            print(f"\n... ({len(segments) - 10} more segments)")

    finally:
        # Cleanup temp file
        if os.path.exists(wav_path):
            os.remove(wav_path)
            print(f"\nCleaned up {wav_path}")


if __name__ == "__main__":
    main()
