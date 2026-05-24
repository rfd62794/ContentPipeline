"""
Tests for core/obs_manager.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock obsws_python before importing
sys.modules['obsws_python'] = MagicMock()
sys.modules['obsws_python.obs'] = MagicMock()
sys.modules['obsws_python.error'] = MagicMock()

from core.obs_manager import (
    OBSManager, OBSBoot, OBSCapture, OBSScenes, OBSSources,
    RecordingStatus, StreamStats, build_obs_recording_path, format_recording_note, parse_stream_stats
)


class TestOBSManager:
    def test_init_default_params(self):
        """OBSManager initializes with default parameters."""
        obs_mgr = OBSManager()
        assert obs_mgr.host == 'localhost'
        assert obs_mgr.port == 4455
        assert obs_mgr.password == ''
        assert obs_mgr.client is None
        assert obs_mgr.connected is False
    
    def test_init_custom_params(self):
        """OBSManager initializes with custom parameters."""
        obs_mgr = OBSManager(host='192.168.1.100', port=5555, password='secret')
        assert obs_mgr.host == '192.168.1.100'
        assert obs_mgr.port == 5555
        assert obs_mgr.password == 'secret'
    
    @patch('core.obs_manager.obs')
    def test_connect_success(self, mock_obs):
        """connect() successfully establishes connection."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        obs_mgr = OBSManager()
        result = obs_mgr.connect()
        
        assert result is True
        assert obs_mgr.connected is True
        assert obs_mgr.client == mock_client
        mock_obs.ReqClient.assert_called_once()
    
    @patch('core.obs_manager.obs')
    def test_connect_failure(self, mock_obs):
        """connect() returns False on connection failure."""
        mock_obs.ReqClient.side_effect = Exception("Connection refused")
        
        obs_mgr = OBSManager()
        result = obs_mgr.connect()
        
        assert result is False
        assert obs_mgr.connected is False
    
    def test_disconnect(self):
        """disconnect() closes connection."""
        obs_mgr = OBSManager()
        obs_mgr.client = Mock()
        obs_mgr.connected = True
        
        obs_mgr.disconnect()
        
        assert obs_mgr.client is None
        assert obs_mgr.connected is False
    
    def test_is_connected(self):
        """is_connected() returns connection status."""
        obs_mgr = OBSManager()
        assert obs_mgr.is_connected() is False
        
        obs_mgr.connected = True
        assert obs_mgr.is_connected() is True
    
    @patch('psutil.process_iter')
    def test_ensure_obs_running_already_running(self, mock_process_iter):
        """ensure_obs_running() returns True if OBS already running."""
        mock_proc = Mock()
        mock_proc.info = {'name': 'obs64.exe'}
        mock_process_iter.return_value = iter([mock_proc])
        
        obs_mgr = OBSManager()
        result = OBSBoot.ensure_obs_running()
        
        assert result is True
    
    @patch('psutil.process_iter')
    @patch('core.obs_manager.subprocess')
    @patch('core.obs_manager.Path')
    def test_ensure_obs_running_launch_success(self, mock_path, mock_subprocess, mock_psutil):
        """ensure_obs_running() launches OBS successfully."""
        # OBS not running initially
        mock_psutil.return_value = iter([])
        
        # OBS path exists
        mock_path_obj = Mock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.parent = "C:/Program Files/obs-studio/bin/64bit"
        mock_path.return_value = mock_path_obj
        
        # Launch succeeds
        mock_subprocess.Popen.return_value = None
        
        # OBS starts after 1 second
        mock_proc = Mock()
        mock_proc.info = {'name': 'obs64.exe'}
        mock_psutil.side_effect = [iter([]), iter([mock_proc])]
        
        obs_mgr = OBSManager()
        result = OBSBoot.ensure_obs_running()
        
        assert result is True
        # Verify Popen was called with cwd parameter
        mock_subprocess.Popen.assert_called_once()
        call_kwargs = mock_subprocess.Popen.call_args[1]
        assert 'cwd' in call_kwargs
    
    @patch('core.obs_manager.obs')
    def test_switch_scene_success(self, mock_obs):
        """switch_scene() switches scene successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        scenes = OBSScenes(obs_mgr)
        obs_mgr.connected = True
        
        result = scenes.switch_scene("Gaming")
        
        assert result is True
        mock_client.set_current_program_scene.assert_called_once_with("Gaming")
    
    def test_switch_scene_not_connected(self):
        """switch_scene() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        scenes = OBSScenes(obs_mgr)
        
        result = scenes.switch_scene("Gaming")
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_list_scenes_success(self, mock_obs):
        """list_scenes() returns list of scene names."""
        mock_client = Mock()
        mock_scene_list = Mock()
        mock_scene1 = Mock()
        mock_scene1.scene_name = "Gaming"
        mock_scene2 = Mock()
        mock_scene2.scene_name = "Starting Soon"
        mock_scene_list.scenes = [mock_scene1, mock_scene2]
        mock_client.get_scene_list.return_value = mock_scene_list
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        scenes = OBSScenes(obs_mgr)
        
        scenes = scenes.list_scenes()        
        assert scenes == ["Gaming", "Starting Soon"]
    
    def test_list_scenes_not_connected(self):
        """list_scenes() returns empty list when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        scenes = OBSScenes(obs_mgr)
        
        scenes = scenes.list_scenes()        
        assert scenes == []
    
    @patch('core.obs_manager.obs')
    def test_start_recording_success(self, mock_obs):
        """start_recording() starts recording successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.start_recording()
        
        assert result is True
        mock_client.start_record.assert_called_once()
    
    def test_start_recording_not_connected(self):
        """start_recording() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        result = capture.start_recording()
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_stop_recording_success(self, mock_obs):
        """stop_recording() stops recording and returns file path."""
        mock_client = Mock()
        mock_settings = Mock()
        mock_settings.output_settings = {'path': 'C:/Videos/test.mp4'}
        mock_client.get_output_settings.return_value = mock_settings
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        file_path = capture.stop_recording()
        
        assert file_path == 'C:/Videos/test.mp4'
        mock_client.get_output_settings.assert_called_once_with('simple_file_output')
        mock_client.stop_record.assert_called_once()
    
    def test_stop_recording_not_connected(self):
        """stop_recording() returns None when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        file_path = capture.stop_recording()
        
        assert file_path is None
    
    @patch('core.obs_manager.obs')
    def test_pause_recording_success(self, mock_obs):
        """pause_recording() pauses recording successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.pause_recording()
        
        assert result is True
        mock_client.pause_record.assert_called_once()
    
    def test_pause_recording_not_connected(self):
        """pause_recording() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        result = capture.pause_recording()
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_resume_recording_success(self, mock_obs):
        """resume_recording() resumes recording successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.resume_recording()
        
        assert result is True
        mock_client.resume_record.assert_called_once()
    
    def test_resume_recording_not_connected(self):
        """resume_recording() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        result = capture.resume_recording()
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_is_recording_true(self, mock_obs):
        """is_recording() returns True when recording active."""
        mock_client = Mock()
        mock_status = Mock()
        mock_status.output_active = True
        mock_client.get_record_status.return_value = mock_status
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.is_recording()
        
        assert result is True
    
    @patch('core.obs_manager.obs')
    def test_is_recording_false(self, mock_obs):
        """is_recording() returns False when not recording."""
        mock_client = Mock()
        mock_status = Mock()
        mock_status.output_active = False
        mock_client.get_record_status.return_value = mock_status
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.is_recording()
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_start_stream_success(self, mock_obs):
        """start_stream() starts streaming successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.start_stream()
        
        assert result is True
        mock_client.start_stream.assert_called_once()
    
    def test_start_stream_not_connected(self):
        """start_stream() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        result = capture.start_stream()
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_stop_stream_success(self, mock_obs):
        """stop_stream() stops streaming successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.stop_stream()
        
        assert result is True
        mock_client.stop_stream.assert_called_once()
    
    def test_stop_stream_not_connected(self):
        """stop_stream() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        result = capture.stop_stream()
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_mute_source_success(self, mock_obs):
        """mute_source() mutes source successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        sources = OBSSources(obs_mgr)
        
        result = sources.mute_source("Mic/Audio")
        
        assert result is True
        mock_client.set_input_mute.assert_called_once_with(input_name="Mic/Audio", input_muted=True)
    
    def test_mute_source_not_connected(self):
        """mute_source() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        sources = OBSSources(obs_mgr)
        
        result = sources.mute_source("Mic/Audio")
        
        assert result is False
    
    @patch('core.obs_manager.obs')
    def test_unmute_source_success(self, mock_obs):
        """unmute_source() unmutes source successfully."""
        mock_client = Mock()
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        sources = OBSSources(obs_mgr)
        
        result = sources.unmute_source("Mic/Audio")
        
        assert result is True
        mock_client.set_input_mute.assert_called_once_with(input_name="Mic/Audio", input_muted=False)
    
    def test_unmute_source_not_connected(self):
        """unmute_source() returns False when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        sources = OBSSources(obs_mgr)
        
        result = sources.unmute_source("Mic/Audio")
        
        assert result is False



    @patch('core.obs_manager.obs')
    def test_start_recording_already_active(self, mock_obs):
        """start_recording() returns False when recording already active."""
        mock_client = Mock()
        mock_error = Mock()
        mock_error.__str__ = lambda self: "500 Internal Server Error"
        mock_obs.error.OBSSDKRequestError = Exception
        mock_client.start_record.side_effect = Exception("500 Internal Server Error")
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.start_recording()
        
        assert result is False
        mock_client.start_record.assert_called_once()
    
    @patch('core.obs_manager.obs')
    def test_stop_recording_no_active_recording(self, mock_obs):
        """stop_recording() returns None when no recording active."""
        mock_client = Mock()
        mock_settings = Mock()
        mock_settings.output_settings = {'path': 'C:/Videos/test.mp4'}
        mock_client.get_output_settings.return_value = mock_settings
        mock_error = Mock()
        mock_error.__str__ = lambda self: "500 Internal Server Error"
        mock_obs.error.OBSSDKRequestError = Exception
        mock_client.stop_record.side_effect = Exception("500 Internal Server Error")
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        file_path = capture.stop_recording()
        
        assert file_path is None
        mock_client.get_output_settings.assert_called_once_with('simple_file_output')
        mock_client.stop_record.assert_called_once()
    
    @patch('core.obs_manager.obs')
    def test_pause_recording_no_active_recording(self, mock_obs):
        """pause_recording() returns False when no recording active."""
        mock_client = Mock()
        mock_error = Mock()
        mock_error.__str__ = lambda self: "500 Internal Server Error"
        mock_obs.error.OBSSDKRequestError = Exception
        mock_client.pause_record.side_effect = Exception("500 Internal Server Error")
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.pause_recording()
        
        assert result is False
        mock_client.pause_record.assert_called_once()
    
    @patch('core.obs_manager.obs')
    def test_resume_recording_not_paused(self, mock_obs):
        """resume_recording() returns False when recording not paused."""
        mock_client = Mock()
        mock_error = Mock()
        mock_error.__str__ = lambda self: "500 Internal Server Error"
        mock_obs.error.OBSSDKRequestError = Exception
        mock_client.resume_record.side_effect = Exception("500 Internal Server Error")
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        result = capture.resume_recording()
        
        assert result is False
        mock_client.resume_record.assert_called_once()
    
    @patch('core.obs_manager.obs')
    def test_get_status(self, mock_obs):
        """get_recording_status() returns dict with expected keys."""
        mock_client = Mock()
        mock_status = Mock()
        mock_status.output_active = True
        mock_status.output_bytes = 1024000
        mock_status.output_duration = 30.5
        mock_status.output_timecode = "00:00:30:500"
        mock_client.get_record_status.return_value = mock_status
        
        obs_mgr = OBSManager()
        obs_mgr.client = mock_client
        obs_mgr.connected = True
        capture = OBSCapture(obs_mgr)
        
        status = capture.get_recording_status()
        
        assert status is not None
        assert status.active is True
        assert status.bytes_written == 1024000
        assert status.duration_seconds == 30.5
        assert status.timecode == "00:00:30:500"
    
    def test_get_status_not_connected(self):
        """get_recording_status() returns None when not connected."""
        obs_mgr = OBSManager()
        obs_mgr.connected = False
        capture = OBSCapture(obs_mgr)
        
        status = capture.get_recording_status()
        
        assert status is None
    
    @patch('core.obs_manager.obs')
    def test_context_manager(self, mock_obs):
        """OBSManager works as context manager."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        with OBSManager() as obs_mgr:
            assert obs_mgr.connected is True
            assert obs_mgr.client == mock_client
        
        assert obs_mgr.connected is False
        assert obs_mgr.client is None
    
    def test_recording_status_creation(self):
        """RecordingStatus dataclass has expected fields."""
        status = RecordingStatus(
            active=True,
            bytes_written=1024000,
            duration_seconds=30.5,
            timecode="00:00:30:500"
        )
        
        assert status.active is True
        assert status.bytes_written == 1024000
        assert status.duration_seconds == 30.5
        assert status.timecode == "00:00:30:500"

class TestPureFunctions:
    def test_build_obs_recording_path(self):
        """build_obs_recording_path() formats recording path correctly."""
        dt = datetime(2026, 5, 23, 20, 30, 45)
        path = build_obs_recording_path("Dorfromantik", dt)
        
        assert path == "Dorfromantik_20260523_203045.mp4"
    
    def test_format_recording_note(self):
        """format_recording_note() formats note correctly."""
        dt = datetime(2026, 5, 23, 20, 30, 45)
        note = format_recording_note("C:/Videos/test.mp4", dt)
        
        assert "# OBS Recording: C:/Videos/test.mp4 at 2026-05-23 20:30:45" in note
    
    def test_parse_stream_stats(self):
        """parse_stream_stats() parses stats correctly."""
        raw_response = {
            'output_bitrate': 5000,
            'output_dropped_frames': 10,
            'output_total_frames': 1000,
            'output_duration': 120.5
        }
        
        stats = parse_stream_stats(raw_response)
        
        assert stats['bitrate'] == 5000
        assert stats['dropped_frames'] == 10
        assert stats['total_frames'] == 1000
        assert stats['duration'] == 120.5
    
    def test_parse_stream_stats_empty(self):
        """parse_stream_stats() handles empty response."""
        raw_response = {}
        
        stats = parse_stream_stats(raw_response)
        
        assert stats['bitrate'] == 0
        assert stats['dropped_frames'] == 0
        assert stats['total_frames'] == 0
        assert stats['duration'] == 0

class TestNewClasses:
    """Tests for the four new OBS classes after refactor."""
    
    def test_obs_boot_instantiates(self):
        """OBSBoot class exists and ensure_obs_running is callable."""
        assert hasattr(OBSBoot, 'ensure_obs_running')
        assert callable(OBSBoot.ensure_obs_running)
    
    def test_obs_boot_is_static(self):
        """OBSBoot.ensure_obs_running is a static method."""
        import inspect
        assert isinstance(inspect.getattr_static(OBSBoot, 'ensure_obs_running'), staticmethod)
    
    def test_obs_capture_instantiates(self):
        """OBSCapture takes mock OBSManager and all methods are callable."""
        mock_obs = Mock()
        capture = OBSCapture(mock_obs)
        
        assert capture.obs == mock_obs
        assert hasattr(capture, 'start_recording')
        assert hasattr(capture, 'stop_recording')
        assert hasattr(capture, 'pause_recording')
        assert hasattr(capture, 'resume_recording')
        assert hasattr(capture, 'is_recording')
        assert hasattr(capture, 'get_recording_status')
        assert hasattr(capture, 'start_stream')
        assert hasattr(capture, 'stop_stream')
        assert hasattr(capture, 'get_stream_stats')
        
        # Verify all methods are callable
        assert callable(capture.start_recording)
        assert callable(capture.stop_recording)
        assert callable(capture.pause_recording)
        assert callable(capture.resume_recording)
        assert callable(capture.is_recording)
        assert callable(capture.get_recording_status)
        assert callable(capture.start_stream)
        assert callable(capture.stop_stream)
        assert callable(capture.get_stream_stats)
    
    def test_obs_scenes_instantiates(self):
        """OBSScenes takes mock OBSManager and all methods are callable."""
        mock_obs = Mock()
        scenes = OBSScenes(mock_obs)
        
        assert scenes.obs == mock_obs
        assert hasattr(scenes, 'switch_scene')
        assert hasattr(scenes, 'list_scenes')
        
        assert callable(scenes.switch_scene)
        assert callable(scenes.list_scenes)
    
    def test_obs_sources_instantiates(self):
        """OBSSources takes mock OBSManager and all methods are callable."""
        mock_obs = Mock()
        sources = OBSSources(mock_obs)
        
        assert sources.obs == mock_obs
        assert hasattr(sources, 'add_game_capture')
        assert hasattr(sources, 'remove_game_capture')
        assert hasattr(sources, 'mute_source')
        assert hasattr(sources, 'unmute_source')
        
        assert callable(sources.add_game_capture)
        assert callable(sources.remove_game_capture)
        assert callable(sources.mute_source)
        assert callable(sources.unmute_source)
    
    def test_obs_manager_has_no_recording_methods(self):
        """OBSManager has no recording, streaming, scene, or source methods after refactor."""
        obs_mgr = OBSManager()
        
        # Recording methods should NOT exist
        assert not hasattr(obs_mgr, 'start_recording')
        assert not hasattr(obs_mgr, 'stop_recording')
        assert not hasattr(obs_mgr, 'pause_recording')
        assert not hasattr(obs_mgr, 'resume_recording')
        assert not hasattr(obs_mgr, 'is_recording')
        assert not hasattr(obs_mgr, 'get_recording_status')
        
        # Streaming methods should NOT exist
        assert not hasattr(obs_mgr, 'start_stream')
        assert not hasattr(obs_mgr, 'stop_stream')
        assert not hasattr(obs_mgr, 'get_stream_stats')
        
        # Scene methods should NOT exist
        assert not hasattr(obs_mgr, 'switch_scene')
        assert not hasattr(obs_mgr, 'list_scenes')
        
        # Source methods should NOT exist
        assert not hasattr(obs_mgr, 'add_game_capture')
        assert not hasattr(obs_mgr, 'remove_game_capture')
        assert not hasattr(obs_mgr, 'mute_source')
        assert not hasattr(obs_mgr, 'unmute_source')
        
        # Boot method should NOT exist
        assert not hasattr(obs_mgr, 'ensure_obs_running')
    
    def test_obs_manager_connection_methods_present(self):
        """OBSManager retains connection methods after refactor."""
        obs_mgr = OBSManager()
        
        assert hasattr(obs_mgr, 'connect')
        assert hasattr(obs_mgr, 'disconnect')
        assert hasattr(obs_mgr, 'is_connected')
        assert hasattr(obs_mgr, '__enter__')
        assert hasattr(obs_mgr, '__exit__')
        
        assert callable(obs_mgr.connect)
        assert callable(obs_mgr.disconnect)
        assert callable(obs_mgr.is_connected)
        assert callable(obs_mgr.__enter__)
        assert callable(obs_mgr.__exit__)
