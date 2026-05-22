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
from typing import Dict, Any, List
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
    logger.info(f"Attribution type: {type(attribution)}")
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
    
    # Output path
    output_path = output_dir / f"{name}.mp4"
    
    # Assemble short
    logger.info(f"YAML SEG 0: {segments[0]}")
    try:
        assemble_video(
            segments,
            None,  # Voice audio bypassed in shorts mode
            output_path,
            temp_dir,
            config,
            shorts_mode=True,
            attribution=attribution
        )
        logger.info(f"Assembled {name}.mp4")
        
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
