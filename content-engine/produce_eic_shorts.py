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
        "shorts_music_path": "assets/music/background.mp3",
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
            "source_timestamp_end": "0:30",
            "duration": 5,
            "segment_text": "You're prey."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:43",
            "source_timestamp_end": "0:44",
            "duration": 1,
            "segment_text": "You adapt."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:04",
            "source_timestamp_end": "1:10",
            "duration": 6,
            "segment_text": "Now you pursue."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:15",
            "source_timestamp_end": "1:27",
            "duration": 12,
            "segment_text": "One becomes two."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:29",
            "source_timestamp_end": "1:32",
            "duration": 3,
            "segment_text": "Same run."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:32",
            "source_timestamp_end": "1:36",
            "duration": 4,
            "segment_text": "The loop reversed you."
        },
    ]
    
    # Short 3 — The Decision Density Problem
    short_3_segments = [
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:10",
            "source_timestamp_end": "0:20",
            "duration": 10,
            "segment_text": "Decision one."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:33",
            "source_timestamp_end": "0:35",
            "duration": 2,
            "segment_text": "Decision two."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "0:55",
            "source_timestamp_end": "0:56",
            "duration": 1,
            "segment_text": "Decision three."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:37",
            "source_timestamp_end": "1:44",
            "duration": 7,
            "segment_text": "Decision four."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:44",
            "source_timestamp_end": "1:48",
            "duration": 4,
            "segment_text": "90 seconds."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:48",
            "source_timestamp_end": "1:52",
            "duration": 4,
            "segment_text": "This is why run one hooks you."
        },
        {
            "temp_file": EIC_VIDEO,
            "source_timestamp_start": "1:52",
            "source_timestamp_end": "1:58",
            "duration": 6,
            "segment_text": "Run ten feels thinner."
        },
    ]
    
    shorts_config = [
        {"name": "eic_short_1_evolution", "segments": short_1_segments},
        {"name": "eic_short_2_predator", "segments": short_2_segments},
        {"name": "eic_short_3_decisions", "segments": short_3_segments}
    ]
    
    # Assemble shorts with multi-segment structure
    for short_config in shorts_config:
        logger.info(f"Processing {short_config['name']}")
        
        segments = short_config["segments"]
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
            
            # Verify file size
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                logger.info(f"File size: {size_kb:.2f} KB")
                if size_kb < 500:
                    logger.warning(f"File size below 500 KB threshold: {size_kb:.2f} KB")
            else:
                logger.error(f"Output file not created: {output_path}")
                
        except Exception as e:
            logger.error(f"Failed to assemble {short_config['name']}: {e}")
    
    logger.info("EIC Shorts production complete")

if __name__ == "__main__":
    main()