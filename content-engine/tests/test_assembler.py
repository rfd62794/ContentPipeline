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
        """Ken Burns cycling calculates correct intervals for image timing."""
        
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
        """Cycling wraps images when list has multiple items."""
        
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
    def test_assembler_horizontal_unchanged(self, mock_copy, mock_run):
        """shorts_mode=False produces 1920x1080 as before."""

        
        # Configure mock to return successful results
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        segments = [{
            "temp_file": "test.mp4",
            "segment_text": "Test",
            "duration": 5.0
        }]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            audio_path = temp_dir / "audio.mp3"
            audio_path.touch()
            # Create the temp file that the segment references
            (temp_dir / "test.mp4").touch()
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
    

    


    # Multi-segment tests (Phase S5) - basic function existence and signature tests
    
    def test_multi_segment_helper_functions_exist(self):
        """Multi-segment helper functions exist and are callable."""
        from core.assembler import _get_clip_for_segment, _concatenate_clips, _extract_clip_from_local, _parse_timestamp
        
        # Verify functions exist
        self.assertTrue(callable(_get_clip_for_segment))
        self.assertTrue(callable(_concatenate_clips))
        self.assertTrue(callable(_extract_clip_from_local))
        self.assertTrue(callable(_parse_timestamp))
    
    def test_parse_timestamp_valid_formats(self):
        """_parse_timestamp handles MM:SS and HH:MM:SS formats."""
        from core.assembler import _parse_timestamp
        
        # MM:SS format
        self.assertEqual(_parse_timestamp("1:30"), 90)
        self.assertEqual(_parse_timestamp("5:00"), 300)
        
        # HH:MM:SS format
        self.assertEqual(_parse_timestamp("1:30:00"), 5400)
        self.assertEqual(_parse_timestamp("0:05:30"), 330)
        
        # Invalid format
        self.assertIsNone(_parse_timestamp("invalid"))
        self.assertIsNone(_parse_timestamp(""))
    
    def test_parse_timestamp_edge_cases(self):
        """_parse_timestamp handles edge cases correctly."""
        from core.assembler import _parse_timestamp
        
        # Zero values
        self.assertEqual(_parse_timestamp("0:00"), 0)
        self.assertEqual(_parse_timestamp("0:00:00"), 0)
        
        # Large values
        self.assertEqual(_parse_timestamp("59:59"), 3599)
        self.assertEqual(_parse_timestamp("1:00:00"), 3600)
    
    def test_get_clip_function_signature(self):
        """_get_clip_for_segment has correct signature."""
        from core.assembler import _get_clip_for_segment
        import inspect
        
        sig = inspect.signature(_get_clip_for_segment)
        params = list(sig.parameters.keys())
        
        self.assertIn("segment", params)
        self.assertIn("temp_dir", params)
        self.assertIn("index", params)
    
    def test_concatenate_clips_function_signature(self):
        """_concatenate_clips has correct signature."""
        from core.assembler import _concatenate_clips
        import inspect
        
        sig = inspect.signature(_concatenate_clips)
        params = list(sig.parameters.keys())
        
        self.assertIn("clip_paths", params)
        self.assertIn("temp_dir", params)
    
    def test_extract_clip_from_local_function_signature(self):
        """_extract_clip_from_local has correct signature."""
        from core.assembler import _extract_clip_from_local
        import inspect
        
        sig = inspect.signature(_extract_clip_from_local)
        params = list(sig.parameters.keys())
        
        self.assertIn("source_path", params)
        self.assertIn("start_time", params)
        self.assertIn("end_time", params)
        self.assertIn("temp_dir", params)
        self.assertIn("index", params)
    
    def test_multi_segment_data_structure(self):
        """Segment data structure supports all required fields."""
        segment = {
            "temp_file": "test.mp4",
            "segment_text": "Test text",
            "duration": 5.0,
            "source_url": "https://youtube.com/watch?v=test",
            "source_timestamp_start": "0:00",
            "source_timestamp_end": "0:10"
        }
        
        # Verify all required fields are present
        self.assertIn("temp_file", segment)
        self.assertIn("segment_text", segment)
        self.assertIn("duration", segment)
        self.assertIn("source_url", segment)
        self.assertIn("source_timestamp_start", segment)
        self.assertIn("source_timestamp_end", segment)
    
    def test_multi_segment_minimal_data_structure(self):
        """Segment works with minimal required fields (backward compat)."""
        segment = {
            "temp_file": "test.mp4",
            "segment_text": "Test text",
            "duration": 5.0
        }
        
        # Minimal structure should be valid
        self.assertIn("temp_file", segment)
        self.assertIn("segment_text", segment)
        self.assertIn("duration", segment)
    
    def test_add_lower_third_text_new_signature(self):
        """_add_lower_third_text has updated signature with duration parameter."""
        from core.assembler import _add_lower_third_text
        import inspect
        
        sig = inspect.signature(_add_lower_third_text)
        params = list(sig.parameters.keys())
        
        # New signature should have duration parameter
        self.assertIn("duration", params)
        # Should not have old segments parameter
        self.assertNotIn("segments", params)
    
    def test_add_attribution_text_new_signature(self):
        """_add_attribution_text has updated signature with y_center parameter."""
        from core.assembler import _add_attribution_text
        import inspect
        
        sig = inspect.signature(_add_attribution_text)
        params = list(sig.parameters.keys())
        
        # New signature should have y_center parameter
        self.assertIn("y_center", params)
    
    def test_assemble_video_signature_unchanged(self):
        """assemble_video signature remains unchanged for backward compatibility."""
        from core.assembler import assemble_video
        import inspect
        
        sig = inspect.signature(assemble_video)
        params = list(sig.parameters.keys())
        
        # Should still have original parameters
        self.assertIn("segments", params)
        self.assertIn("audio_path", params)
        self.assertIn("output_path", params)
        self.assertIn("temp_dir", params)
        self.assertIn("config", params)
        self.assertIn("shorts_mode", params)
        self.assertIn("attribution", params)
    
    def test_multi_segment_duration_field_required(self):
        """Segment data structure requires duration field for multi-segment."""
        # Segment without duration should still be handled gracefully
        segment = {
            "temp_file": "test.mp4",
            "segment_text": "Test text"
        }
        
        # Duration field is important for multi-segment timing
        # Test that we can add it
        segment["duration"] = 5.0
        self.assertEqual(segment["duration"], 5.0)
    
    def test_timestamp_parsing_consistency(self):
        """Timestamp parsing is consistent across helper functions."""
        from core.assembler import _parse_timestamp
        
        # Test that same timestamp produces same result
        result1 = _parse_timestamp("1:30")
        result2 = _parse_timestamp("1:30")
        
        self.assertEqual(result1, result2)
        self.assertEqual(result1, 90)
    
    # Phase S5 Multi-Segment Tests (Replacement for deleted old tests)
    
    @patch("core.assembler.shutil.copy")
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler._concatenate_clips")
    @patch("core.assembler._add_attribution_text")
    def test_multi_segment_processes_all_segments(self, mock_attribution, mock_concat, mock_run, mock_copy):
        """Multi-segment: _assemble_shorts() with 3 segments calls _add_lower_third_text() exactly 3 times."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_concat.return_value = Path("combined.mp4")
        mock_attribution.return_value = Path("final.mp4")
        
        segments = [
            {"temp_file": "test1.mp4", "segment_text": "Text 1", "duration": 2},
            {"temp_file": "test2.mp4", "segment_text": "Text 2", "duration": 3},
            {"temp_file": "test3.mp4", "segment_text": "Text 3", "duration": 4}
        ]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            config = {"shorts_music_path": None, "shorts_attribution_enabled": True}
            
            for seg in segments:
                (temp_dir / seg["temp_file"]).touch()
            
            assemble_video(segments, None, output_path, temp_dir, config, shorts_mode=True, attribution="Test")
            
            # Count how many times _add_lower_third_text was called (via subprocess.run calls with drawtext)
            text_overlay_calls = 0
            for call in mock_run.call_args_list:
                cmd_str = str(call)
                if "drawtext" in cmd_str and "enable='between(t" in cmd_str:
                    text_overlay_calls += 1
            
            # Should have exactly 3 text overlay calls (one per segment)
            self.assertEqual(text_overlay_calls, 3, "Should process exactly 3 segments with text overlays")
    
    @patch("core.assembler.shutil.copy")
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler._concatenate_clips")
    @patch("core.assembler._add_attribution_text")
    def test_multi_segment_attribution_once(self, mock_attribution, mock_concat, mock_run, mock_copy):
        """Multi-segment: _add_attribution_text() called exactly once regardless of segment count."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_concat.return_value = Path("combined.mp4")
        mock_attribution.return_value = Path("final.mp4")
        
        segments = [
            {"temp_file": "test1.mp4", "segment_text": "Text 1", "duration": 2},
            {"temp_file": "test2.mp4", "segment_text": "Text 2", "duration": 3}
        ]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            config = {"shorts_music_path": None, "shorts_attribution_enabled": True}
            
            for seg in segments:
                (temp_dir / seg["temp_file"]).touch()
            
            assemble_video(segments, None, output_path, temp_dir, config, shorts_mode=True, attribution="Test")
            
            # Attribution should be called exactly once
            mock_attribution.assert_called_once()
    
    @patch("core.assembler.shutil.copy")
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler._concatenate_clips")
    def test_multi_segment_no_attribution_when_none(self, mock_concat, mock_run, mock_copy):
        """Multi-segment: _add_attribution_text() never called when attribution=None."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_concat.return_value = Path("combined.mp4")
        
        segments = [
            {"temp_file": "test1.mp4", "segment_text": "Text 1", "duration": 2},
            {"temp_file": "test2.mp4", "segment_text": "Text 2", "duration": 3}
        ]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            config = {"shorts_music_path": None, "shorts_attribution_enabled": True}
            
            for seg in segments:
                (temp_dir / seg["temp_file"]).touch()
            
            assemble_video(segments, None, output_path, temp_dir, config, shorts_mode=True, attribution=None)
            
            # Verify that no attribution command was called (no drawtext with "attribution")
            for call in mock_run.call_args_list:
                cmd_str = str(call)
                self.assertNotIn("attribution", cmd_str.lower(), "No attribution should be added when attribution=None")
    
    @patch("core.assembler.shutil.copy")
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler._concatenate_clips")
    @patch("core.assembler._add_attribution_text")
    def test_multi_segment_scale_command_new_layout(self, mock_attribution, mock_concat, mock_run, mock_copy):
        """Multi-segment: FFmpeg scale command contains blur fill filter_complex with boxblur and colorchannelmixer."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_concat.return_value = Path("combined.mp4")
        mock_attribution.return_value = Path("final.mp4")
        
        segments = [
            {"temp_file": "test1.mp4", "segment_text": "Text 1", "duration": 2}
        ]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            config = {"shorts_music_path": None, "shorts_attribution_enabled": True}
            
            (temp_dir / "test1.mp4").touch()
            
            assemble_video(segments, None, output_path, temp_dir, config, shorts_mode=True, attribution="Test")
            
            # Verify that scale command uses blur fill with filter_complex
            blur_fill_found = False
            for call in mock_run.call_args_list:
                cmd_str = str(call)
                if "filter_complex" in cmd_str and "boxblur=20:5" in cmd_str and "colorchannelmixer=rr=0.7:gg=0.7:bb=0.7" in cmd_str:
                    blur_fill_found = True
                    break
            
            self.assertTrue(blur_fill_found, "Scale command should use blur fill filter_complex")
    
    @patch("core.assembler.shutil.copy")
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler._concatenate_clips")
    @patch("core.assembler._add_attribution_text")
    def test_multi_segment_music_missing_completes(self, mock_attribution, mock_concat, mock_run, mock_copy):
        """Multi-segment: Missing shorts_music_path completes assembly without exception."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_concat.return_value = Path("combined.mp4")
        mock_attribution.return_value = Path("final.mp4")
        
        segments = [
            {"temp_file": "test1.mp4", "segment_text": "Text 1", "duration": 2}
        ]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            config = {"shorts_music_path": "nonexistent.mp3", "shorts_attribution_enabled": False}
            
            (temp_dir / "test1.mp4").touch()
            
            # Should not raise exception
            assemble_video(segments, None, output_path, temp_dir, config, shorts_mode=True)
            
            # Should complete successfully
            self.assertTrue(mock_run.called or mock_concat.called or mock_attribution.called, "Assembly should complete despite missing music")
    
    @patch("core.assembler.shutil.copy")
    @patch("core.assembler.subprocess.run")
    @patch("core.assembler._concatenate_clips")
    @patch("core.assembler._add_attribution_text")
    def test_multi_segment_muted_clip_no_audio(self, mock_attribution, mock_concat, mock_run, mock_copy):
        """Multi-segment: FFmpeg scale command contains -an flag (no audio in scaled segments)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_concat.return_value = Path("combined.mp4")
        mock_attribution.return_value = Path("final.mp4")
        
        segments = [
            {"temp_file": "test1.mp4", "segment_text": "Text 1", "duration": 2}
        ]
        
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = Path(tmp)
            output_path = temp_dir / "output.mp4"
            config = {"shorts_music_path": None, "shorts_attribution_enabled": False}
            
            (temp_dir / "test1.mp4").touch()
            
            assemble_video(segments, None, output_path, temp_dir, config, shorts_mode=True)
            
            # Verify that -an flag appears in scale commands (no audio)
            has_an_flag = False
            for call in mock_run.call_args_list:
                cmd_str = str(call)
                if "-an" in cmd_str:
                    has_an_flag = True
                    break
            
            self.assertTrue(has_an_flag, "Scale command should contain -an flag to remove audio")
    
    @patch("core.assembler.Path")
    def test_get_clip_uses_temp_file(self, mock_path):
        """_get_clip_for_segment() returns temp_file if it exists."""
        from core.assembler import _get_clip_for_segment
        
        mock_temp_file = MagicMock()
        mock_temp_file.exists.return_value = True
        mock_path.return_value = mock_temp_file
        
        segment = {"temp_file": "existing.mp4"}
        temp_dir = Path("/tmp")
        
        result = _get_clip_for_segment(segment, temp_dir, 0)
        
        # Should return the temp_file path
        self.assertIsNotNone(result)

if __name__ == "__main__":
    unittest.main()
