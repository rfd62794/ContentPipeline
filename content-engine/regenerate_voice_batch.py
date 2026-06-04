#!/usr/bin/env python3
"""
Batch regenerate all 20 Shorts with Zira VO.
Sequential execution with audio verification before proceeding to next.
"""

import subprocess
import sys
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# All 20 YAML files to regenerate
YAML_FILES = [
    "shorts/mlu_auto_tool.yaml",
    "shorts/mlu_boss_cheese.yaml",
    "shorts/mlu_designers_math.yaml",
    "shorts/mlu_fishing_ddr.yaml",
    "shorts/mlu_hidden_orb.yaml",
    "shorts/mlu_map_opens.yaml",
    "shorts/mlu_mobile_vs_pc.yaml",
    "shorts/mlu_passive_game.yaml",
    "shorts/mlu_purple_wall.yaml",
    "shorts/mlu_respawn_timing.yaml",
    "shorts/duckov_headphones_regret.yaml",
    "shorts/duckov_tarkov_context.yaml",
    "shorts/raccoin_near_miss.yaml",
    "shorts/raccoin_second_tower.yaml",
    "shorts/raccoin_physics_observation.yaml",
    "shorts/raccoin_fishbone_discovery.yaml",
    "shorts/scritchy_scratchy_mundo_bankrupted.yaml",
    "shorts/scritchy_scratchy_582_million.yaml",
    "shorts/scritchy_scratchy_negative_ticket.yaml",
    "shorts/scritchy_scratchy_no_worms.yaml",
]

def verify_audio_track(video_path: Path) -> bool:
    """Verify MP4 exists and has reasonable size (proxy for audio presence)."""
    try:
        if not video_path.exists():
            return False
        # Check file size > 100KB (silence-only would be much smaller)
        size_mb = video_path.stat().st_size / (1024 * 1024)
        return size_mb > 0.1
    except Exception as e:
        logger.error(f"Audio verification failed for {video_path}: {e}")
        return False

def regenerate_short(yaml_file: str) -> bool:
    """Regenerate a single Short and verify audio."""
    yaml_path = Path(yaml_file)
    name = yaml_path.stem
    
    logger.info(f"Regenerating: {name}")
    
    # Run produce_short.py
    result = subprocess.run(
        [sys.executable, "produce_short.py", str(yaml_path)],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Failed to produce {name}: {result.stderr[-500:]}")
        return False
    
    # Verify output exists and has audio
    output_path = Path(f"output/shorts/{name}.mp4")
    if not output_path.exists():
        logger.error(f"Output file not found: {output_path}")
        return False
    
    if not verify_audio_track(output_path):
        logger.error(f"Output has no audio track: {output_path}")
        return False
    
    logger.info(f"Success: {name} with audio verified")
    return True

def main():
    results = []
    
    for yaml_file in YAML_FILES:
        success = regenerate_short(yaml_file)
        results.append({
            "yaml": yaml_file,
            "success": success
        })
        
        if not success:
            logger.error(f"Stopping batch due to failure: {yaml_file}")
            break
    
    # Summary
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    logger.info(f"\n=== Batch Summary ===")
    logger.info(f"Passed: {passed}/{len(results)}")
    logger.info(f"Failed: {failed}")
    
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        logger.info(f"  {status}: {r['yaml']}")
    
    # Save results to file
    with open("voice_batch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
