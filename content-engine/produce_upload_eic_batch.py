#!/usr/bin/env python3
"""
Batch produce and upload 8 EIC shorts.
"""

import subprocess
import sys
import logging
from pathlib import Path
import json

from metadata_builder import load_short_yaml, load_meta_yaml, resolve_metadata, validate_metadata
from youtube_upload import get_authenticated_service, upload_video

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

SHORTS = [
    "eic_what_am_i",
    "eic_trunk_both_ends",
    "eic_very_snail",
    "eic_lethal_mushroom",
    "eic_absolute_mutant",
    "eic_weaker_more_damage",
    "eic_eating_charm",
    "eic_hide_in_hole",
]

def produce_short(short_id: str) -> bool:
    yaml_path = f"shorts/{short_id}.yaml"
    result = subprocess.run(
        [".venv/Scripts/python.exe", "produce_short.py", yaml_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error(f"Produce failed {short_id}: {result.stderr[-500:]}")
        return False
    output_path = Path(f"output/shorts/{short_id}.mp4")
    if not output_path.exists():
        logger.error(f"Output not found: {output_path}")
        return False
    logger.info(f"Produced: {short_id}")
    return True

def upload_short(short_id: str, upload_service) -> str:
    short = load_short_yaml(f"shorts/{short_id}.yaml")
    meta = load_meta_yaml(f"shorts/{short_id}.meta.yaml")
    metadata = resolve_metadata(short, meta, None)
    errors = validate_metadata(metadata)
    if errors:
        logger.error(f"Validation errors {short_id}: {errors}")
        return None
    video_id = upload_video(upload_service, f"output/shorts/{short_id}.mp4", metadata)
    return video_id

def main():
    results = []

    # Authenticate once
    upload_service = get_authenticated_service()
    if not upload_service:
        logger.error("YouTube authentication failed")
        return 1

    for short_id in SHORTS:
        logger.info(f"\n--- {short_id} ---")
        result = {"short_id": short_id, "produce": False, "upload": False, "video_id": None, "error": None}

        try:
            if not produce_short(short_id):
                result["error"] = "Produce failed"
                results.append(result)
                break

            result["produce"] = True

            video_id = upload_short(short_id, upload_service)
            if video_id:
                logger.info(f"Uploaded: {video_id}")
                result["upload"] = True
                result["video_id"] = video_id
            else:
                result["error"] = "Upload failed"
                results.append(result)
                break

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error {short_id}: {e}")
            results.append(result)
            break

        results.append(result)

    # Summary
    passed = sum(1 for r in results if r["upload"])
    failed = len(results) - passed
    logger.info(f"\n=== Summary ===")
    logger.info(f"Passed: {passed}/{len(results)}")
    for r in results:
        status = "PASS" if r["upload"] else "FAIL"
        logger.info(f"  {status}: {r['short_id']}")
        if r["video_id"]:
            logger.info(f"    Video ID: {r['video_id']}")
        if r["error"]:
            logger.info(f"    Error: {r['error']}")

    with open("eic_batch_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
