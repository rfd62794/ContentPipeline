"""
Tests for stream_launcher.py — pure function tests only.

No network, no OBS, no Steam, no YouTube API calls.
Integration functions (start_stream, connect_obs, launch_game, etc.) are not tested here.
"""

import pytest
from pathlib import Path
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from stream_launcher import (
    load_stream_config,
    build_stream_title,
    build_youtube_stream_url,
    get_steam_launch_uri,
    validate_stream_config,
    find_stream_config,
    ensure_obs_running,
    get_active_window_title,
    is_game_focused,
    is_game_running,
)


class TestBuildStreamTitle:
    """Test build_stream_title function."""
    
    def test_build_stream_title_normal(self):
        config = {"title": "Chill Dorfromantik stream"}
        result = build_stream_title(config)
        assert result == "Chill Dorfromantik stream"
    
    def test_build_stream_title_truncates(self):
        config = {"title": "A" * 150}
        result = build_stream_title(config)
        assert len(result) == 100
        assert result == "A" * 100
    
    def test_build_stream_title_empty(self):
        config = {"title": ""}
        result = build_stream_title(config)
        assert result == ""
    
    def test_build_stream_title_missing(self):
        config = {}
        result = build_stream_title(config)
        assert result == ""


class TestBuildYoutubeUrl:
    """Test build_youtube_stream_url function."""
    
    def test_build_youtube_url(self):
        result = build_youtube_stream_url("@robertfloyddugger4516")
        assert result == "https://www.youtube.com/@robertfloyddugger4516/live"
    
    def test_build_youtube_url_different_handle(self):
        result = build_youtube_stream_url("@testchannel")
        assert result == "https://www.youtube.com/@testchannel/live"


class TestGetSteamUri:
    """Test get_steam_launch_uri function."""
    
    def test_get_steam_uri(self):
        result = get_steam_launch_uri(1455840)
        assert result == "steam://rungameid/1455840"
    
    def test_get_steam_uri_different_appid(self):
        result = get_steam_launch_uri(1092000)
        assert result == "steam://rungameid/1092000"
    
    def test_get_steam_uri_zero(self):
        result = get_steam_launch_uri(0)
        assert result == "steam://rungameid/0"


class TestValidateStreamConfig:
    """Test validate_stream_config function."""
    
    def test_validate_config_valid(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert errors == []
    
    def test_validate_missing_game(self):
        config = {
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "game" in errors[0].lower()
    
    def test_validate_invalid_privacy(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "invalid",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "privacy" in errors[0].lower()
    
    def test_validate_title_too_long(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "A" * 150,
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "title" in errors[0].lower()
    
    def test_validate_missing_scene(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "public",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "obs_scene" in errors[0].lower()
    
    def test_validate_missing_appid(self):
        config = {
            "game": "Dorfromantik",
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "steam_appid" in errors[0].lower()
    
    def test_validate_appid_not_int(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": "1455840",  # string instead of int
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "steam_appid" in errors[0].lower()
    
    def test_validate_multiple_errors(self):
        config = {
            "title": "A" * 150,
            "privacy": "invalid"
        }
        errors = validate_stream_config(config)
        assert len(errors) >= 2
    
    def test_validate_missing_overlay_scene(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_mic_source": "Mic/Aux",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "obs_overlay_scene" in errors[0].lower()
    
    def test_validate_missing_mic_source(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "game_process_name": "Dorfromantik.exe"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "obs_mic_source" in errors[0].lower()
    
    def test_validate_missing_process_name(self):
        config = {
            "game": "Dorfromantik",
            "steam_appid": 1455840,
            "title": "Test stream",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic/Aux"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 1
        assert "game_process_name" in errors[0].lower()


class TestFindStreamConfig:
    """Test find_stream_config function."""
    
    def test_find_config_exact_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            streams_dir = Path(tmpdir)
            config_file = streams_dir / "dorfromantik.yaml"
            config_file.write_text("game: Dorfromantik\nsteam_appid: 1455840")
            
            result = find_stream_config("Dorfromantik", streams_dir)
            assert result == config_file
    
    def test_find_config_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            streams_dir = Path(tmpdir)
            config_file = streams_dir / "Dorfromantik.yaml"
            config_file.write_text("game: Dorfromantik\nsteam_appid: 1455840")
            
            result = find_stream_config("dorfromantik", streams_dir)
            assert result == config_file
    
    def test_find_config_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            streams_dir = Path(tmpdir)
            config_file = streams_dir / "dorfromantik.yaml"
            config_file.write_text("game: Dorfromantik\nsteam_appid: 1455840")
            
            result = find_stream_config("UnknownGame", streams_dir)
            assert result is None
    
    def test_find_config_by_game_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            streams_dir = Path(tmpdir)
            config_file = streams_dir / "different_name.yaml"
            config_file.write_text("game: Dorfromantik\nsteam_appid: 1455840")
            
            result = find_stream_config("Dorfromantik", streams_dir)
            assert result == config_file


class TestLoadStreamConfig:
    """Test load_stream_config function."""
    
    def test_load_stream_config_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("game: TestGame\nsteam_appid: 123456")
            
            result = load_stream_config(config_file)
            assert result == {"game": "TestGame", "steam_appid": 123456}
    
    def test_load_stream_config_with_all_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            yaml_content = """
game: TestGame
steam_appid: 123456
title: Test Title
description: Test Description
category: Gaming
privacy: public
obs_scene: Gaming
tags:
  - test
  - gaming
"""
            config_file.write_text(yaml_content)
            
            result = load_stream_config(config_file)
            assert result["game"] == "TestGame"
            assert result["steam_appid"] == 123456
            assert result["title"] == "Test Title"
            assert result["privacy"] == "public"
            assert result["obs_scene"] == "Gaming"
            assert result["tags"] == ["test", "gaming"]


class TestEnsureObsRunning:
    """Test ensure_obs_running function."""
    
    def test_ensure_obs_not_running(self):
        """Test ensure_obs_running returns False when OBS executable not found."""
        with patch('stream_launcher.psutil.process_iter') as mock_process_iter:
            # Mock OBS not running
            mock_process_iter.return_value = []
            
            with patch('stream_launcher.Path') as mock_path:
                # Mock OBS executable path not found
                mock_path.return_value.exists.return_value = False
                
                result = ensure_obs_running()
                assert result is False
    
    def test_ensure_obs_already_running(self):
        """Test ensure_obs_running returns True when OBS is already running."""
        with patch('stream_launcher.psutil.process_iter') as mock_process_iter:
            # Mock OBS already running
            mock_process_iter.return_value = [MagicMock(info={'name': 'obs64.exe'})]
            
            result = ensure_obs_running()
            assert result is True


class TestGetActiveWindowTitle:
    """Test get_active_window_title function."""
    
    def test_get_active_window_title_mock(self):
        """Test get_active_window_title with mocked win32gui."""
        with patch('stream_launcher.win32gui') as mock_win32gui:
            mock_win32gui.GetForegroundWindow.return_value = 12345
            mock_win32gui.GetWindowText.return_value = "Dorfromantik"
            
            result = get_active_window_title()
            assert result == "Dorfromantik"
    
    def test_get_active_window_title_no_win32gui(self):
        """Test get_active_window_title returns empty string when win32gui is None."""
        with patch('stream_launcher.win32gui', None):
            result = get_active_window_title()
            assert result == ""
    
    def test_get_active_window_title_exception(self):
        """Test get_active_window_title returns empty string on exception."""
        with patch('stream_launcher.win32gui') as mock_win32gui:
            mock_win32gui.GetForegroundWindow.side_effect = Exception("Error")
            
            result = get_active_window_title()
            assert result == ""


class TestIsGameFocused:
    """Test is_game_focused function."""
    
    def test_is_game_focused_match(self):
        """Test is_game_focused returns True when game name is in window title."""
        window_title = "Dorfromantik - Main Menu"
        game_name = "Dorfromantik"
        result = is_game_focused(window_title, game_name)
        assert result is True
    
    def test_is_game_focused_no_match(self):
        """Test is_game_focused returns False when game name is not in window title."""
        window_title = "Chrome - YouTube"
        game_name = "Dorfromantik"
        result = is_game_focused(window_title, game_name)
        assert result is False
    
    def test_is_game_focused_case_insensitive(self):
        """Test is_game_focused is case-insensitive."""
        window_title = "DORFROMANTIK - Main Menu"
        game_name = "dorfromantik"
        result = is_game_focused(window_title, game_name)
        assert result is True
    
    def test_is_game_focused_empty_title(self):
        """Test is_game_focused returns False for empty window title."""
        window_title = ""
        game_name = "Dorfromantik"
        result = is_game_focused(window_title, game_name)
        assert result is False


class TestIsGameRunning:
    """Test is_game_running function."""
    
    def test_is_game_running_mock(self):
        """Test is_game_running with mocked psutil."""
        with patch('stream_launcher.psutil.process_iter') as mock_process_iter:
            # Mock game process running
            mock_process = MagicMock()
            mock_process.info = {'name': 'Dorfromantik.exe'}
            mock_process_iter.return_value = [mock_process]
            
            result = is_game_running("Dorfromantik.exe")
            assert result is True
    
    def test_is_game_running_not_found(self):
        """Test is_game_running returns False when process not found."""
        with patch('stream_launcher.psutil.process_iter') as mock_process_iter:
            # Mock no matching process
            mock_process_iter.return_value = []
            
            result = is_game_running("Dorfromantik.exe")
            assert result is False
    
    def test_is_game_running_case_insensitive(self):
        """Test is_game_running is case-insensitive."""
        with patch('stream_launcher.psutil.process_iter') as mock_process_iter:
            # Mock game process with different case
            mock_process = MagicMock()
            mock_process.info = {'name': 'dorfromantik.exe'}
            mock_process_iter.return_value = [mock_process]
            
            result = is_game_running("Dorfromantik.exe")
            assert result is True