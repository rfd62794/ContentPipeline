"""
Produce three Dave the Diver Shorts with multi-segment assembly and attribution layer.

Source: https://www.youtube.com/watch?v=LUTPCMkA7xQ (CohhCarnage Dave the Diver Episode 1)
Attribution: "Gameplay via: CohhCarnage"

⚠️ NOTE: Timestamps below are ESTIMATES based on typical Dave the Diver Episode 1 pacing.
Do NOT download clips from CohhCarnage until Director confirms timestamps.
Using existing pre-downloaded clips for now.

Three Shorts to produce:
1. The Stat (displacement wall)
2. The Diagram (loop chains)
3. The Reveal (loop colonization)
"""

import sys
import logging
from pathlib import Path
from core.assembler import assemble_video

sys.path.insert(0, str(Path(__file__).resolve().parent))

def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Starting Dave the Diver Shorts production")
    
    # Configuration (matching config.yaml values)
    config = {
        "shorts_music_path": "assets/music/background.mp3",
        "shorts_attribution_enabled": True,
        "shorts_attribution_y_pct": 0.05,
        "shorts_attribution_font_size": 30,
        "shorts_attribution_color": "white",
        "shorts_attribution_opacity": 0.85,
        "shorts_text_font": "monospace",
        "shorts_text_size": 48,
        "shorts_text_color": "white",
        "shorts_lower_third_height_pct": 0.25
    }
    
    # Attribution text
    attribution = "Gameplay via: CohhCarnage"
    
    # CohhCarnage source URL (for future use when timestamps confirmed)
    COHH_URL = "https://www.youtube.com/watch?v=LUTPCMkA7xQ"
    
    # Output directory
    output_dir = Path("output/dave_shorts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Temp directory for processing
    temp_dir = Path("temp/dave_shorts")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the three shorts with multi-segment structure
    # ⚠️ TIMESTAMPS ARE ESTIMATES — do not download until Director confirms
    
    # Short 1 — The Stat
    short_1_segments = [
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "08:00",
            "source_timestamp_end": "08:06",
            "duration": 6,
            "segment_text": "50% of players reached\nthe Sea People Village."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "08:06",
            "source_timestamp_end": "08:10",
            "duration": 4,
            "segment_text": "4% made it past it."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "08:10",
            "source_timestamp_end": "08:15",
            "duration": 5,
            "segment_text": "That's not a difficulty wall."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "08:15",
            "source_timestamp_end": "08:21",
            "duration": 6,
            "segment_text": "That's a displacement wall."
        },
    ]
    
    # Short 2 — The Diagram
    short_2_segments = [
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "05:00",
            "source_timestamp_end": "05:05",
            "duration": 5,
            "segment_text": "Dave's loop:\nA → B → C → seaweed farm"
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "05:05",
            "source_timestamp_end": "05:10",
            "duration": 5,
            "segment_text": "Each loop feeds forward.\nNever back."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "10:00",
            "source_timestamp_end": "10:06",
            "duration": 6,
            "segment_text": "Stardew's loop:\nA ↔ B ↔ C ↔ D"
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "10:06",
            "source_timestamp_end": "10:12",
            "duration": 6,
            "segment_text": "Everything feeds everything.\nNothing becomes optional."
        },
    ]
    
    # Short 3 — The Reveal
    short_3_segments = [
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "15:00",
            "source_timestamp_end": "15:06",
            "duration": 6,
            "segment_text": "Balatro is a literal\nplayable minigame in Dave."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "15:06",
            "source_timestamp_end": "15:11",
            "duration": 5,
            "segment_text": "Not a mental model.\nAn actual card game."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "15:11",
            "source_timestamp_end": "15:17",
            "duration": 6,
            "segment_text": "The host loop was\nalready exhausted."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "15:17",
            "source_timestamp_end": "15:23",
            "duration": 6,
            "segment_text": "The guest loop\ndidn't need to fight."
        },
        {
            "source_url": COHH_URL,
            "source_timestamp_start": "15:23",
            "source_timestamp_end": "15:28",
            "duration": 5,
            "segment_text": "That's loop colonization."
        },
    ]
    
    # For now, use existing pre-downloaded clips as temp_file
    # This allows testing multi-segment assembly without downloading from CohhCarnage
    # ⚠️ Remove temp_file entries when Director confirms timestamps for actual downloads
    existing_clips = {
        "short_1": "output/dave_shorts/clips/LUTPCMkA7xQ_598_632.mp4",
        "short_2": "output/dave_shorts/clips/LUTPCMkA7xQ_898_932.mp4",
        "short_3": "output/dave_shorts/clips/LUTPCMkA7xQ_1198_1232.mp4"
    }
    
    # Add temp_file to segments for testing (use same clip for all segments in each short)
    for segment in short_1_segments:
        segment["temp_file"] = existing_clips["short_1"]
    for segment in short_2_segments:
        segment["temp_file"] = existing_clips["short_2"]
    for segment in short_3_segments:
        segment["temp_file"] = existing_clips["short_3"]
    
    shorts_config = [
        {"name": "dave_short_1_stat", "segments": short_1_segments},
        {"name": "dave_short_2_diagram", "segments": short_2_segments},
        {"name": "dave_short_3_reveal", "segments": short_3_segments}
    ]
    
    # Assemble shorts with multi-segment structure
    for short_config in shorts_config:
        logger.info(f"Processing {short_config['name']}")
        
        segments = short_config["segments"]
        output_path = output_dir / f"{short_config['name']}.mp4"
        
        # Assemble as short with attribution (no voice audio in shorts mode)
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
    
    logger.info("Dave the Diver Shorts production complete")

if __name__ == "__main__":
    main()