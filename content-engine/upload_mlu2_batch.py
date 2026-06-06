#!/usr/bin/env python3
"""
Batch upload 4 MLU2 shorts to YouTube.
"""

import sys
import logging
from pathlib import Path
import json

from metadata_builder import load_short_yaml, load_meta_yaml, resolve_metadata, validate_metadata
from youtube_upload import get_authenticated_service, upload_video

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

SHORTS = [
    "mlu2_spacesuit_surprise",
    "mlu2_lava_surrounds",
    "mlu2_nine_planets_dlc",
    "mlu2_enemies_climb",
]

def upload_short(short_id: str) -> dict:
    """Upload a single short to YouTube."""
    result = {
        "short_id": short_id,
        "success": False,
        "video_id": None,
        "error": None
    }
    
    try:
        # Load YAMLs
        short_path = f"shorts/{short_id}.yaml"
        meta_path = f"shorts/{short_id}.meta.yaml"
        
        short = load_short_yaml(short_path)
        meta = load_meta_yaml(meta_path)
        
        # Resolve metadata
        metadata = resolve_metadata(short, meta, None)
        
        # Validate metadata
        errors = validate_metadata(metadata)
        if errors:
            result["error"] = f"Validation errors: {errors}"
            return result
        
        # Check video file exists
        video_path = f"output/shorts/{short_id}.mp4"
        if not Path(video_path).exists():
            result["error"] = f"Video file not found: {video_path}"
            return result
        
        # Authenticate YouTube
        upload_service = get_authenticated_service()
        
        if not upload_service:
            result["error"] = "YouTube authentication failed"
            return result
        
        # Upload video
        logger.info(f"Uploading: {video_path}")
        video_id = upload_video(upload_service, video_path, metadata)
        
        if video_id:
            logger.info(f"Upload successful: {video_id}")
            result["success"] = True
            result["video_id"] = video_id
        else:
            result["error"] = "Upload failed"
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error uploading {short_id}: {e}")
    
    return result

def main():
    results = []
    
    logger.info(f"Uploading {len(SHORTS)} MLU2 shorts")
    
    for short_id in SHORTS:
        logger.info(f"\n--- Processing: {short_id} ---")
        result = upload_short(short_id)
        results.append(result)
        
        if not result["success"]:
            logger.error(f"Failed to upload {short_id}: {result['error']}")
            logger.error("Stopping batch due to failure")
            break
    
    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    logger.info(f"\n=== Upload Summary ===")
    logger.info(f"Passed: {passed}/{len(results)}")
    logger.info(f"Failed: {failed}")
    
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        logger.info(f"  {status}: {r['short_id']}")
        if r["video_id"]:
            logger.info(f"    Video ID: {r['video_id']}")
        if r["error"]:
            logger.info(f"    Error: {r['error']}")
    
    # Save results
    with open("mlu2_upload_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
