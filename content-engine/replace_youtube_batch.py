#!/usr/bin/env python3
"""
Batch replace YouTube scheduled videos with regenerated Zira VO versions.
For each short: find existing scheduled video by title, delete it, upload replacement with same metadata.
"""

import sys
import logging
from pathlib import Path
import json

from metadata_builder import load_short_yaml, load_meta_yaml, resolve_metadata, validate_metadata, format_schedule
from youtube_upload import get_authenticated_service, upload_video, build_video_resource
from youtube_library import YouTubeLibrary

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# All 20 short IDs to replace
SHORT_IDS = [
    "mlu_auto_tool",
    "mlu_boss_cheese",
    "mlu_designers_math",
    "mlu_fishing_ddr",
    "mlu_hidden_orb",
    "mlu_map_opens",
    "mlu_mobile_vs_pc",
    "mlu_passive_game",
    "mlu_purple_wall",
    "mlu_respawn_timing",
    "duckov_headphones_regret",
    "duckov_tarkov_context",
    "raccoin_near_miss",
    "raccoin_second_tower",
    "raccoin_physics_observation",
    "raccoin_fishbone_discovery",
    "scritchy_scratchy_mundo_bankrupted",
    "scritchy_scratchy_582_million",
    "scritchy_scratchy_negative_ticket",
    "scritchy_scratchy_no_worms",
]

def replace_short(short_id: str) -> dict:
    """
    Replace a single scheduled video with regenerated version.
    
    Returns:
        Dict with success status, old_video_id, new_video_id, error message if any.
    """
    result = {
        "short_id": short_id,
        "success": False,
        "old_video_id": None,
        "new_video_id": None,
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
        
        # Authenticate YouTube (use upload scope for both operations)
        upload_service = get_authenticated_service()
        library = YouTubeLibrary()
        
        if not upload_service:
            result["error"] = "YouTube authentication failed"
            return result
        
        # Find existing video by title
        title = metadata.get('title', '')
        old_video_id = library.find_video_by_title(title)
        
        if old_video_id:
            logger.info(f"Found existing video: {old_video_id}")
            # Delete existing video using upload service (has correct scope)
            try:
                upload_service.videos().delete(id=old_video_id).execute()
                logger.info(f"Deleted old video: {old_video_id}")
                result["old_video_id"] = old_video_id
            except Exception as e:
                result["error"] = f"Failed to delete old video: {e}"
                return result
        else:
            logger.warning(f"No existing video found with title: {title}")
        
        # Upload new video
        logger.info(f"Uploading new video: {video_path}")
        new_video_id = upload_video(upload_service, video_path, metadata)
        
        if new_video_id:
            logger.info(f"Upload successful: {new_video_id}")
            result["success"] = True
            result["new_video_id"] = new_video_id
        else:
            result["error"] = "Upload failed"
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error replacing {short_id}: {e}")
    
    return result

def main():
    results = []
    
    logger.info("Starting YouTube replacement batch")
    logger.info(f"Processing {len(SHORT_IDS)} shorts")
    
    for short_id in SHORT_IDS:
        logger.info(f"\n--- Processing: {short_id} ---")
        result = replace_short(short_id)
        results.append(result)
        
        if not result["success"]:
            logger.error(f"Failed to replace {short_id}: {result['error']}")
            logger.error("Stopping batch due to failure")
            break
    
    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    logger.info(f"\n=== Replacement Summary ===")
    logger.info(f"Passed: {passed}/{len(results)}")
    logger.info(f"Failed: {failed}")
    
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        logger.info(f"  {status}: {r['short_id']}")
        if r["old_video_id"]:
            logger.info(f"    Old ID: {r['old_video_id']}")
        if r["new_video_id"]:
            logger.info(f"    New ID: {r['new_video_id']}")
        if r["error"]:
            logger.info(f"    Error: {r['error']}")
    
    # Save results to file
    with open("youtube_replacement_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
