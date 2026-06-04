#!/usr/bin/env python3
"""
Batch overlay voice onto Scritchy Scratchy MP4s and re-upload to YouTube.
"""

import sys
import logging
from pathlib import Path
import json

from overlay_voice_to_mp4 import overlay_voice_to_short
from metadata_builder import load_short_yaml, load_meta_yaml, resolve_metadata, validate_metadata
from youtube_upload import get_authenticated_service, upload_video

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Scritchy Scratchy shorts to process
SCRITCHY_SHORTS = [
    "scritchy_scratchy_mundo_bankrupted",
    "scritchy_scratchy_582_million",
    "scritchy_scratchy_negative_ticket",
    "scritchy_scratchy_no_worms",
]

def process_short(short_id: str) -> dict:
    """Overlay voice and upload to YouTube."""
    result = {
        "short_id": short_id,
        "overlay_success": False,
        "upload_success": False,
        "video_id": None,
        "error": None
    }
    
    try:
        yaml_path = f"shorts/{short_id}.yaml"
        input_mp4 = f"output/shorts/{short_id}.mp4"
        output_mp4 = f"output/shorts/{short_id}_voiced.mp4"
        
        # Overlay voice
        logger.info(f"Overlaying voice: {short_id}")
        overlay_success = overlay_voice_to_short(yaml_path, input_mp4, output_mp4)
        
        if not overlay_success:
            result["error"] = "Voice overlay failed"
            return result
        
        result["overlay_success"] = True
        logger.info(f"Voice overlay complete: {output_mp4}")
        
        # Load metadata
        meta_path = f"shorts/{short_id}.meta.yaml"
        short = load_short_yaml(yaml_path)
        meta = load_meta_yaml(meta_path)
        metadata = resolve_metadata(short, meta, None)
        
        # Validate metadata
        errors = validate_metadata(metadata)
        if errors:
            result["error"] = f"Validation errors: {errors}"
            return result
        
        # Upload to YouTube
        logger.info(f"Uploading to YouTube: {short_id}")
        upload_service = get_authenticated_service()
        
        if not upload_service:
            result["error"] = "YouTube authentication failed"
            return result
        
        video_id = upload_video(upload_service, output_mp4, metadata)
        
        if video_id:
            logger.info(f"Upload successful: {video_id}")
            result["upload_success"] = True
            result["video_id"] = video_id
            
            # Replace original MP4 with voiced version
            Path(input_mp4).unlink()
            Path(output_mp4).rename(input_mp4)
        else:
            result["error"] = "Upload failed"
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error processing {short_id}: {e}")
    
    return result

def main():
    results = []
    
    logger.info(f"Processing {len(SCRITCHY_SHORTS)} Scritchy Scratchy shorts")
    
    for short_id in SCRITCHY_SHORTS:
        logger.info(f"\n--- Processing: {short_id} ---")
        result = process_short(short_id)
        results.append(result)
        
        if not result["overlay_success"] or not result["upload_success"]:
            logger.error(f"Failed to process {short_id}: {result['error']}")
            logger.error("Stopping batch due to failure")
            break
    
    # Summary
    passed = sum(1 for r in results if r["overlay_success"] and r["upload_success"])
    failed = len(results) - passed
    
    logger.info(f"\n=== Batch Summary ===")
    logger.info(f"Passed: {passed}/{len(results)}")
    logger.info(f"Failed: {failed}")
    
    for r in results:
        status = "PASS" if r["overlay_success"] and r["upload_success"] else "FAIL"
        logger.info(f"  {status}: {r['short_id']}")
        if r["video_id"]:
            logger.info(f"    Video ID: {r['video_id']}")
        if r["error"]:
            logger.info(f"    Error: {r['error']}")
    
    # Save results
    with open("scritchy_overlay_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
