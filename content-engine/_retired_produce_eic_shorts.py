"""
Produce three Everything Is Crab Shorts with multi-segment assembly.

Source: Local recording file (own footage, no attribution needed)

Three Shorts to produce:
1. The Evolution Loop Click
2. Predator Becomes Prey
3. The Decision Density Problem
"""

import sys
import logging
from pathlib import Path
from core.assembler import assemble_video

sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Starting EIC Shorts production")
    
    # Configuration (matching config.yaml values)
    config = {
        "shorts_music_path": "assets/music/Pixelated_Passion.mp3",
        "shorts_attribution_enabled": False,  # No attribution for own footage
        "shorts_attribution_y_pct": 0.05,
        "shorts_attribution_font_size": 30,
        "shorts_attribution_color": "white",
        "shorts_attribution_opacity": 0.85,
        "shorts_text_font": "monospace",
        "shorts_text_size": 48,
        "shorts_text_color": "white",
        "shorts_lower_third_height_pct": 0.25
    }
    
    # EIC video path (local file)
    EIC_VIDEO = "C:/Users/cheat/Videos/Everything Is Crab/2026-05-19 19-27-58.mp4"
    
    # Verify EIC video exists
    if not Path(EIC_VIDEO).exists():
        logger.error(f"EIC video not found: {EIC_VIDEO}")
        return
    
    logger.info(f"Using EIC video: {EIC_VIDEO}")
    
    # No attribution for own footage
    attribution = None
    
    # Output directory
    output_dir = Path("output/eic_shorts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Temp directory for processing
    temp_dir = Path("temp/eic_shorts")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the three shorts with multi-segment structure
    # Timestamps confirmed by Director
    
    # Short 1 — The Evolution Loop Click
    short_1_segments = [
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:33",
            "source_timestamp_end": "0:35",
            "duration": 2,
            "segment_text": "You feed."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:35",
            "source_timestamp_end": "0:38",
            "duration": 3,
            "segment_text": "You evolve."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:46",
            "source_timestamp_end": "0:51",
            "duration": 5,
            "segment_text": "You feed again."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:59",
            "source_timestamp_end": "1:02",
            "duration": 3,
            "segment_text": "You evolve deeper."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:02",
            "source_timestamp_end": "1:06",
            "duration": 4,
            "segment_text": "Most games give you stats."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:06",
            "source_timestamp_end": "1:10",
            "duration": 4,
            "segment_text": "This gives you a body."
        },
    ]
    
    # Short 2 — Predator Becomes Prey
    short_2_segments = [
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:25",
            "source_timestamp_end": "0:27",
            "duration": 2,
            "segment_text": "You're small."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:27",
            "source_timestamp_end": "0:30",
            "duration": 3,
            "segment_text": "You run."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:43",
            "source_timestamp_end": "0:44",
            "duration": 1,
            "segment_text": "Dash."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:44",
            "source_timestamp_end": "0:46",
            "duration": 2,
            "segment_text": "You survive."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:55",
            "source_timestamp_end": "0:56",
            "duration": 1,
            "segment_text": "You consume."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:04",
            "source_timestamp_end": "1:06",
            "duration": 2,
            "segment_text": "Same run."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:06",
            "source_timestamp_end": "1:10",
            "duration": 4,
            "segment_text": "Now you pursue."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:15",
            "source_timestamp_end": "1:18",
            "duration": 3,
            "segment_text": "One chases you."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:18",
            "source_timestamp_end": "1:22",
            "duration": 4,
            "segment_text": "You turn."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:22",
            "source_timestamp_end": "1:27",
            "duration": 5,
            "segment_text": "Two."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:29",
            "source_timestamp_end": "1:32",
            "duration": 3,
            "segment_text": "Dexterous."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:32",
            "source_timestamp_end": "1:38",
            "duration": 6,
            "segment_text": "The loop didn't upgrade you. It reversed you."
        },
    ]
    
    # Short 3 — Predator Fantasy (same content as YAML)
    short_3_segments = [
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:25",
            "source_timestamp_end": "0:27",
            "duration": 2,
            "segment_text": "You're small."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:27",
            "source_timestamp_end": "0:30",
            "duration": 3,
            "segment_text": "You run."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "2:51",
            "source_timestamp_end": "2:56",
            "duration": 5,
            "segment_text": "Chaos Tree."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "2:57",
            "source_timestamp_end": "2:59",
            "duration": 2,
            "segment_text": "+10% Size."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:00",
            "source_timestamp_end": "3:10",
            "duration": 7,
            "segment_text": "An enemy followed me to my food."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:10",
            "source_timestamp_end": "3:11",
            "duration": 1,
            "segment_text": "They died there."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:11",
            "source_timestamp_end": "3:15",
            "duration": 4,
            "segment_text": "Next one arrived."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:15",
            "source_timestamp_end": "3:18",
            "duration": 3,
            "segment_text": "I evolved."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:18",
            "source_timestamp_end": "3:21",
            "duration": 3,
            "segment_text": "They died immediately after."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:16",
            "source_timestamp_end": "3:29",
            "duration": 5,
            "segment_text": "Fur became Wool."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:30",
            "source_timestamp_end": "3:35",
            "duration": 5,
            "segment_text": "Night fell."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:36",
            "source_timestamp_end": "3:41",
            "duration": 5,
            "segment_text": "The last one didn't survive it."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:41",
            "source_timestamp_end": "3:52",
            "duration": 6,
            "segment_text": "By minute three,"
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "3:41",
            "source_timestamp_end": "3:52",
            "duration": 6,
            "segment_text": "killing was a side effect."
        },
    ]
    
    shorts_config = [
        # {"name": "eic_short_1_evolution", "segments": short_1_segments},  # Already produced
        # {"name": "eic_short_2_predator", "segments": short_2_segments},
        {"name": "eic_short_3_predator_fantasy", "segments": short_3_segments}  # Test Short 3 with retired script
    ]
    
    # Assemble shorts with multi-segment structure (one at a time for visual confirmation)
    for short_config in shorts_config:
        logger.info(f"Processing {short_config['name']}")
        
        segments = short_config["segments"]
        
        # Add stacking text accumulation with sliding window (last 5 lines)
        MAX_VISIBLE_LINES = 5
        accumulated_lines = []
        for segment in segments:
            accumulated_lines.append(segment["segment_text"])
            visible_lines = accumulated_lines[-MAX_VISIBLE_LINES:]
            segment["segment_text"] = "\n".join(visible_lines)
        
        output_path = output_dir / f"{short_config['name']}.mp4"
        
        # Assemble as short (no attribution for own footage)
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
            logger.info(f"Assembled {short_config['name']}.mp4")
            
            # Verify file size and get duration
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                logger.info(f"File size: {size_kb:.2f} KB")
                if size_kb < 500:
                    logger.warning(f"File size below 500 KB threshold: {size_kb:.2f} KB")
                
                # Get video duration using ffprobe
                try:
                    import subprocess
                    result = subprocess.run([
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)
                    ], capture_output=True, text=True)
                    if result.returncode == 0:
                        duration = float(result.stdout.strip())
                        logger.info(f"Duration: {duration:.2f} seconds")
                    else:
                        logger.warning(f"Could not get duration: ffprobe error")
                except Exception as e:
                    logger.warning(f"Could not get duration: {e}")
                    
                logger.info(f"Output file: {output_path}")
            else:
                logger.error(f"Output file not created: {output_path}")
                
        except Exception as e:
            logger.error(f"Failed to assemble {short_config['name']}: {e}")
    
    logger.info("EIC Shorts production complete")

if __name__ == "__main__":
    main()