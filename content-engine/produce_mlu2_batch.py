#!/usr/bin/env python3
"""
Batch produce 4 MLU2 shorts with Zira VO.
"""

import subprocess
import sys
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

SHORTS = [
    "mlu2_spacesuit_surprise",
    "mlu2_lava_surrounds",
    "mlu2_nine_planets_dlc",
    "mlu2_enemies_climb",
]

def produce_short(short_id: str) -> bool:
    """Produce a single short."""
    yaml_path = f"shorts/{short_id}.yaml"
    
    logger.info(f"Producing: {short_id}")
    
    result = subprocess.run(
        [".venv/Scripts/python.exe", "produce_short.py", yaml_path],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Failed to produce {short_id}: {result.stderr[-500:]}")
        return False
    
    # Verify output exists
    output_path = Path(f"output/shorts/{short_id}.mp4")
    if not output_path.exists():
        logger.error(f"Output file not found: {output_path}")
        return False
    
    logger.info(f"Success: {short_id}")
    return True

def main():
    results = []
    
    for short_id in SHORTS:
        success = produce_short(short_id)
        results.append({
            "short_id": short_id,
            "success": success
        })
        
        if not success:
            logger.error(f"Stopping batch due to failure: {short_id}")
            break
    
    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    logger.info(f"\n=== Batch Summary ===")
    logger.info(f"Passed: {passed}/{len(results)}")
    logger.info(f"Failed: {failed}")
    
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        logger.info(f"  {status}: {r['short_id']}")
    
    # Save results
    with open("mlu2_batch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
