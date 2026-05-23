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
        current_line = segment["segment_text"]
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
        "voice_gap": yaml_config.get("voice_gap", 1.5),
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


def compute_voice_schedule(
    segments: List[Dict[str, Any]],
    tts_durations: List[float],
    voice_delay: float = 0.3,
    voice_gap: float = 1.5
) -> List[Optional[float]]:
    """
    Compute actual start times for voice clips respecting gap constraints.

    For each segment, calculates when its voice clip should actually start,
    considering both the per-segment delay and minimum gap between clips.
    Skips segments where the voice would be pushed past the segment's end time.

    Args:
        segments: List of segment dictionaries with 'duration' field.
        tts_durations: List of TTS clip durations (same length as segments).
        voice_delay: Delay after segment start before voice fires (default 0.3s).
        voice_gap: Minimum seconds between voice clip end and next start (default 1.5s).

    Returns:
        List of actual start times (float) or None if segment's voice is skipped.
    """
    schedule = []
    cumulative_time = 0.0
    previous_voice_end = -float('inf')  # No previous voice initially

    for i, (segment, tts_duration) in enumerate(zip(segments, tts_durations)):
        segment_start = cumulative_time
        segment_end = cumulative_time + segment.get('duration', 5.0)
        
        # Skip segments with no voice (tts_duration == 0.0)
        if tts_duration == 0.0:
            schedule.append(None)
            cumulative_time += segment.get('duration', 5.0)
            continue
        
        # Calculate earliest start based on segment timing
        earliest_start = segment_start + voice_delay
        
        # Calculate earliest start based on gap constraint
        gap_constrained_start = previous_voice_end + voice_gap if previous_voice_end != -float('inf') else earliest_start
        
        # Actual start is the maximum of both constraints
        actual_start = max(earliest_start, gap_constrained_start)
        
        # Check if voice would end past segment end
        voice_end = actual_start + tts_duration
        if voice_end > segment_end:
            # Skip this segment's voice
            schedule.append(None)
            previous_voice_end = previous_voice_end  # No change
        else:
            schedule.append(actual_start)
            previous_voice_end = voice_end
        
        cumulative_time += segment.get('duration', 5.0)
    
    return schedule


def estimate_tts_duration(text: str) -> float:
    """
    Estimate TTS duration based on word count.
    Rough approximation: ~0.5s per word.
    """
    word_count = len(text.split())
    return word_count * 0.5


def generate_all_voice_clips(
    beats: list[dict],
    voice_schedule: list[float | None],
    voice_name: str,
    temp_dir: Path
) -> dict[int, Path]:
    """
    Generate all TTS clips before assembly begins.
    Returns dict of segment_index -> voice_file_path.
    Only generates clips for segments where 
    voice_schedule[i] is not None and beat text is not empty.
    All files written to disk before function returns.
    No FFmpeg. No assembly. TTS only.
    """
    import subprocess
    import sys
    import logging
    logger = logging.getLogger(__name__)
    
    voice_paths = {}
    for i, beat in enumerate(beats):
        if voice_schedule[i] is None:
            continue
        text = beat.get("line", "")
        if not should_generate_voice(text):
            continue
        output_path = temp_dir / f"voice_{i}.mp3"
        logger.info(f"Generating TTS for segment {i}: '{text[:30]}'")
        subprocess.run(
            [sys.executable, "tts_worker.py", text, str(output_path), voice_name],
            check=True
        )
        logger.info(f"TTS generated for segment {i}")
        voice_paths[i] = output_path
    
    return voice_paths


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
    beats = yaml_config["beats"]
    stack_text = yaml_config.get("stack_text", False)
    max_visible_lines = yaml_config.get("max_visible_lines", 5)
    
    logger.info(f"Producing short: {name}")
    logger.info(f"Source: {source}")
    logger.info(f"Attribution: {attribution if attribution else 'None'}")
    logger.info(f"Beats: {len(beats)}")
    logger.info(f"Stack text: {stack_text}")
    
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
        segments = apply_text_stacking(segments, max_visible_lines)

    # Setup directories
    output_dir = Path("output/shorts")
    output_dir.mkdir(parents=True, exist_ok=True)

    temp_dir = Path("temp/shorts")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # PHASE 1: Estimate TTS durations for scheduling
    tts_durations = []
    if config.get("voice_enabled"):
        for beat in beats:
            text = beat.get("line", "")
            if should_generate_voice(text):
                duration = estimate_tts_duration(text)
                tts_durations.append(duration)
            else:
                tts_durations.append(0.0)
    else:
        tts_durations = [0.0] * len(beats)
    
    # Compute voice schedule with gap constraints
    voice_schedule = None
    print("DEBUG: About to start voice scheduling")
    try:
        print("DEBUG: In try block")
        print(f"DEBUG: voice_enabled={config.get('voice_enabled')}, tts_durations={tts_durations}")
        if config.get("voice_enabled") and any(d > 0 for d in tts_durations):
            print("DEBUG: Inside if condition")
            voice_delay = config.get("voice_delay", 0.3)
            voice_gap = config.get("voice_gap", 1.5)
            voice_schedule = compute_voice_schedule(segments, tts_durations, voice_delay, voice_gap)
            
            # Log schedule results
            for i, scheduled_start in enumerate(voice_schedule):
                if scheduled_start is not None:
                    logger.info(f"  Segment {i}: voice scheduled at {scheduled_start:.2f}s")
                else:
                    logger.info(f"  Segment {i}: voice skipped (gap constraint)")
            
            config["voice_schedule"] = voice_schedule
        else:
            # No voice scheduling needed
            voice_schedule = [None] * len(segments)
            config["voice_schedule"] = voice_schedule
        
        print("DEBUG: After voice scheduling, about to start PHASE 2")
    except Exception as e:
        print(f"ERROR in voice scheduling: {e}")
        import traceback
        traceback.print_exc()
        raise
    # PHASE 2: Generate all TTS clips in one pass (before assembly)
    voice_paths = {}
    print(f"DEBUG: voice_enabled={config.get('voice_enabled')}, voice_schedule={voice_schedule}")
    if config.get("voice_enabled") and voice_schedule:
        voice_name = config.get("voice_name", "David")
        logger.info(f"Voice enabled — generating TTS clips (voice: {voice_name})")
        voice_paths = generate_all_voice_clips(beats, voice_schedule, voice_name, temp_dir)
        logger.info(f"Generated {len(voice_paths)} voice clips")
    
    # Assign voice paths to segments
    for i, segment in enumerate(segments):
        if i in voice_paths:
            segment["voice_path"] = str(voice_paths[i])
        else:
            segment["voice_path"] = None
        segment["voice_start"] = voice_schedule[i] if voice_schedule else None

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
        for vp in voice_paths.values():
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
