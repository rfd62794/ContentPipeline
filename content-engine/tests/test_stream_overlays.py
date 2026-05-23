"""
Tests for stream overlay functionality and commit counter.
Pure function tests only - no OBS, no YouTube, no filesystem writes.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from stream_launcher import (
    find_active_repo,
    count_commits_since,
    build_game_info_url,
    update_game_registry_entry,
    validate_stream_config
)


class TestCountCommitsSince:
    """Tests for count_commits_since function."""
    
    @patch('subprocess.run')
    def test_count_commits_since_valid(self, mock_run):
        """Mocked git output returns correct count."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="commit1\ncommit2\ncommit3\n"
        )
        result = count_commits_since("/fake/repo", datetime.now())
        assert result == 3
    
    @patch('subprocess.run')
    def test_count_commits_since_no_commits(self, mock_run):
        """Empty output returns 0."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=""
        )
        result = count_commits_since("/fake/repo", datetime.now())
        assert result == 0
    
    @patch('subprocess.run')
    def test_count_commits_since_git_error(self, mock_run):
        """subprocess error returns 0, no raise."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        result = count_commits_since("/fake/repo", datetime.now())
        assert result == 0
    
    @patch('subprocess.run')
    def test_count_commits_since_not_a_repo(self, mock_run):
        """Invalid path returns 0, no raise."""
        mock_run.return_value = MagicMock(returncode=128)
        result = count_commits_since("/not/a/repo", datetime.now())
        assert result == 0


class TestFindActiveRepo:
    """Tests for find_active_repo function."""
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.rglob')
    def test_find_active_repo_finds_most_recent(self, mock_rglob, mock_exists, mock_run):
        """Returns repo with most recent commit."""
        # Mock path exists
        mock_exists.return_value = True
        
        # Mock two repos with different timestamps
        mock_rglob.return_value = [
            Path("/fake/repo1/.git"),
            Path("/fake/repo2/.git")
        ]
        
        def side_effect(*args, **kwargs):
            cmd_args = args[0]
            if "repo1" in " ".join(cmd_args):
                return MagicMock(returncode=0, stdout="1000000")
            else:
                return MagicMock(returncode=0, stdout="2000000")
        
        mock_run.side_effect = side_effect
        result = find_active_repo("/fake")
        # Handle path separator differences between OS
        assert "repo2" in result
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.rglob')
    def test_find_active_repo_no_repos(self, mock_rglob, mock_exists, mock_run):
        """Empty search path returns None."""
        mock_exists.return_value = True
        mock_rglob.return_value = []
        result = find_active_repo("/empty")
        assert result is None
    
    @patch('pathlib.Path.exists')
    def test_find_active_repo_error(self, mock_exists):
        """Filesystem error returns None, no raise."""
        mock_exists.side_effect = PermissionError()
        result = find_active_repo("/restricted")
        assert result is None


class TestBuildGameInfoUrl:
    """Tests for build_game_info_url function."""
    
    def test_build_game_info_url_basic(self):
        """Returns valid file:// URL with params."""
        result = build_game_info_url(
            "/fake/path/game_info.html",
            "Dorfromantik",
            3,
            7
        )
        assert "file:///" in result
        assert "game=Dorfromantik" in result
        assert "session=3" in result
        assert "commits=7" in result
    
    def test_build_game_info_url_encodes_spaces(self):
        """Game name with spaces encoded correctly."""
        result = build_game_info_url(
            "/fake/path/game_info.html",
            "Scritchy Scratchy",
            1,
            5
        )
        assert "game=Scritchy%20Scratchy" in result
    
    def test_build_game_info_url_params_present(self):
        """game, session, commits all in URL."""
        result = build_game_info_url(
            "/fake/path/game_info.html",
            "TestGame",
            42,
            99
        )
        assert "game=TestGame" in result
        assert "session=42" in result
        assert "commits=99" in result


class TestSessionCountTracking:
    """Tests for session count in registry."""
    
    def test_session_count_increments(self):
        """session_count increments on each call."""
        registry = {"123": {"exe_name": "game.exe", "install_path": "/path", "session_count": 2}}
        updated = update_game_registry_entry(registry, 123, "game.exe", "/path", session_count=3)
        assert updated["123"]["session_count"] == 3
    
    def test_session_count_starts_at_one(self):
        """First stream is session 1, not 0."""
        registry = {}
        updated = update_game_registry_entry(registry, 123, "game.exe", "/path", session_count=1)
        assert updated["123"]["session_count"] == 1
    
    def test_session_count_preserves_other_fields(self):
        """session_count update preserves exe_name and install_path."""
        registry = {"123": {"exe_name": "game.exe", "install_path": "/path", "session_count": 1}}
        updated = update_game_registry_entry(registry, 123, "game.exe", "/path", session_count=2)
        assert updated["123"]["exe_name"] == "game.exe"
        assert updated["123"]["install_path"] == "/path"
    
    def test_session_count_default_zero(self):
        """session_count defaults to 0 when not specified."""
        registry = {}
        updated = update_game_registry_entry(registry, 123, "game.exe", "/path")
        assert updated["123"]["session_count"] == 0


class TestTestModes:
    """Tests for test mode validation."""
    
    def test_validate_test_mode_valid(self):
        """Valid test_mode values accepted."""
        config = {
            "game": "TestGame",
            "steam_appid": 123,
            "title": "Test",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic",
            "test_mode": "unlisted"
        }
        errors = validate_stream_config(config)
        assert len(errors) == 0
    
    def test_validate_test_mode_invalid(self):
        """Invalid test_mode returns error."""
        config = {
            "game": "TestGame",
            "steam_appid": 123,
            "title": "Test",
            "privacy": "public",
            "obs_scene": "Gaming",
            "obs_overlay_scene": "BRB",
            "obs_mic_source": "Mic",
            "test_mode": "invalid_mode"
        }
        errors = validate_stream_config(config)
        assert len(errors) > 0
        assert "test_mode" in str(errors)


class TestOverlayFiles:
    """Tests for overlay HTML files."""
    
    def test_overlay_html_files_exist(self):
        """All 4 HTML files present in overlays/."""
        overlays_dir = Path(__file__).parent.parent / "overlays"
        required_files = [
            "starting_soon.html",
            "brb.html",
            "game_info.html",
            "ending.html"
        ]
        for filename in required_files:
            assert (overlays_dir / filename).exists(), f"Missing {filename}"
    
    def test_overlay_html_no_external_deps(self):
        """No http:// or https:// in overlay HTML."""
        overlays_dir = Path(__file__).parent.parent / "overlays"
        html_files = list(overlays_dir.glob("*.html"))
        
        for html_file in html_files:
            content = html_file.read_text()
            # Check for external HTTP references (except file:// which is allowed)
            assert "http://" not in content, f"{html_file} contains http:// reference"
            assert "https://" not in content, f"{html_file} contains https:// reference"