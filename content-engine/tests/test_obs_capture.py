"""
Tests for core/obs_capture.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock obsws_python before importing
sys.modules['obsws_python'] = MagicMock()
sys.modules['obsws_python.obs'] = MagicMock()
sys.modules['obsws_python.error'] = MagicMock()

from core.obs_capture import OBSCapture, OBSCaptureError, RecordingStatus


class TestOBSCapture:
    def test_init_default_params(self):
        """OBSCapture initializes with default parameters."""
        obs_cap = OBSCapture()
        assert obs_cap.host == 'localhost'
        assert obs_cap.port == 4455
        assert obs_cap.password == ''
        assert obs_cap.client is None
        assert obs_cap.connected is False
    
    def test_init_custom_params(self):
        """OBSCapture initializes with custom parameters."""
        obs_cap = OBSCapture(host='192.168.1.100', port=5555, password='secret')
        assert obs_cap.host == '192.168.1.100'
        assert obs_cap.port == 5555
        assert obs_cap.password == 'secret'
    
    @patch('core.obs_capture.obs')
    def test_connect_success(self, mock_obs):
        """connect() successfully establishes connection."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        
        assert obs_cap.connected is True
        assert obs_cap.client == mock_client
        mock_obs.ReqClient.assert_called_once()
    
    @patch('core.obs_capture.obs')
    def test_connect_failure(self, mock_obs):
        """connect() raises OBSCaptureError on connection failure."""
        mock_obs.ReqClient.side_effect = Exception("Connection refused")
        
        obs_cap = OBSCapture()
        try:
            obs_cap.connect()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Failed to connect to OBS" in str(e)
    
    def test_disconnect(self):
        """disconnect() closes connection."""
        obs_cap = OBSCapture()
        obs_cap.client = Mock()
        obs_cap.connected = True
        
        obs_cap.disconnect()
        
        assert obs_cap.client is None
        assert obs_cap.connected is False
    
    @patch('core.obs_capture.obs')
    def test_start_recording_success(self, mock_obs):
        """start_recording() starts recording successfully."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        obs_cap.start_recording()
        
        mock_client.start_record.assert_called_once()
    
    @patch('core.obs_capture.obs')
    def test_start_recording_not_connected(self, mock_obs):
        """start_recording() raises error when not connected."""
        obs_cap = OBSCapture()
        try:
            obs_cap.start_recording()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Not connected to OBS" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_start_recording_already_active(self, mock_obs):
        """start_recording() raises error when recording already active."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        # Create custom exception that mimics OBSSDKRequestError
        class MockOBSSDKRequestError(Exception):
            def __str__(self):
                return "Request StartRecord returned code 500"
        
        mock_obs.error.OBSSDKRequestError = MockOBSSDKRequestError
        mock_client.start_record.side_effect = MockOBSSDKRequestError()
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        
        try:
            obs_cap.start_recording()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Recording already active" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_stop_recording_success(self, mock_obs):
        """stop_recording() stops recording and returns file path."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        # Mock output settings
        mock_settings = Mock()
        mock_settings.output_settings = {'path': 'C:/Videos/test.mp4'}
        mock_client.get_output_settings.return_value = mock_settings
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        file_path = obs_cap.stop_recording()
        
        assert file_path == 'C:/Videos/test.mp4'
        mock_client.get_output_settings.assert_called_once_with('simple_file_output')
        mock_client.stop_record.assert_called_once()
    
    @patch('core.obs_capture.obs')
    def test_stop_recording_not_connected(self, mock_obs):
        """stop_recording() raises error when not connected."""
        obs_cap = OBSCapture()
        try:
            obs_cap.stop_recording()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Not connected to OBS" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_stop_recording_no_active_recording(self, mock_obs):
        """stop_recording() raises error when no recording active."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        # Mock output settings
        mock_settings = Mock()
        mock_settings.output_settings = {'path': 'C:/Videos/test.mp4'}
        mock_client.get_output_settings.return_value = mock_settings
        
        # Create custom exception that mimics OBSSDKRequestError
        class MockOBSSDKRequestError(Exception):
            def __str__(self):
                return "Request StopRecord returned code 500"
        
        mock_obs.error.OBSSDKRequestError = MockOBSSDKRequestError
        mock_client.stop_record.side_effect = MockOBSSDKRequestError()
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        
        try:
            obs_cap.stop_recording()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "No recording active" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_get_status(self, mock_obs):
        """get_status() returns RecordingStatus object."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        # Mock record status
        mock_status = Mock()
        mock_status.output_active = True
        mock_status.output_bytes = 1000000
        mock_status.output_duration = 10.5
        mock_status.output_timecode = "00:00:10.500"
        mock_client.get_record_status.return_value = mock_status
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        status = obs_cap.get_status()
        
        assert isinstance(status, RecordingStatus)
        assert status.active is True
        assert status.bytes_written == 1000000
        assert status.duration_seconds == 10.5
        assert status.timecode == "00:00:10.500"
    
    @patch('core.obs_capture.obs')
    def test_get_status_not_connected(self, mock_obs):
        """get_status() raises error when not connected."""
        obs_cap = OBSCapture()
        try:
            obs_cap.get_status()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Not connected to OBS" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_set_scene(self, mock_obs):
        """set_scene() switches to specified scene."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        obs_cap.set_scene("GameScene")
        
        mock_client.set_current_program_scene.assert_called_once_with("GameScene")
    
    @patch('core.obs_capture.obs')
    def test_set_scene_not_connected(self, mock_obs):
        """set_scene() raises error when not connected."""
        obs_cap = OBSCapture()
        try:
            obs_cap.set_scene("GameScene")
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Not connected to OBS" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_list_scenes(self, mock_obs):
        """list_scenes() returns list of scene names."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        # Mock scene list
        mock_scene_list = Mock()
        mock_scene1 = Mock()
        mock_scene1.scene_name = "GameScene"
        mock_scene2 = Mock()
        mock_scene2.scene_name = "CameraScene"
        mock_scene_list.scenes = [mock_scene1, mock_scene2]
        mock_client.get_scene_list.return_value = mock_scene_list
        
        obs_cap = OBSCapture()
        obs_cap.connect()
        scenes = obs_cap.list_scenes()
        
        assert scenes == ["GameScene", "CameraScene"]
    
    @patch('core.obs_capture.obs')
    def test_list_scenes_not_connected(self, mock_obs):
        """list_scenes() raises error when not connected."""
        obs_cap = OBSCapture()
        try:
            obs_cap.list_scenes()
            assert False, "Should have raised OBSCaptureError"
        except OBSCaptureError as e:
            assert "Not connected to OBS" in str(e)
    
    @patch('core.obs_capture.obs')
    def test_context_manager(self, mock_obs):
        """OBSCapture works as context manager."""
        mock_client = Mock()
        mock_obs.ReqClient.return_value = mock_client
        
        with OBSCapture() as obs_cap:
            assert obs_cap.connected is True
            assert obs_cap.client == mock_client
        
        assert obs_cap.connected is False
        assert obs_cap.client is None


class TestRecordingStatus:
    def test_recording_status_creation(self):
        """RecordingStatus dataclass creates correctly."""
        status = RecordingStatus(
            active=True,
            bytes_written=1000000,
            duration_seconds=10.5,
            timecode="00:00:10.500"
        )
        assert status.active is True
        assert status.bytes_written == 1000000
        assert status.duration_seconds == 10.5
        assert status.timecode == "00:00:10.500"
