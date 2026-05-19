"""
ContentEngine P7 — Visual Assembly Orchestration

Orchestrates FFmpeg to process all sourced assets (Ken Burns, scale, trim),
concatenates audio tracks, and multiplexes into the final MP4.
"""

import argparse
import sys
import subprocess
import shutil
import yaml
from pathlib import Path
from core.db import get_connection
from core.inventory_manager import increment_usage
from core.logger import Logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.assembler import preprocess_segment, assemble_video, get_ffmpeg_path

def main():
    logger = Logger()
    parser = argparse.ArgumentParser(description="ContentEngine P7 — Visual Assembly")
    parser.add_argument("--script_id", type=int, default=1, help="Script ID to assemble")
    parser.add_argument("--output_name", type=str, default=None, help="Base name for output files (e.g. video_2)")
    args = parser.parse_args()

    script_id = args.script_id
    output_base = args.output_name if args.output_name else f"video_{script_id}"

    logger.stage_start(f"P7 — FFmpeg Assembly (Script {script_id})")

    # Paths
    engine_root = Path(__file__).resolve().parent
    temp_dir = engine_root / "temp"
    output_dir = engine_root / "output"
    config_path = engine_root / "config.yaml"
    
    # Audio search paths
    audio_search_dirs = [
        engine_root / "audio",
        engine_root / "assets" / "audio",
        engine_root / "output"
    ]
    
    # Load config
    with open(config_path, "r", encoding="utf-8") as f:
        config_full = yaml.safe_load(f)
        config = config_full.get("assembly", {})
    
    # Check shorts mode
    shorts_mode = config.get("shorts_mode", False)

    # Cleanup temp
    if temp_dir.exists(): shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    cursor = conn.execute(
        "SELECT * FROM asset_briefs WHERE script_id = ? AND status = 'sourced' ORDER BY segment_index",
        (script_id,)
    )
    segments = cursor.fetchall()
    conn.close()

    if not segments:
        logger.stage_error("P7", f"No sourced segments found for Script ID {script_id}.")
        sys.exit(1)

    logger.info(f"Preprocessing {len(segments)} visual segments...")
    proc_segments = []
    
    for seg in segments:
        label = "HOOK" if seg["segment_index"] == 0 else f"BODY {seg['segment_index']}"
        logger.info(f"Processing {label} ({seg['estimated_duration_s']}s)")
        
        out_file = preprocess_segment(seg, temp_dir, config)
        if out_file:
            logger.info(f"Preprocessed: {out_file.name}")
            seg["temp_file"] = out_file
            proc_segments.append(seg)
        else:
            logger.stage_error("P7", f"Failed to preprocess segment {seg['segment_index']}")
            sys.exit(1)

    logger.info("Preparing audio track...")
    # Find hook + body audio
    hook_audio = None
    body_audio = None
    for ad in audio_search_dirs:
        h = ad / f"script_{script_id}_hook.mp3"
        b = ad / f"script_{script_id}_body.mp3"
        if h.exists(): hook_audio = h
        if b.exists(): body_audio = b
        
    if not hook_audio or not body_audio:
        logger.stage_error("P7", f"Audio files not found for Script {script_id}")
        sys.exit(1)
        
    full_audio = temp_dir / "full_audio.mp3"
    audio_concat = temp_dir / "audio_concat.txt"
    with open(audio_concat, "w") as f:
        f.write(f"file '{hook_audio.resolve()}'\n")
        f.write(f"file '{body_audio.resolve()}'\n")
        
    subprocess.run([
        get_ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat),
        "-c", "copy", str(full_audio)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    logger.info(f"Audio concatenated: {hook_audio.name} + {body_audio.name}")

    logger.info("Assembling final video...")
    output_video = output_dir / f"{output_base}.mp4"
    if shorts_mode:
        # Output to shorts subdirectory
        shorts_dir = output_dir / "shorts"
        shorts_dir.mkdir(parents=True, exist_ok=True)
        output_video = shorts_dir / f"{output_base}.mp4"
    
    assemble_video(proc_segments, full_audio, output_video, temp_dir, config, shorts_mode=shorts_mode)
    
    logger.info(f"Assembled: {output_video.name}")
    if (output_dir / f"{output_base}.srt").exists():
        logger.info(f"Subtitles: {output_base}.srt")
        
    # --- INVENTORY USAGE UPDATE ---
    logger.info("Updating inventory usage stats...")
    for seg in proc_segments:
        if seg.get("selected_asset"):
            increment_usage(seg["selected_asset"])
    logger.info("Usage stats updated")

    logger.stage_complete("P7", {"output": str(output_video)})

if __name__ == "__main__":
    main()
