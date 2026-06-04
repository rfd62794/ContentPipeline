#!/usr/bin/env python3
"""
Post-production voice overlay for existing MP4 files.
Generates voice clips from YAML beats, mixes with music, and replaces audio track in MP4.
"""

import sys
import yaml
import logging
from pathlib import Path
import subprocess
import tempfile
import shutil

from core.assembler import get_ffmpeg_path

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# SAPI TTS generation (synchronous, from produce_short.py)
def generate_voice_clip(text: str, voice_name: str, output_path: Path) -> bool:
    """Generate voice clip using Windows SAPI COM via pywin32."""
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        
        # Find voice by name
        voices = speaker.GetVoices()
        selected_voice = None
        for voice in voices:
            if voice_name.lower() in voice.GetDescription().lower():
                selected_voice = voice
                break
        
        if selected_voice:
            speaker.Voice = selected_voice
        else:
            logger.warning(f"Voice '{voice_name}' not found, using default")
        
        # Generate WAV
        speaker.Speak(text, 0)  # 0 = synchronous
        
        # Use SAPI to save to WAV file
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Format.Type = 22  # 22 = 22kHz 16-bit mono PCM
        stream.Open(str(output_path.with_suffix('.wav')), 3)  # 3 = create
        speaker.AudioOutputStream = stream
        speaker.Speak(text, 0)
        stream.Close()
        
        # Convert WAV to MP3 using ffmpeg
        ffmpeg_path = get_ffmpeg_path()
        subprocess.run([
            ffmpeg_path, '-y',
            '-i', str(output_path.with_suffix('.wav')),
            '-codec:a', 'libmp3lame',
            '-ar', '44100',
            '-ac', '1',
            str(output_path)
        ], check=True, capture_output=True)
        
        # Clean up WAV
        output_path.with_suffix('.wav').unlink()
        
        return True
    except Exception as e:
        logger.error(f"Failed to generate voice clip: {e}")
        return False

def build_voice_track(beats: list, voice_name: str, voice_volume: float, temp_dir: Path) -> Path:
    """Generate and concatenate voice clips for all beats."""
    voice_clips = []
    
    for i, beat in enumerate(beats):
        text = beat.get('line', '')
        if not text:
            continue
        
        voice_clip_path = temp_dir / f"voice_{i}.mp3"
        if generate_voice_clip(text, voice_name, voice_clip_path):
            voice_clips.append(voice_clip_path)
    
    if not voice_clips:
        logger.warning("No voice clips generated")
        return None
    
    # Concatenate voice clips
    concat_file = temp_dir / "voice_concat.txt"
    with open(concat_file, 'w') as f:
        for clip in voice_clips:
            f.write(f"file '{clip.absolute().as_posix()}'\n")
    
    voice_track_path = temp_dir / "voice_track.mp3"
    ffmpeg_path = get_ffmpeg_path()
    subprocess.run([
        ffmpeg_path, '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-codec:a', 'libmp3lame',
        '-ar', '44100',
        '-ac', '1',
        str(voice_track_path)
    ], check=True, capture_output=True)
    
    return voice_track_path

def mix_audio_tracks(voice_track: Path, music_path: str, music_volume: float, voice_volume: float, temp_dir: Path) -> Path:
    """Mix voice and music into single audio track."""
    ffmpeg_path = get_ffmpeg_path()
    mixed_audio_path = temp_dir / "mixed_audio.mp3"
    
    if music_path and Path(music_path).exists():
        subprocess.run([
            ffmpeg_path, '-y',
            '-i', str(voice_track),
            '-i', music_path,
            '-filter_complex', f"[0:a]volume={voice_volume}[v];[1:a]volume={music_volume}[m];[v][m]amix=inputs=2:duration=first",
            '-codec:a', 'libmp3lame',
            '-ar', '44100',
            '-ac', '1',
            str(mixed_audio_path)
        ], check=True, capture_output=True)
    else:
        # Voice only
        shutil.copy(voice_track, mixed_audio_path)
    
    return mixed_audio_path

def overlay_audio_to_mp4(input_mp4: Path, mixed_audio: Path, output_mp4: Path) -> bool:
    """Replace audio track in MP4 with mixed audio."""
    ffmpeg_path = get_ffmpeg_path()
    
    try:
        subprocess.run([
            ffmpeg_path, '-y',
            '-i', str(input_mp4),
            '-i', str(mixed_audio),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            str(output_mp4)
        ], check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error(f"Failed to overlay audio: {e}")
        return False

def overlay_voice_to_short(yaml_path: str, input_mp4: str, output_mp4: str) -> bool:
    """Overlay voice and music onto existing MP4."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Load YAML
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        beats = config.get('beats', [])
        voice_name = config.get('voice_name', 'David')
        voice_volume = config.get('voice_volume', 0.50)
        music_path = config.get('music_path')
        music_volume = config.get('music_volume', 0.20)
        
        logger.info(f"Processing {len(beats)} beats with voice '{voice_name}'")
        
        # Build voice track
        voice_track = build_voice_track(beats, voice_name, voice_volume, temp_path)
        if not voice_track:
            logger.error("Failed to build voice track")
            return False
        
        # Mix audio
        mixed_audio = mix_audio_tracks(voice_track, music_path, music_volume, voice_volume, temp_path)
        
        # Overlay to MP4
        success = overlay_audio_to_mp4(Path(input_mp4), mixed_audio, Path(output_mp4))
        
        return success

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Overlay voice to existing MP4")
    parser.add_argument('--yaml', required=True, help='YAML config file')
    parser.add_argument('--input', required=True, help='Input MP4 file')
    parser.add_argument('--output', required=True, help='Output MP4 file')
    
    args = parser.parse_args()
    
    success = overlay_voice_to_short(args.yaml, args.input, args.output)
    
    if success:
        logger.info(f"Success: {args.output}")
        return 0
    else:
        logger.error("Failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
