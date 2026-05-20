import re
import subprocess
import json
import math
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import whisper
except ImportError:
    whisper = None

logger = logging.getLogger(__name__)


def sanitize_drawtext(text: str) -> str:
    """Escape characters that break FFmpeg filter syntax on Windows."""
    if not text:
        return ""
    # Escape backslashes first to prevent double-escaping
    text = text.replace("\\", "\\\\")
    # Escape single quotes (since we use single quotes around the text)
    text = text.replace("'", "'\\''")
    # Escape special FFmpeg filter characters
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    return text
    text = text.replace("\\", "/")
    return text


def get_ffmpeg_path() -> str:
    """Return the path to the verified local ffmpeg.exe if present, else fallback to 'ffmpeg'."""
    local_bin = Path(__file__).resolve().parent.parent / "ffmpeg.exe"
    if local_bin.exists():
        return str(local_bin)
    return "ffmpeg"


def generate_srt(audio_path: Path, output_srt_path: Path):
    """
    Generate an SRT file using Whisper transcription with word-level timestamps.
    """
    if not whisper:
        print("  [WHISPER] Subtitle generation skipped: whisper not installed.")
        return None
        
    print(f"  [WHISPER] Transcribing {audio_path.name}...")
    model = whisper.load_model("base")
    result = model.transcribe(str(audio_path), word_timestamps=True, language="en")
    
    with open(output_srt_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(result["segments"], 1):
            start = _format_timestamp(segment["start"])
            end = _format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")
            
    print(f"      ✓ SRT generated: {output_srt_path.name}")
    return output_srt_path


def _format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS,mmm string."""
    td_h = int(seconds // 3600)
    td_m = int((seconds % 3600) // 60)
    td_s = int(seconds % 60)
    td_ms = int((seconds % 1) * 1000)
    return f"{td_h:02d}:{td_m:02d}:{td_s:02d},{td_ms:03d}"


def preprocess_segment(segment: Dict[str, Any], temp_dir: Path, config: Dict[str, Any]) -> Path | None:
    """
    Process an asset into a standardized 1920x1080 30fps MP4 segment.
    Supports Ken Burns cycling for multiple images.
    """
    idx = segment["segment_index"]
    duration = segment["estimated_duration_s"]
    drawtext_filter = segment.get("drawtext_string", "")
    
    # 1. Image Cycling Logic
    raw_paths = segment.get("image_paths")
    if raw_paths:
        try:
            image_paths = json.loads(raw_paths)
        except:
            image_paths = [segment["selected_asset"]]
    else:
        image_paths = [segment["selected_asset"]]
        
    interval = config.get("image_cycling_interval_s", 12)
    enabled = config.get("image_cycling_enabled", True)
    
    if not enabled:
        n_intervals = 1
        interval = duration
    else:
        n_intervals = max(1, math.ceil(duration / interval))
    
    print(f"  [ASSEMBLER seg {idx}] {n_intervals} intervals, {len(image_paths)} unique images")
    
    interval_clips = []
    for i in range(n_intervals):
        clip_duration = min(float(interval), float(duration) - i*interval)
        if clip_duration <= 0: break
        
        img_path = Path(image_paths[i % len(image_paths)])
        out_clip = temp_dir / f"seg_{idx}_part_{i}.mp4"
        
        # Ken Burns Params
        zoom_direction = "in" if i % 2 == 0 else "out"
        pan_x = ["-0.02", "0.02", "0", "-0.02"][i % 4]
        pan_y = ["0", "-0.02", "0.02", "0"][i % 4]
        
        # Zoom speed 0.0015 @ 30fps = ~1.5x zoom in 10s
        frames = int(clip_duration * 30)
        if zoom_direction == "in":
            lb = "min(zoom+0.0015,1.5)"
        else:
            lb = "if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))"

        # -------------------------------------------------------------
        # PASS 1: Visual Base (Zoompan for Images, Trim for Video)
        # -------------------------------------------------------------
        kb_tmp = temp_dir / f"seg_{idx}_part_{i}_kb.mp4"
        is_video = img_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm"]
        
        if is_video:
            # For video, just trim and scale
            # We use setpts=PTS-STARTPTS to ensure the trimmed clip starts at 0
            filt_v = f"scale=1920:1080,setpts=PTS-STARTPTS"
            cmd_kb = [
                get_ffmpeg_path(), "-y", "-i", str(img_path),
                "-vf", filt_v, "-t", str(clip_duration),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-an", str(kb_tmp)
            ]
        else:
            # For image, apply Ken Burns (Zoompan)
            filt_kb = (
                f"scale=1920:1080,zoompan=z='{lb}':d={frames}:"
                f"x='round(iw/2-(iw/zoom/2)+({pan_x}*iw))':y='round(ih/2-(ih/zoom/2)+({pan_y}*ih))':s=1920x1080"
            )
            cmd_kb = [
                get_ffmpeg_path(), "-y", "-framerate", "30", "-loop", "1", "-i", str(img_path),
                "-vf", filt_kb, "-t", str(clip_duration),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-an", str(kb_tmp)
            ]
        
        result_kb = subprocess.run(cmd_kb, capture_output=True, text=True)
        if result_kb.returncode != 0:
            logger.error(f"FFmpeg Pass 1 (KB) failed for seg {idx}: {result_kb.stderr[-500:]}")
            raise subprocess.CalledProcessError(result_kb.returncode, cmd_kb, output=result_kb.stdout, stderr=result_kb.stderr)
            
        # -------------------------------------------------------------
        # PASS 2: Drawtext / Box Overlay (Optional)
        # -------------------------------------------------------------
        # Only apply text to the FIRST interval of the segment (usually the hook)
        if drawtext_filter and i == 0:
            # Check if drawtext_filter is already a pre-built FFmpeg filter chain
            # (e.g., starts with 'drawtext' or 'drawbox')
            if "drawtext=" in drawtext_filter or "drawbox=" in drawtext_filter:
                # Use it as-is, but still apply sanitize_drawtext (which now handles smart-quotes)
                # except it shouldn't replace '=' if it's a filter.
                # Actually, if it's a filter, it was likely correctly escaped by the extractor.
                filt_text = drawtext_filter
            else:
                # It's raw text, apply the production Title Slide template using textfile approach
                textfile = temp_dir / f"seg_{idx}_interval_{i}_text.txt"
                with open(textfile, 'w', encoding='utf-8') as f:
                    f.write(drawtext_filter)
                
                # Convert to absolute path and escape special characters for FFmpeg
                textfile_abs = str(textfile.resolve()).replace("\\", "\\\\").replace(":", "\\:")
                
                filt_text = (
                    f"drawbox=y=ih*0.7:h=ih*0.2:color=black@0.6:t=fill,"
                    f"drawtext=textfile='{textfile_abs}':fontcolor=white:fontsize=64:"
                    f"x=(w-text_w)/2:y=ih*0.75+(ih*0.1-text_h)/2"
                )
            
            cmd_text = [
                get_ffmpeg_path(), "-y", "-i", str(kb_tmp),
                "-vf", filt_text,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-an", str(out_clip)
            ]
            
            result_text = subprocess.run(cmd_text, capture_output=True, text=True)
            
            # Clean up textfile if it was created
            if 'textfile' in locals() and textfile.exists():
                textfile.unlink()
            
            if result_text.returncode != 0:
                logger.error(f"FFmpeg Pass 2 (Text) failed for seg {idx}: {result_text.stderr[-500:]}")
                raise subprocess.CalledProcessError(result_text.returncode, cmd_text, output=result_text.stdout, stderr=result_text.stderr)
            
            # Cleanup intermediate
            if kb_tmp.exists(): kb_tmp.unlink()
        else:
            # No text, just move Pass 1 result
            shutil.move(str(kb_tmp), str(out_clip))
            
        interval_clips.append(out_clip)

    # Concatenate intervals
    final_seg = temp_dir / f"seg_{idx}.mp4"
    if len(interval_clips) == 1:
        shutil.move(str(interval_clips[0]), str(final_seg))
    else:
        concat_txt = temp_dir / f"seg_{idx}_concat.txt"
        with open(concat_txt, "w") as f:
            for c in interval_clips:
                f.write(f"file '{c.resolve()}'\n")
        result_concat = subprocess.run([
            get_ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c", "copy", str(final_seg)
        ], capture_output=True, text=True)
        if result_concat.returncode != 0:
            logger.error(f"FFmpeg Concat failed for seg {idx}: {result_concat.stderr[-500:]}")
            raise subprocess.CalledProcessError(result_concat.returncode, "ffmpeg_concat", output=result_concat.stdout, stderr=result_concat.stderr)
        
    return final_seg


import shutil

def assemble_video(segments: List[Dict[str, Any]], audio_path: Path, output_path: Path, temp_dir: Path, config: Dict[str, Any], shorts_mode: bool = False, attribution: str = None):
    """
    Concatenate preprocessed segments and mux with audio. Supports subtitles.
    
    When shorts_mode=True:
    - Output resolution: 1080x1920 (vertical)
    - Voice audio is bypassed
    - Attribution text overlay (top 20%) if provided
    - Text overlay: lower third with segment text
    - Background music: optional track at 0.25 volume
    
    Args:
        segments: List of segment dictionaries
        audio_path: Audio file path
        output_path: Output file path
        temp_dir: Temporary directory for processing
        config: Configuration dictionary
        shorts_mode: Enable shorts mode (vertical video)
        attribution: Optional attribution string for attribution overlay
    """
    # Shorts mode path
    if shorts_mode:
        return _assemble_shorts(segments, output_path, temp_dir, config, attribution)
    
    # Horizontal (long-form) path
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg['temp_file']}'\n")
            
    # Concatenate visuals
    visuals_only = temp_dir / "visuals_no_audio.mp4"
    result_vconcat = subprocess.run([
        get_ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(visuals_only)
    ], capture_output=True, text=True)
    if result_vconcat.returncode != 0:
        logger.error(f"FFmpeg Visual Concat failed: {result_vconcat.stderr[-500:]}")
        raise subprocess.CalledProcessError(result_vconcat.returncode, "ffmpeg_visual_concat", output=result_vconcat.stdout, stderr=result_vconcat.stderr)
    
    # Subtitles
    srt_path = None
    if config.get("subtitles_enabled"):
        srt_path = output_path.with_suffix(".srt")
        generate_srt(audio_path, srt_path)
    
    # Mux with audio + subtitles
    cmd = ["ffmpeg", "-y", "-i", str(visuals_only), "-i", str(audio_path)]
    
    vf = []
    sub_mode = config.get("subtitle_mode", "srt")
    if srt_path and srt_path.exists() and sub_mode in ["burn", "both"]:
        # Subtitles filter needs escaped path for Windows
        esc_path = str(srt_path).replace("\\", "/").replace(":", "\\:")
        vf.append(f"subtitles='{esc_path}'")
        
    if vf:
        cmd += ["-vf", ",".join(vf)]
        
    cmd += ["-c:v", "libx264", "-c:a", "aac", "-shortest", str(output_path)]
    
    result_mux = subprocess.run(cmd, capture_output=True, text=True)
    if result_mux.returncode != 0:
        logger.error(f"FFmpeg Mux failed: {result_mux.stderr[-500:]}")
        raise subprocess.CalledProcessError(result_mux.returncode, cmd, output=result_mux.stdout, stderr=result_mux.stderr)
    
    if srt_path and sub_mode not in ["srt", "both"]:
        srt_path.unlink()


def _assemble_shorts(segments: List[Dict[str, Any]], output_path: Path, temp_dir: Path, config: Dict[str, Any], attribution: str = None):
    """
    Assemble video in Shorts mode (vertical 1080x1920).
    
    - Muted gameplay clips as background
    - Attribution text overlay (top 20%) if provided
    - Lower third text overlay with segment text
    - Optional background music at 0.25 volume
    - No voice audio
    
    Args:
        segments: List of segment dictionaries
        output_path: Output file path
        temp_dir: Temporary directory for processing
        config: Configuration dictionary
        attribution: Optional attribution string (e.g., "Gameplay via: CohhCarnage")
    """
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg['temp_file']}'\n")
    
    # Concatenate visuals
    visuals_only = temp_dir / "visuals_no_audio.mp4"
    result_vconcat = subprocess.run([
        get_ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(visuals_only)
    ], capture_output=True, text=True)
    if result_vconcat.returncode != 0:
        logger.error(f"FFmpeg Visual Concat failed: {result_vconcat.stderr[-500:]}")
        raise subprocess.CalledProcessError(result_vconcat.returncode, "ffmpeg_visual_concat", output=result_vconcat.stdout, stderr=result_vconcat.stderr)
    
    # Scale to vertical resolution (1080x1920) and calculate clip position
    # For 1920x1080 source scaled to fit 1080 wide in 1920 tall frame:
    # Scaled clip height = 1080 * (1080/1920) = 607px
    # Clip starts at y = (1920 - 607) / 2 = 656px
    # Clip ends at y = 656 + 607 = 1263px
    # Space above clip: 0 to 656px → attribution centered here
    # Space below clip: 1263 to 1920px → analysis text centered here
    
    target_width = 1080
    target_height = 1920
    source_aspect = 1920 / 1080  # Assuming 16:9 source
    scaled_height = int(target_width / source_aspect)  # 607px
    clip_start_y = (target_height - scaled_height) // 2  # 656px
    clip_end_y = clip_start_y + scaled_height  # 1263px
    
    # Calculate text zone positions
    attribution_zone_center = clip_start_y // 2  # Center of space above clip
    analysis_zone_center = clip_end_y + (target_height - clip_end_y) // 2  # Center of space below clip
    
    vertical_visuals = temp_dir / "vertical_visuals.mp4"
    result_scale = subprocess.run([
        get_ffmpeg_path(), "-y", "-i", str(visuals_only),
        "-vf", f"scale={target_width}:{scaled_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:{clip_start_y}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-an", str(vertical_visuals)
    ], capture_output=True, text=True)
    if result_scale.returncode != 0:
        logger.error(f"FFmpeg Scale failed: {result_scale.stderr[-500:]}")
        raise subprocess.CalledProcessError(result_scale.returncode, "ffmpeg_scale", output=result_scale.stdout, stderr=result_scale.stderr)
    
    # Add attribution text overlay if provided (positioned above clip)
    attribution_visuals = vertical_visuals
    if attribution and config.get("shorts_attribution_enabled", False):
        attribution_visuals = temp_dir / "attribution_overlay.mp4"
        _add_attribution_text(vertical_visuals, attribution_visuals, attribution, config, attribution_zone_center)
    
    # Add lower third text overlay for each segment (positioned below clip)
    text_overlay = temp_dir / "text_overlay.mp4"
    _add_lower_third_text(attribution_visuals, text_overlay, segments, temp_dir, config, analysis_zone_center)
    
    # Add background music if configured
    music_path = config.get("shorts_music_path")
    if music_path and Path(music_path).exists():
        # Mix music at 0.25 volume
        music_input = Path(music_path)
        result_music = subprocess.run([
            get_ffmpeg_path(), "-y", "-i", str(text_overlay), "-i", str(music_input),
            "-filter_complex", "[1:a]volume=0.25[music];[0:a][music]amix=inputs=2:duration=first",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(output_path)
        ], capture_output=True, text=True)
        if result_music.returncode != 0:
            logger.error(f"FFmpeg Music Mix failed: {result_music.stderr[-500:]}")
            raise subprocess.CalledProcessError(result_music.returncode, "ffmpeg_music_mix", output=result_music.stdout, stderr=result_music.stderr)
    else:
        # No music, just copy the text overlay video
        shutil.copy(str(text_overlay), str(output_path))
        if music_path:
            logger.warning(f"Music file not found: {music_path}, assembling without music")


def _add_lower_third_text(input_video: Path, output_video: Path, segments: List[Dict[str, Any]], temp_dir: Path, config: Dict[str, Any], y_center: int):
    """Add lower third text overlay to video (positioned below gameplay clip)."""
    # Get text styling from config
    font = config.get("shorts_text_font", "monospace")
    font_size = config.get("shorts_text_size", 48)
    text_color = config.get("shorts_text_color", "white")
    
    # Use calculated center position for analysis text zone
    y_pos = y_center
    
    # Build drawtext filter for each segment
    # For simplicity, we'll add a single text overlay for the first segment
    if segments:
        segment_text = segments[0].get("segment_text", "")
        
        # Write segment text to a temporary file (FFmpeg textfile approach)
        textfile = output_video.parent / "segment_text.txt"
        with open(textfile, 'w', encoding='utf-8') as f:
            f.write(segment_text)
        
        # Convert to absolute path and escape special characters for FFmpeg
        textfile_abs = str(textfile.resolve()).replace("\\", "\\\\").replace(":", "\\:")
        
        # Build FFmpeg command with lower third text (no drawbox - text in letterboxed space)
        cmd = [
            get_ffmpeg_path(), "-y", "-i", str(input_video),
            "-vf", f"drawtext=textfile='{textfile_abs}':fontcolor={text_color}:fontsize={font_size}:"
                   f"x=(w-text_w)/2:y={y_pos}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-an", str(output_video)
        ]
        logger.info(f"FFmpeg Lower Third Command: {' '.join(cmd)}")
        result_text = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up textfile
        if textfile.exists():
            textfile.unlink()
        
        if result_text.returncode != 0:
            logger.error(f"FFmpeg Text Overlay failed: {result_text.stderr[-500:]}")
            raise subprocess.CalledProcessError(result_text.returncode, "ffmpeg_text_overlay", output=result_text.stdout, stderr=result_text.stderr)
    else:
        # No segments, just copy input
        shutil.copy(str(input_video), str(output_video))


def _add_attribution_text(input_video: Path, output_video: Path, attribution: str, config: Dict[str, Any], y_center: int):
    """Add attribution text overlay to video (positioned above gameplay clip)."""
    # Get attribution styling from config
    font = config.get("shorts_text_font", "monospace")
    font_size = config.get("shorts_attribution_font_size", 30)
    text_color = config.get("shorts_attribution_color", "white")
    opacity = config.get("shorts_attribution_opacity", 0.85)
    
    # Use calculated center position for attribution zone
    y_pos = y_center
    
    # Write attribution text to a temporary file (FFmpeg textfile approach)
    textfile = output_video.parent / "attribution_text.txt"
    with open(textfile, 'w', encoding='utf-8') as f:
        f.write(attribution)
    
    # Convert to absolute path and escape special characters for FFmpeg
    textfile_abs = str(textfile.resolve()).replace("\\", "\\\\").replace(":", "\\:")
    
    # Build FFmpeg command with textfile parameter
    cmd = [
        get_ffmpeg_path(), "-y", "-i", str(input_video),
        "-vf", f"drawtext=textfile='{textfile_abs}':fontcolor={text_color}:fontsize={font_size}:"
               f"x=(w-text_w)/2:y={y_pos}:alpha={opacity}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-an", str(output_video)
    ]
    logger.info(f"FFmpeg Attribution Command: {' '.join(cmd)}")
    result_text = subprocess.run(cmd, capture_output=True, text=True)
    
    # Clean up textfile
    if textfile.exists():
        textfile.unlink()
    
    if result_text.returncode != 0:
        logger.error(f"FFmpeg Attribution Overlay failed: {result_text.stderr[-500:]}")
        raise subprocess.CalledProcessError(result_text.returncode, "ffmpeg_attribution_overlay", output=result_text.stdout, stderr=result_text.stderr)
