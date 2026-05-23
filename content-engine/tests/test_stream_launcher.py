"""
Tests for stream_launcher.py — pure function tests only.

No network, no OBS, no Steam, no YouTube API calls.
Integration functions (start_stream, connect_obs, launch_game, etc.) are not tested here.
"""

import pytest
from pathlib import Path
import tempfile
import yaml
import json
import os
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
    find_game_exe,
    load_game_registry,
    save_game_registry,
    update_game_registry_entry,
    get_exe_from_registry,
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
        """Test validate_config does not require game_process_name (optional field)."""
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
        # game_process_name is optional, so should not have errors
        assert len(errors) == 0


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


class TestFindGameExe:
    """Test find_game_exe function."""
    
    def test_find_game_exe_returns_largest_exe(self):
        """Test find_game_exe returns the largest .exe file from install directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock Steam install structure
            steam_path = Path(tmpdir)
            common_dir = steam_path / "steamapps" / "common" / "Dorfromantik"
            common_dir.mkdir(parents=True)
            
            # Create mock exe files with different sizes
            small_exe = common_dir / "small.exe"
            small_exe.write_bytes(b"x" * 1000)
            
            medium_exe = common_dir / "medium.exe"
            medium_exe.write_bytes(b"x" * 5000)
            
            large_exe = common_dir / "Dorfromantik.exe"
            large_exe.write_bytes(b"x" * 10000)
            
            # Mock SteamLibrary to return game info
            with patch('steam_library.SteamLibrary') as mock_steam_lib_class:
                mock_game_info = MagicMock()
                mock_game_info.installdir = "Dorfromantik"
                mock_game_info.appid = 1455840
                
                mock_steam_instance = MagicMock()
                mock_steam_instance.get_installed_games.return_value = [mock_game_info]
                mock_steam_lib_class.return_value = mock_steam_instance
                
                result = find_game_exe(1455840, steam_path)
                
                # Should return the largest exe
                assert result == "Dorfromantik.exe"
    
    def test_find_game_exe_no_exe_files(self):
        """Test find_game_exe returns None when no exe files found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            steam_path = Path(tmpdir)
            common_dir = steam_path / "steamapps" / "common" / "Dorfromantik"
            common_dir.mkdir(parents=True)
            
            # Don't create any exe files
            
            with patch('steam_library.SteamLibrary') as mock_steam_lib:
                mock_game_info = MagicMock()
                mock_game_info.installdir = "Dorfromantik"
                mock_steam_instance = MagicMock()
                mock_steam_instance.get_installed_games.return_value = [mock_game_info]
                mock_steam_lib.return_value = mock_steam_instance
                
                result = find_game_exe(1455840, steam_path)
                
                assert result is None
    
    def test_find_game_exe_installdir_not_found(self):
        """Test find_game_exe returns None when installdir not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            steam_path = Path(tmpdir)
            
            with patch('steam_library.SteamLibrary') as mock_steam_lib:
                # Mock game info without installdir
                mock_game_info = MagicMock()
                mock_game_info.installdir = None
                mock_steam_instance = MagicMock()
                mock_steam_instance.get_installed_games.return_value = [mock_game_info]
                mock_steam_lib.return_value = mock_steam_instance
                
                result = find_game_exe(1455840, steam_path)
                
                assert result is None


class TestGameRegistry:
    """Test game registry functions."""
    
    def test_load_registry_missing_file(self):
        """Test load_game_registry returns empty dict when file missing."""
        with patch('stream_launcher.Path') as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            
            result = load_game_registry()
            assert result == {}
    
    def test_load_registry_existing(self):
        """Test load_game_registry loads existing registry."""
        test_data = {"1455840": {"exe_name": "Dorfromantik.exe", "install_path": "/path", "last_seen": "2026-05-23"}}
        
        # Test by mocking json.load directly
        with patch('stream_launcher.json.load', return_value=test_data):
            with patch('stream_launcher.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                
                result = load_game_registry()
                assert result == test_data
    
    def test_save_registry_writes_json(self):
        """Test save_game_registry writes JSON file."""
        test_data = {"1455840": {"exe_name": "Dorfromantik.exe"}}
        
        # Test by mocking json.dump directly
        with patch('stream_launcher.json.dump') as mock_dump:
            with patch('stream_launcher.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_temp_instance = MagicMock()
                mock_path_instance.with_suffix.return_value = mock_temp_instance
                mock_path.return_value = mock_path_instance
                
                save_game_registry(test_data)
            
            # Verify json.dump was called with test_data
            mock_dump.assert_called_once()
            assert mock_dump.call_args[0][0] == test_data
    
    def test_registry_entry_persists_across_calls(self):
        """Test registry entry persists across multiple calls."""
        registry = {}
        
        # First call adds entry
        updated = update_game_registry_entry(registry, 1455840, "Dorfromantik.exe", "/path")
        assert "1455840" in updated
        
        # Second call updates entry
        updated2 = update_game_registry_entry(updated, 1455840, "Dorfromantik.exe", "/newpath")
        assert updated2["1455840"]["install_path"] == "/newpath"
        
        # Original registry should not be mutated
        assert "1455840" not in registry
    
    def test_registry_handles_multiple_games(self):
        """Test registry handles multiple game entries."""
        registry = {}
        
        # Add multiple games
        registry = update_game_registry_entry(registry, 1455840, "Dorfromantik.exe", "/path1")
        registry = update_game_registry_entry(registry, 1092000, "Stacklands.exe", "/path2")
        registry = update_game_registry_entry(registry, 1462210, "Scritchy Scratchy.exe", "/path3")
        
        # Verify all entries exist
        assert len(registry) == 3
        assert get_exe_from_registry(registry, 1455840) == "Dorfromantik.exe"
        assert get_exe_from_registry(registry, 1092000) == "Stacklands.exe"
        assert get_exe_from_registry(registry, 1462210) == "Scritchy Scratchy.exe"
    
    def test_registry_timestamp_format(self):
        """Test registry timestamp is in ISO format."""
        registry = {}
        result = update_game_registry_entry(registry, 1455840, "Dorfromantik.exe", "/path")
        
        timestamp = result["1455840"]["last_seen"]
        # ISO format should have T and colons
        assert "T" in timestamp
        assert ":" in timestamp
        # Should be parseable as datetime
        from datetime import datetime
        datetime.fromisoformat(timestamp)
    
    def test_update_entry_new_appid(self):
        """Test update_game_registry_entry adds new appid."""
        registry = {}
        result = update_game_registry_entry(registry, 1455840, "Dorfromantik.exe", "/path")
        
        assert "1455840" in result
        assert result["1455840"]["exe_name"] == "Dorfromantik.exe"
        assert result["1455840"]["install_path"] == "/path"
        assert "last_seen" in result["1455840"]
        # Original registry should not be mutated
        assert "1455840" not in registry
    
    def test_update_entry_existing_appid(self):
        """Test update_game_registry_entry updates existing appid."""
        registry = {
            "1455840": {"exe_name": "Old.exe", "install_path": "/oldpath", "last_seen": "2026-01-01"}
        }
        result = update_game_registry_entry(registry, 1455840, "New.exe", "/newpath")
        
        assert result["1455840"]["exe_name"] == "New.exe"
        assert result["1455840"]["install_path"] == "/newpath"
        assert result["1455840"]["last_seen"] != "2026-01-01"
        # Original registry should not be mutated
        assert registry["1455840"]["exe_name"] == "Old.exe"
    
    def test_update_entry_no_mutation(self):
        """Test update_game_registry_entry does not mutate input dict."""
        registry = {"1455840": {"exe_name": "Old.exe"}}
        original_registry = json.loads(json.dumps(registry))
        
        update_game_registry_entry(registry, 1455840, "New.exe", "/path")
        
        assert registry == original_registry
    
    def test_get_exe_found(self):
        """Test get_exe_from_registry returns exe_name when found."""
        registry = {
            "1455840": {"exe_name": "Dorfromantik.exe", "install_path": "/path"}
        }
        result = get_exe_from_registry(registry, 1455840)
        assert result == "Dorfromantik.exe"
    
    def test_get_exe_not_found(self):
        """Test get_exe_from_registry returns None when appid not found."""
        registry = {
            "1455840": {"exe_name": "Dorfromantik.exe"}
        }
        result = get_exe_from_registry(registry, 999999)
        assert result is None
    
    def test_update_sets_last_seen_timestamp(self):
        """Test update_game_registry_entry sets ISO datetime timestamp."""
        registry = {}
        result = update_game_registry_entry(registry, 1455840, "Dorfromantik.exe", "/path")
        
        last_seen = result["1455840"]["last_seen"]
        # Should be ISO format datetime
        assert "T" in last_seen
        assert ":" in last_seen
    
    def test_find_game_exe_uses_registry_first(self):
        """Test find_game_exe uses registry entry when available and valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock install directory with exe
            install_dir = Path(tmpdir) / "steamapps" / "common" / "Dorfromantik"
            install_dir.mkdir(parents=True)
            exe_file = install_dir / "Dorfromantik.exe"
            exe_file.write_bytes(b"x" * 1000)
            
            # Create registry with entry
            registry = {
                "1455840": {
                    "exe_name": "Dorfromantik.exe",
                    "install_path": str(install_dir),
                    "last_seen": "2026-05-23T15:30:00"
                }
            }
            
            with patch('stream_launcher.load_game_registry') as mock_load:
                mock_load.return_value = registry
                with patch('stream_launcher.save_game_registry') as mock_save:
                    with patch('stream_launcher.update_game_registry_entry') as mock_update:
                        mock_update.return_value = registry
                        
                        result = find_game_exe(1455840, Path(tmpdir))
                        
                        assert result == "Dorfromantik.exe"
                        # Should have called save to update last_seen
                        mock_save.assert_called_once()
    
    def test_find_game_exe_registry_miss_falls_through_to_scan(self):
        """Test find_game_exe falls through to scan when registry entry missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock install structure
            steam_path = Path(tmpdir)
            common_dir = steam_path / "steamapps" / "common" / "Dorfromantik"
            common_dir.mkdir(parents=True)
            
            large_exe = common_dir / "Dorfromantik.exe"
            large_exe.write_bytes(b"x" * 10000)
            
            # Empty registry
            registry = {}
            
            with patch('stream_launcher.load_game_registry') as mock_load:
                mock_load.return_value = registry
                with patch('stream_launcher.save_game_registry') as mock_save:
                    with patch('steam_library.SteamLibrary') as mock_steam_lib:
                        mock_game_info = MagicMock()
                        mock_game_info.installdir = "Dorfromantik"
                        mock_game_info.appid = 1455840
                        
                        mock_steam_instance = MagicMock()
                        mock_steam_instance.get_installed_games.return_value = [mock_game_info]
                        mock_steam_lib.return_value = mock_steam_instance
                        
                        result = find_game_exe(1455840, steam_path)
                        
                        assert result == "Dorfromantik.exe"
                        # Should have saved new registry entry
                        mock_save.assert_called_once()
    
    def test_find_game_exe_updates_registry_after_scan(self):
        """Test find_game_exe updates registry after successful scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            steam_path = Path(tmpdir)
            common_dir = steam_path / "steamapps" / "common" / "Dorfromantik"
            common_dir.mkdir(parents=True)
            
            large_exe = common_dir / "Dorfromantik.exe"
            large_exe.write_bytes(b"x" * 10000)
            
            registry = {}
            
            with patch('stream_launcher.load_game_registry') as mock_load:
                mock_load.return_value = registry
                with patch('stream_launcher.save_game_registry') as mock_save:
                    with patch('steam_library.SteamLibrary') as mock_steam_lib:
                        mock_game_info = MagicMock()
                        mock_game_info.installdir = "Dorfromantik"
                        mock_game_info.appid = 1455840
                        
                        mock_steam_instance = MagicMock()
                        mock_steam_instance.get_installed_games.return_value = [mock_game_info]
                        mock_steam_lib.return_value = mock_steam_instance
                        
                        result = find_game_exe(1455840, steam_path)
                        
                        # Verify save was called with updated registry
                        assert mock_save.called
                        saved_registry = mock_save.call_args[0][0]
                        assert "1455840" in saved_registry
                        assert saved_registry["1455840"]["exe_name"] == "Dorfromantik.exe"
    
    def test_find_game_exe_validates_exe_exists(self):
        """Test find_game_exe validates exe exists before using registry entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create registry entry pointing to non-existent exe
            install_dir = Path(tmpdir) / "steamapps" / "common" / "Dorfromantik"
            install_dir.mkdir(parents=True)
            # Don't create the exe file initially
            
            registry = {
                "1455840": {
                    "exe_name": "Dorfromantik.exe",
                    "install_path": str(install_dir),
                    "last_seen": "2026-05-23T15:30:00"
                }
            }
            
            with patch('stream_launcher.load_game_registry') as mock_load:
                mock_load.return_value = registry
                with patch('stream_launcher.save_game_registry') as mock_save:
                    with patch('steam_library.SteamLibrary') as mock_steam_lib:
                        # Mock scan to find exe
                        mock_game_info = MagicMock()
                        mock_game_info.installdir = "Dorfromantik"
                        mock_game_info.appid = 1455840
                        
                        mock_steam_instance = MagicMock()
                        mock_steam_instance.get_installed_games.return_value = [mock_game_info]
                        mock_steam_lib.return_value = mock_steam_instance
                        
                        # Create exe during scan (simulate finding it)
                        exe_file = install_dir / "Dorfromantik.exe"
                        exe_file.write_bytes(b"x" * 10000)
                        
                        result = find_game_exe(1455840, Path(tmpdir))
                        
                        # Should have fallen through to scan and found exe
                        assert result == "Dorfromantik.exe"