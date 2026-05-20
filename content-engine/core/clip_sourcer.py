"""
Clip Sourcer — yt-dlp based video clip download

Extracted from youtube_sourcer.py download_clip function.
Clean interface for downloading timestamped clips from YouTube.

Contract:
- download_clip(url, start_time, end_time, output_filename) downloads clip
- clip_exists(filepath) checks file existence
- All failures return empty string and log error — never sys.exit()
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional


class ClipSourcer:
    """Download timestamped clips from YouTube using yt-dlp."""
    
    def __init__(self, output_dir: str, logger) -> None:
        """
        Initialize ClipSourcer.
        
        Args:
            output_dir: Directory to save downloaded clips
            logger: Logger instance for operation logging
        """
        self.output_dir = Path(output_dir)
        self.logger = logger
    
    def download_clip(self, url: str, start_time: str, end_time: str, 
                     output_filename: str = None) -> str:
        """
        Download a timestamped clip from YouTube.
        
        Args:
            url: YouTube video URL
            start_time: Start timestamp in "MM:SS" or "HH:MM:SS" format
            end_time: End timestamp in "MM:SS" or "HH:MM:SS" format
            output_filename: Optional output filename (auto-generated if None)
            
        Returns:
            Filepath of downloaded clip on success, empty string on failure
        """
        # Create output directory if missing
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse timestamps
        start_seconds = self._parse_timestamp(start_time)
        end_seconds = self._parse_timestamp(end_time)
        
        if start_seconds is None or end_seconds is None:
            self.logger.error(f"Invalid timestamp format: {start_time} - {end_time}")
            return ""
        
        # Add buffer
        buffer = 2
        s = max(0, start_seconds - buffer)
        e = end_seconds + buffer
        
        # Generate output filename
        video_id = url.split("=")[-1]
        if output_filename is None:
            output_filename = f"{video_id}_{s}_{e}.mp4"
        
        output_path = self.output_dir / output_filename
        
        # Build yt-dlp command
        cmd = [
            "yt-dlp",
            "--download-sections", f"*{s}-{e}",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", str(output_path),
            url
        ]
        
        try:
            self.logger.info(f"ClipSourcer: Downloading clip {s}-{e} from {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                self.logger.error(f"ClipSourcer: yt-dlp failed: {result.stderr[:500]}")
                return ""
            
            if output_path.exists():
                self.logger.info(f"ClipSourcer: Clip saved to {output_path}")
                return str(output_path)
            else:
                self.logger.error(f"ClipSourcer: Output file not found at {output_path}")
                return ""
                
        except subprocess.TimeoutExpired:
            self.logger.error("ClipSourcer: Download timed out")
            return ""
        except Exception as e:
            self.logger.error(f"ClipSourcer: Download failed: {e}")
            return ""
    
    def clip_exists(self, filepath: str) -> bool:
        """
        Check if a clip file exists.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return Path(filepath).exists()
    
    def _parse_timestamp(self, timestamp: str) -> Optional[int]:
        """
        Parse timestamp string to seconds.
        
        Args:
            timestamp: Timestamp in "MM:SS" or "HH:MM:SS" format
            
        Returns:
            Seconds as integer, or None if parsing fails
        """
        try:
            parts = timestamp.split(":")
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                return None
        except (ValueError, AttributeError):
            return None