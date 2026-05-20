"""
Produce three Dave the Diver Shorts with attribution layer.

Source: https://www.youtube.com/watch?v=LUTPCMkA7xQ (CohhCarnage Dave the Diver Episode 1)
Attribution: "Gameplay via: CohhCarnage"

Three Shorts to produce:
1. Stat (displacement wall)
2. Diagram (loop chains)
3. Reveal (loop colonization)
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
    
    # Output directory
    output_dir = Path("output/dave_shorts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Temp directory for processing (separate from output to avoid path duplication)
    temp_dir = Path("temp/dave_shorts")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the three shorts with timestamps (these would need to be determined from the video)
    # For now, using placeholder timestamps - these would need to be adjusted based on actual content
    shorts = [
        {
            "name": "dave_short_1_stat",
            "start": "10:00",
            "end": "10:30",
            "segment_text": "Dave the Diver: Displacement mechanics"
        },
        {
            "name": "dave_short_2_diagram",
            "start": "15:00",
            "end": "15:30",
            "segment_text": "Dave the Diver: Loop chains explained"
        },
        {
            "name": "dave_short_3_reveal",
            "start": "20:00",
            "end": "20:30",
            "segment_text": "Dave the Diver: Loop colonization reveal"
        }
    ]
    
    # Use existing downloaded clips
    existing_clips = {
        "dave_short_1_stat": "output/dave_shorts/clips/LUTPCMkA7xQ_598_632.mp4",
        "dave_short_2_diagram": "output/dave_shorts/clips/LUTPCMkA7xQ_898_932.mp4",
        "dave_short_3_reveal": "output/dave_shorts/clips/LUTPCMkA7xQ_1198_1232.mp4"
    }
    
    # Assemble shorts from existing clips
    for short in shorts:
        logger.info(f"Processing {short['name']}")
        
        # Use existing clip
        clip_path = existing_clips.get(short['name'])
        if not clip_path or not Path(clip_path).exists():
            logger.error(f"Clip not found for {short['name']}: {clip_path}")
            continue
        
        logger.info(f"Using existing clip: {clip_path}")
        
        # Create segment for assembler (use absolute path)
        segments = [{
            "temp_file": str(Path(clip_path).resolve()),
            "segment_text": short["segment_text"]
        }]
        
        # Output path
        output_path = output_dir / f"{short['name']}.mp4"
        
        # Use a dummy audio path (since we're not using voice audio in shorts mode)
        audio_path = temp_dir / "dummy_audio.mp3"
        audio_path.touch()
        
        # Assemble as short with attribution
        try:
            assemble_video(
                segments,
                audio_path,
                output_path,
                temp_dir,
                config,
                shorts_mode=True,
                attribution=attribution
            )
            logger.info(f"Assembled {short['name']}.mp4")
            
            # Verify file size
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                logger.info(f"File size: {size_kb:.2f} KB")
                if size_kb < 500:
                    logger.warning(f"File size below 500 KB threshold: {size_kb:.2f} KB")
            else:
                logger.error(f"Output file not created: {output_path}")
                
        except Exception as e:
            logger.error(f"Failed to assemble {short['name']}: {e}")
    
    logger.info("Dave the Diver Shorts production complete")

if __name__ == "__main__":
    main()