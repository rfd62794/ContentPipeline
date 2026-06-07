"""
YAML-driven short production runner.

Replaces produce_eic_shorts.py and produce_dave_shorts.py with a single
config-driven approach. All short definitions live in shorts/ directory as YAML files.

Usage:
    python produce_short.py shorts/eic_short_1_evolution.yaml
    python produce_short.py shorts/dave_short_1_stat.yaml
"""

import sys
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.assembler import assemble_video

sys.path.insert(0, str(Path(__file__).resolve().parent))

def load_yaml_config(yaml_path: Path) -> Dict[str, Any]:
    """Load short configuration from YAML file."""
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def convert_beats_to_segments(beats: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    """
    Convert YAML beats to assembler segment format.
    
    Args:
        beats: List of beat objects from YAML
        source: Source video path or URL
    
    Returns:
        List of segment dictionaries for assembler
    """
    segments = []
    for beat in beats:
        segment = {
            "temp_file": source,
            "source_timestamp_start": beat["clip_start"],
            "source_timestamp_end": beat["clip_end"],
            "duration": beat["duration"],
            "segment_text": beat["line"]
        }
        segments.append(segment)
    return segments

def apply_text_stacking(segments: List[Dict[str, Any]], max_visible_lines: int = 5) -> List[Dict[str, Any]]:
    """
    Apply text stacking with sliding window to segments.
    
    Args:
        segments: Original segments with single-line text
        max_visible_lines: Maximum number of lines to show at once
    
    Returns:
        Segments with accumulated text (last N lines visible)
    """
    stacked_segments = []
    accumulated_lines = []
    
    for segment in segments:
        # Add current line to accumulated lines
        current_line = segment["segment_text"] or ""
        accumulated_lines.append(current_line)
        
        # Keep only last N lines (sliding window)
        if len(accumulated_lines) > max_visible_lines:
            accumulated_lines = accumulated_lines[-max_visible_lines:]
        
        # Create stacked text by joining with newlines
        stacked_text = "\n".join(accumulated_lines)
        
        # Create new segment with stacked text
        stacked_segment = segment.copy()
        stacked_segment["segment_text"] = stacked_text
        stacked_segments.append(stacked_segment)
    
    return stacked_segments

def build_config_from_yaml(yaml_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build assembler config from YAML configuration.
    
    Args:
        yaml_config: Loaded YAML configuration
    
    Returns:
        Config dictionary for assembler
    """
    config = {
        "shorts_music_path": yaml_config.get("music_path", "assets/music/Pixelated_Passion.mp3"),
        "shorts_music_start": yaml_config.get("music_start", 0),
        "music_volume": yaml_config.get("music_volume", 0.20),
        "voice_enabled": yaml_config.get("voice", False),
        "voice_volume": yaml_config.get("voice_volume", 0.50),
        "voice_name": yaml_config.get("voice_name", "David"),
        "voice_delay": yaml_config.get("voice_delay", 0.3),
        "shorts_attribution_enabled": yaml_config.get("attribution") is not None,
        "shorts_attribution_y_pct": 0.05,
        "shorts_attribution_font_size": 30,
        "shorts_attribution_color": "white",
        "shorts_attribution_opacity": 0.85,
        "shorts_text_font": "monospace",
        "shorts_text_size": 48,
        "shorts_text_color": "white",
        "shorts_lower_third_height_pct": 0.25
    }
    return config

# =============================================================================
# Pure Functions (Testable Without edge_tts or ffmpeg)
# =============================================================================

OUTRO_LINE = "Like and subscribe if you're enjoying the ride."
OUTRO_DURATION = 4


def _parse_timestamp(ts: str) -> float:
    """
    Parse a timestamp string (M:SS or H:MM:SS) into total seconds.

    Args:
        ts: Timestamp string e.g. "3:19" or "1:03:19".

    Returns:
        Total seconds as float.
    """
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(parts[0])


def _format_timestamp(seconds: float) -> str:
    """
    Format total seconds back into M:SS string.

    Args:
        seconds: Total seconds.

    Returns:
        Timestamp string e.g. "3:23".
    """
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def get_video_duration(source_path: str) -> Optional[float]:
    """
    Get video duration in seconds via ffprobe.

    Args:
        source_path: Path to video file.

    Returns:
        Duration in seconds, or None if ffprobe fails.
    """
    import subprocess
    from core.assembler import get_ffmpeg_path
    ffprobe = get_ffmpeg_path().replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", source_path],
            capture_output=True, text=True, timeout=15
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def build_outro_beat(
    beats: List[Dict[str, Any]],
    video_duration: Optional[float] = None,
    outro_duration: int = OUTRO_DURATION,
    outro_line: str = OUTRO_LINE,
) -> Optional[Dict[str, Any]]:
    """
    Build an outro beat derived from the last beat's clip_end.

    clip_start = last beat's clip_end
    clip_end   = clip_start + outro_duration, clamped to video_duration if known

    Args:
        beats: Beat list from YAML (must be non-empty).
        video_duration: Total video length in seconds for clamping. None = no clamp.
        outro_duration: Duration in seconds to extend past the last clip_end.
        outro_line: CTA text for the outro beat.

    Returns:
        Outro beat dict, or None if beats is empty.
    """
    if not beats:
        return None
    last_beat = beats[-1]
    clip_start_sec = _parse_timestamp(str(last_beat["clip_end"]))
    clip_end_sec = clip_start_sec + outro_duration
    if video_duration is not None:
        clip_end_sec = min(clip_end_sec, video_duration)
    return {
        "clip_start": _format_timestamp(clip_start_sec),
        "clip_end": _format_timestamp(clip_end_sec),
        "duration": int(clip_end_sec - clip_start_sec),
        "line": outro_line,
    }


def should_generate_voice(segment_text: Optional[str]) -> bool:
    """
    Return True if a voice clip should be generated for this segment's text.

    Args:
        segment_text: The text string for this segment (may be None or empty).

    Returns:
        True if text is a non-empty, non-whitespace string.
    """
    return bool(segment_text and segment_text.strip())


def build_voice_mix_filter(voice_volume: float, voice_delay: float = 0.3) -> str:
    """
    Build the ffmpeg filter_complex string for mixing voice into a silent video.

    Assumes input 0 is the video (no audio), input 1 is music, input 2 is voice.
    Music and voice are mixed together at their respective volumes.
    Voice is delayed by voice_delay seconds to create a double-hit effect (text first, then voice).

    Args:
        voice_volume: Voice track volume (0.0 to 1.0).
        voice_delay: Delay in seconds before voice starts (default 0.3).

    Returns:
        ffmpeg filter_complex string.
    """
    delay_ms = int(voice_delay * 1000)
    return f"[2:a]adelay={delay_ms}|{delay_ms},volume={voice_volume}[v];[1:a][v]amix=inputs=2:duration=shortest[audio]"


def generate_voice_clip(text: str, voice: str, output_path: Path) -> None:
    """
    Generate a TTS audio clip using Windows SAPI COM (pywin32) and save to output_path.

    Writes WAV via SAPI, then converts to MP3 via ffmpeg.
    Fully offline — no network required.

    Args:
        text: Text to synthesize.
        voice: SAPI voice description substring to match (e.g. "David", "Zira").
               If no match found, uses the system default voice.
        output_path: Destination path for the generated MP3.
    """
    import win32com.client
    import subprocess
    from core.assembler import get_ffmpeg_path

    wav_path = output_path.with_suffix(".wav")

    sapi = win32com.client.Dispatch("SAPI.SpVoice")

    # Select voice by matching description substring (case-insensitive)
    voices = sapi.GetVoices()
    for i in range(voices.Count):
        if voice.lower() in voices.Item(i).GetDescription().lower():
            sapi.Voice = voices.Item(i)
            break

    # Write to WAV file via SpFileStream
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    stream.Open(str(wav_path), 3)  # SSFMCreateForWrite = 3
    sapi.AudioOutputStream = stream
    sapi.Speak(text, 0)  # SVSFDefault — explicit synchronous mode
    stream.Close()

    # Convert WAV -> MP3 via ffmpeg
    subprocess.run(
        [get_ffmpeg_path(), "-y", "-i", str(wav_path), str(output_path)],
        capture_output=True, check=True
    )
    wav_path.unlink(missing_ok=True)


def produce_short_from_yaml(yaml_path: Path):
    """
    Produce a short from YAML configuration file.
    
    Args:
        yaml_path: Path to YAML configuration file
    """
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info(f"Loading short config: {yaml_path}")
    
    # Load YAML configuration
    yaml_config = load_yaml_config(yaml_path)
    
    # Extract configuration
    name = yaml_config["name"]
    source = yaml_config["source"]
    attribution = yaml_config.get("attribution")
    beats = list(yaml_config["beats"])
    stack_text = yaml_config.get("stack_text", False)
    max_visible_lines = yaml_config.get("max_visible_lines", 5)
    add_outro = yaml_config.get("add_outro", False)
    outro_clip = yaml_config.get("outro_clip", None)
    
    logger.info(f"Producing short: {name}")
    logger.info(f"Source: {source}")
    logger.info(f"Attribution: {attribution if attribution else 'None'}")
    logger.info(f"Beats: {len(beats)}")
    logger.info(f"Stack text: {stack_text}")
    logger.info(f"Add outro: {add_outro}")

    # Inject outro beat if requested
    if add_outro:
        if outro_clip:
            # Explicit override from YAML
            beats.append(outro_clip)
            logger.info(f"Outro injected from outro_clip override")
        else:
            # Auto-derive from last beat's clip_end
            if not source.startswith("http"):
                video_duration = get_video_duration(source)
            else:
                video_duration = None
            outro = build_outro_beat(beats, video_duration)
            if outro:
                beats.append(outro)
                logger.info(f"Outro injected: {outro['clip_start']} -> {outro['clip_end']} ({outro['duration']}s)")
            else:
                logger.warning("add_outro=true but no beats found — skipping outro")
    
    # Verify source exists (if local file)
    if not source.startswith("http"):
        source_path = Path(source)
        if not source_path.exists():
            logger.error(f"Source video not found: {source}")
            return
        logger.info(f"Source video verified: {source}")
    
    # Build assembler config
    config = build_config_from_yaml(yaml_config)
    
    # Convert beats to segments
    segments = convert_beats_to_segments(beats, source)
    
    # Apply text stacking if enabled
    if stack_text:
        logger.info(f"Applying text stacking (max {max_visible_lines} lines)")
        logger.info(f"Before stacking: {len(segments)} segments")
        segments = apply_text_stacking(segments, max_visible_lines)
        logger.info(f"After stacking: {len(segments)} segments")

    # Setup directories
    output_dir = Path("output/shorts")
    output_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = Path("temp/shorts")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Clear temp directory to prevent cached voice files from interfering
    for file in temp_dir.glob("*"):
        file.unlink()
    logger.info(f"Cleared temp directory: {temp_dir}")

    # Generate per-beat TTS voice clips if voice is enabled
    voice_clips_generated = []
    if config.get("voice_enabled"):
        voice_name = config.get("voice_name", "en-US-GuyNeural")
        logger.info(f"Voice enabled — generating TTS clips (voice: {voice_name})")
        for i, segment in enumerate(segments):
            raw_text = beats[i].get("line", "")
            if should_generate_voice(raw_text):
                voice_path = temp_dir / f"voice_{i}.mp3"
                logger.info(f"  Segment {i}: TTS '{raw_text[:40]}' -> {voice_path}")
                try:
                    generate_voice_clip(raw_text, voice_name, voice_path)
                    logger.info(f"  Segment {i}: TTS complete, file exists: {voice_path.exists()}")
                    segment["voice_path"] = str(voice_path)
                    voice_clips_generated.append(voice_path)
                except Exception as e:
                    logger.error(f"  Segment {i}: TTS failed: {e}")
                    segment["voice_path"] = None
            else:
                logger.info(f"  Segment {i}: Skipping (no text)")
                segment["voice_path"] = None
    else:
        logger.info("Voice disabled")

    # Output path
    output_path = output_dir / f"{name}.mp4"

    # Assemble short
    try:
        assemble_video(
            segments,
            None,  # Voice audio handled per-segment via segment["voice_path"]
            output_path,
            temp_dir,
            config,
            shorts_mode=True,
            attribution=attribution
        )
        logger.info(f"Assembled {name}.mp4")

        # Clean up temp voice clips
        for vp in voice_clips_generated:
            try:
                vp.unlink()
            except OSError:
                pass
        
        # Verify file size
        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            logger.info(f"File size: {size_kb:.2f} KB")
            if size_kb < 500:
                logger.warning(f"File size below 500 KB threshold: {size_kb:.2f} KB")
        else:
            logger.error(f"Output file not created: {output_path}")
            
    except Exception as e:
        logger.error(f"Failed to assemble {name}: {e}")
        raise
    
    logger.info(f"Short production complete: {output_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python produce_short.py <yaml_config_path>")
        print("Example: python produce_short.py shorts/eic_short_1_evolution.yaml")
        sys.exit(1)
    
    yaml_path = Path(sys.argv[1])
    if not yaml_path.exists():
        print(f"Error: YAML config not found: {yaml_path}")
        sys.exit(1)
    
    produce_short_from_yaml(yaml_path)

if __name__ == "__main__":
    main()
