import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.assembler import preprocess_segment, _format_timestamp, assemble_video

class TestAssembler(unittest.TestCase):
    def test_format_timestamp(self):
        self.assertEqual(_format_timestamp(61.5), "00:01:01,500")
        self.assertEqual(_format_timestamp(3661.001), "01:01:01,001")

    @patch("subprocess.run")
    @patch("shutil.move")
    def test_ken_burns_cycling_calculates_correct_intervals(self, mock_move, mock_run):
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segment = {
            "segment_index": 0,
            "estimated_duration_s": 25,
            "selected_asset": "img.png",
            "image_paths": json.dumps(["img1.png", "img2.png"]),
            "visual_type": "image"
        }
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            config = {
                "image_cycling_enabled": True,
                "image_cycling_interval_s": 10
            }
            
            # 25s duration / 10s interval = 3 intervals (10, 10, 5)
            preprocess_segment(segment, temp_dir, config)
            
            # Verify subprocess.run was called for each interval (3 times) + 1 for concat
            # Total calls = 4
            self.assertEqual(mock_run.call_count, 4)
        
    @patch("subprocess.run")
    @patch("shutil.move")
    def test_cycling_wraps_images(self, mock_move, mock_run):
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segment = {
            "segment_index": 1,
            "estimated_duration_s": 30,
            "selected_asset": "img.png",
            "image_paths": json.dumps(["only_one.png"]),
            "visual_type": "image"
        }
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            config = {
                "image_cycling_enabled": True,
                "image_cycling_interval_s": 10
            }
            
            # 30s duration / 10s interval = 3 intervals
            # But only 1 unique image provided. It should wrap.
            preprocess_segment(segment, temp_dir, config)
            
            # Check that the 3 interval commands all used "only_one.png"
            calls = mock_run.call_args_list
            # First 3 calls are the interval generations
            for i in range(3):
                cmd = calls[i][0][0]
                self.assertIn("only_one.png", cmd)
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_shorts_mode_vertical(self, mock_copy, mock_run):
        """shorts_mode=True passes 1080x1920 to FFmpeg."""
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test segment text"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()  # Create dummy audio file
            config = {
                "shorts_music_path": None,
                "shorts_text_font": "monospace",
                "shorts_text_size": 48,
                "shorts_text_color": "white",
                "shorts_lower_third_height_pct": 0.25
            }
            
            assemble_video(segments, audio_path, output_path, temp_dir, config, shorts_mode=True)
            
            # Verify that FFmpeg was called with vertical resolution
            calls = mock_run.call_args_list
            # Check that scale filter includes 1080x1920
            scale_call_found = False
            for call in calls:
                cmd = call[0][0] if call[0] else []
                if "scale=1080:1920" in " ".join(cmd):
                    scale_call_found = True
                    break
            self.assertTrue(scale_call_found, "FFmpeg scale call should include 1080x1920")
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_shorts_mode_mutes_clip(self, mock_copy, mock_run):
        """shorts_mode=True includes -an flag on input clip."""
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            config = {"shorts_music_path": None}
            
            assemble_video(segments, audio_path, output_path, temp_dir, config, shorts_mode=True)
            
            # Verify that -an flag is used (no audio)
            calls = mock_run.call_args_list
            audio_flag_found = False
            for call in calls:
                cmd = call[0][0] if call[0] else []
                if "-an" in cmd:
                    audio_flag_found = True
                    break
            self.assertTrue(audio_flag_found, "FFmpeg should include -an flag to mute audio")
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_horizontal_unchanged(self, mock_copy, mock_run):
        """shorts_mode=False produces 1920x1080 as before."""
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            config = {}
            
            assemble_video(segments, audio_path, output_path, temp_dir, config, shorts_mode=False)
            
            # Verify that horizontal path is used (no vertical scaling)
            calls = mock_run.call_args_list
            vertical_scale_found = False
            for call in calls:
                cmd = call[0][0] if call[0] else []
                if "1080:1920" in " ".join(cmd):
                    vertical_scale_found = True
                    break
            self.assertFalse(vertical_scale_found, "Horizontal mode should not use vertical scaling")
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_music_missing_no_halt(self, mock_copy, mock_run):
        """Missing music path logs warning, continues."""
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            config = {"shorts_music_path": "nonexistent.mp3"}  # Missing file
            
            # Should not raise exception despite missing music
            assemble_video(segments, audio_path, output_path, temp_dir, config, shorts_mode=True)
            
            # Verify it completed without error
            self.assertTrue(mock_copy.called, "Should copy output despite missing music")
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_attribution_renders(self, mock_copy, mock_run):
        """shorts_mode with attribution passes attribution string to FFmpeg."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test segment text"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            config = {
                "shorts_music_path": None,
                "shorts_attribution_enabled": True,
                "shorts_attribution_y_pct": 0.05,
                "shorts_attribution_font_size": 30,
                "shorts_attribution_color": "white",
                "shorts_attribution_opacity": 0.85
            }
            
            assemble_video(segments, audio_path, output_path, temp_dir, config, 
                         shorts_mode=True, attribution="Gameplay via: CohhCarnage")
            
            # Verify that drawtext was called with attribution text
            calls = mock_run.call_args_list
            attribution_found = False
            for call in calls:
                cmd = call[0] if call[0] else []
                cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                if "Gameplay via: CohhCarnage" in cmd_str:
                    attribution_found = True
                    break
            self.assertTrue(attribution_found, "FFmpeg should include attribution text")
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_no_attribution_unchanged(self, mock_copy, mock_run):
        """shorts_mode with attribution=None matches pre-attribution output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test segment text"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            config = {
                "shorts_music_path": None,
                "shorts_attribution_enabled": True
            }
            
            # Call without attribution
            assemble_video(segments, audio_path, output_path, temp_dir, config, 
                         shorts_mode=True, attribution=None)
            
            # Verify that attribution text is NOT in any FFmpeg call
            calls = mock_run.call_args_list
            for call in calls:
                cmd = call[0] if call[0] else []
                cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                if "Gameplay via:" in cmd_str or "attribution" in cmd_str.lower():
                    self.fail("No attribution text should be present when attribution=None")
    
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler.shutil.copy")
    def test_assembler_attribution_position(self, mock_copy, mock_run):
        """attribution y position uses shorts_attribution_y_pct from config."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test"
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            config = {
                "shorts_music_path": None,
                "shorts_attribution_enabled": True,
                "shorts_attribution_y_pct": 0.1,
                "shorts_attribution_font_size": 30
            }
            
            assemble_video(segments, audio_path, output_path, temp_dir, config, 
                         shorts_mode=True, attribution="Test attribution")
            
            # Verify that the custom y_pct (0.1 = 10%) is used in calculation
            # 1920 * 0.1 = 192 pixels from top
            calls = mock_run.call_args_list
            y_position_found = False
            for call in calls:
                cmd = call[0] if call[0] else []
                cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
                if "y=192" in cmd_str:  # 1920 * 0.1 = 192
                    y_position_found = True
                    break
            self.assertTrue(y_position_found, "Should use custom y position from config")

if __name__ == "__main__":
    unittest.main()
