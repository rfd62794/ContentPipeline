"""
Tests for Steam Library Detection System

All tests use pure functions with mocked file I/O and HTTP calls.
No actual Steam installation or API calls required.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from steam_library import (
    parse_acf_file,
    parse_acf_files,
    get_installed_games,
    SteamWebAPI,
    SteamWebAPIError,
    SteamLibrary,
    GameInfo,
    print_library_table
)


# =============================================================================
# ACF Parser Tests (Pure Functions)
# =============================================================================

class TestParseACFFile:
    """Tests for parse_acf_file pure function."""
    
    def test_parse_simple_acf(self):
        """Test parsing a simple ACF file with key-value pairs."""
        content = '''
"AppState"
{
    "appid"        "12345"
    "name"         "Test Game"
    "installdir"   "TestGame"
}
'''
        result = parse_acf_file(content)
        assert result['appid'] == '12345'
        assert result['name'] == 'Test Game'
        assert result['installdir'] == 'TestGame'
    
    def test_parse_acf_with_nested_sections(self):
        """Test parsing ACF with nested sections."""
        content = '''
"AppState"
{
    "appid" "12345"
    "StateFlags"
    {
        "UpdateResult" "0"
        "Finished" "1"
    }
}
'''
        result = parse_acf_file(content)
        assert result['appid'] == '12345'
        # Nested sections should be merged
        assert 'UpdateResult' in result or 'StateFlags' in result
    
    def test_parse_acf_empty_content(self):
        """Test parsing empty content returns empty dict."""
        assert parse_acf_file("") == {}
        assert parse_acf_file(None) == {}
    
    def test_parse_acf_with_comments(self):
        """Test that comments are ignored."""
        content = '''
"AppState"
{
    // This is a comment
    "appid" "12345"
    "name" "Test Game"
}
'''
        result = parse_acf_file(content)
        assert result['appid'] == '12345'
        assert result['name'] == 'Test Game'
    
    def test_parse_acf_with_quotes_in_values(self):
        """Test handling of quoted values."""
        content = '''
"AppState"
{
    "name" "Game with spaces"
    "installdir" "Path With Spaces"
}
'''
        result = parse_acf_file(content)
        assert result['name'] == 'Game with spaces'
        assert result['installdir'] == 'Path With Spaces'
    
    def test_parse_acf_malformed_line(self):
        """Test that malformed lines are skipped gracefully."""
        content = '''
"AppState"
{
    "appid" "12345"
    invalid line without quotes
    "name" "Test Game"
}
'''
        result = parse_acf_file(content)
        assert result['appid'] == '12345'
        assert result['name'] == 'Test Game'


class TestParseACFFiles:
    """Tests for parse_acf_files with mocked file I/O."""
    
    @patch('steam_library.Path')
    def test_parse_acf_files_from_directory(self, mock_path):
        """Test parsing multiple ACF files from a directory."""
        # Mock directory structure
        mock_dir = MagicMock()
        mock_path.return_value = mock_dir
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        
        # Mock ACF files
        mock_file1 = MagicMock()
        mock_file1.name = 'appmanifest_12345.acf'
        mock_file1.read_text.return_value = '''
"AppState"
{
    "appid" "12345"
    "name" "Game One"
}
'''
        
        mock_file2 = MagicMock()
        mock_file2.name = 'appmanifest_67890.acf'
        mock_file2.read_text.return_value = '''
"AppState"
{
    "appid" "67890"
    "name" "Game Two"
}
'''
        
        mock_dir.glob.return_value = [mock_file1, mock_file2]
        
        results = parse_acf_files(mock_dir)
        
        assert len(results) == 2
        assert results[0]['appid'] == '12345'
        assert results[1]['appid'] == '67890'
    
    @patch('steam_library.Path')
    def test_parse_acf_files_nonexistent_directory(self, mock_path):
        """Test handling of non-existent directory."""
        mock_dir = MagicMock()
        mock_path.return_value = mock_dir
        mock_dir.exists.return_value = False
        
        results = parse_acf_files(mock_dir)
        assert results == []
    
    @patch('steam_library.Path')
    def test_parse_acf_files_read_error(self, mock_path):
        """Test handling of file read errors."""
        mock_dir = MagicMock()
        mock_path.return_value = mock_dir
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        
        mock_file = MagicMock()
        mock_file.read_text.side_effect = IOError("Permission denied")
        mock_dir.glob.return_value = [mock_file]
        
        results = parse_acf_files(mock_dir)
        assert results == []


class TestGetInstalledGames:
    """Tests for get_installed_games with mocked file I/O."""
    
    @patch('steam_library.parse_acf_files')
    @patch('steam_library.Path')
    def test_get_installed_games_success(self, mock_path, mock_parse):
        """Test successful retrieval of installed games."""
        mock_parse.return_value = [
            {'appid': '12345', 'name': 'Game One', 'installdir': 'GameOne'},
            {'appid': '67890', 'name': 'Game Two', 'installdir': 'GameTwo'},
        ]
        
        games = get_installed_games()
        
        assert len(games) == 2
        assert games[0]['appid'] == 12345
        assert games[0]['name'] == 'Game One'
        assert games[0]['installdir'] == 'GameOne'
    
    @patch('steam_library.parse_acf_files')
    def test_get_installed_games_invalid_appid(self, mock_parse):
        """Test handling of invalid appid."""
        mock_parse.return_value = [
            {'appid': 'invalid', 'name': 'Bad Game', 'installdir': 'BadGame'},
        ]
        
        games = get_installed_games()
        assert len(games) == 0
    
    @patch('steam_library.parse_acf_files')
    def test_get_installed_games_missing_fields(self, mock_parse):
        """Test handling of missing fields."""
        mock_parse.return_value = [
            {'appid': '12345'},  # Missing name and installdir
        ]
        
        games = get_installed_games()
        assert len(games) == 1
        assert games[0]['appid'] == 12345
        assert games[0]['name'] == 'Unknown'
        assert games[0]['installdir'] == ''


# =============================================================================
# Steam Web API Client Tests
# =============================================================================

class TestSteamWebAPI:
    """Tests for SteamWebAPI with mocked HTTP calls."""
    
    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch.dict('os.environ', {
            'STEAM_API_KEY': 'test_key',
            'STEAM_ID': '76561198000000000'
        }):
            api = SteamWebAPI()
            assert api.api_key == 'test_key'
            assert api.steam_id == '76561198000000000'
    
    def test_init_with_params(self):
        """Test initialization with parameters."""
        api = SteamWebAPI(api_key='param_key', steam_id='param_id')
        assert api.api_key == 'param_key'
        assert api.steam_id == 'param_id'
    
    def test_init_missing_api_key(self):
        """Test error when API key is missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SteamWebAPIError, match="STEAM_API_KEY"):
                SteamWebAPI()
    
    def test_init_missing_steam_id(self):
        """Test error when Steam ID is missing."""
        with patch.dict('os.environ', {'STEAM_API_KEY': 'test_key'}, clear=True):
            with pytest.raises(SteamWebAPIError, match="STEAM_ID"):
                SteamWebAPI()
    
    @patch('steam_library.requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': {'games': []}}
        mock_get.return_value = mock_response
        
        api = SteamWebAPI(api_key='test_key', steam_id='test_id')
        result = api._make_request('/test/', {})
        
        assert result == {'response': {'games': []}}
        mock_get.assert_called_once()
    
    @patch('steam_library.requests.get')
    def test_make_request_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        from requests import RequestException
        mock_get.side_effect = RequestException("Connection error")
        
        api = SteamWebAPI(api_key='test_key', steam_id='test_id')
        with pytest.raises(SteamWebAPIError, match="Request failed"):
            api._make_request('/test/', {})
    
    @patch('steam_library.requests.get')
    def test_make_request_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        api = SteamWebAPI(api_key='test_key', steam_id='test_id')
        with pytest.raises(SteamWebAPIError, match="Invalid JSON"):
            api._make_request('/test/', {})
    
    @patch('steam_library.requests.get')
    def test_get_owned_games(self, mock_get):
        """Test GetOwnedGames API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': {
                'games': [
                    {'appid': 12345, 'name': 'Game One', 'playtime_forever': 120},
                    {'appid': 67890, 'name': 'Game Two', 'playtime_forever': 0},
                ]
            }
        }
        mock_get.return_value = mock_response
        
        api = SteamWebAPI(api_key='test_key', steam_id='test_id')
        games = api.get_owned_games()
        
        assert len(games) == 2
        assert games[0]['appid'] == 12345
        assert games[0]['name'] == 'Game One'
        assert games[0]['playtime_forever'] == 120
        assert games[1]['playtime_forever'] == 0
    
    @patch('steam_library.requests.get')
    def test_get_owned_games_with_free_games(self, mock_get):
        """Test GetOwnedGames with free games option."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': {
                'games': [
                    {'appid': 12345, 'name': 'Free Game', 'playtime_forever': 30},
                ]
            }
        }
        mock_get.return_value = mock_response
        
        api = SteamWebAPI(api_key='test_key', steam_id='test_id')
        games = api.get_owned_games(include_played_free_games=True)
        
        assert len(games) == 1
        # Verify the parameter was passed
        call_args = mock_get.call_args
        assert call_args[1]['params']['include_played_free_games'] == 1
    
    @patch('steam_library.requests.get')
    def test_get_recently_played_games(self, mock_get):
        """Test GetRecentlyPlayedGames API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': {
                'games': [
                    {
                        'appid': 12345,
                        'name': 'Recent Game',
                        'playtime_2weeks': 60,
                        'playtime_forever': 300
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        api = SteamWebAPI(api_key='test_key', steam_id='test_id')
        games = api.get_recently_played_games(count=5)
        
        assert len(games) == 1
        assert games[0]['appid'] == 12345
        assert games[0]['playtime_2weeks'] == 60
        assert games[0]['playtime_forever'] == 300
        # Verify count parameter
        call_args = mock_get.call_args
        assert call_args[1]['params']['count'] == 5


# =============================================================================
# SteamLibrary Class Tests
# =============================================================================

class TestSteamLibrary:
    """Tests for SteamLibrary merging logic."""
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_library_merge(self, mock_api_class, mock_get_installed):
        """Test merging local and web data."""
        # Mock local games
        mock_get_installed.return_value = [
            {'appid': 12345, 'name': 'Local Game', 'installdir': 'LocalGame'},
        ]
        
        # Mock web API
        mock_api = MagicMock()
        mock_api.get_owned_games.return_value = [
            {'appid': 12345, 'name': 'Web Game Name', 'playtime_forever': 120},
            {'appid': 67890, 'name': 'Web Only Game', 'playtime_forever': 0},
        ]
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_library()
        
        assert len(games) == 2
        
        # Game 12345: merged data
        game1 = next(g for g in games if g.appid == 12345)
        assert game1.installed is True
        assert game1.name == 'Web Game Name'  # Prefer web name
        assert game1.installdir == 'LocalGame'
        assert game1.playtime_hours == 2.0  # 120 minutes = 2 hours
        
        # Game 67890: web only
        game2 = next(g for g in games if g.appid == 67890)
        assert game2.installed is False
        assert game2.name == 'Web Only Game'
        assert game2.installdir is None
        assert game2.playtime_hours == 0.0
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_library_web_api_error(self, mock_api_class, mock_get_installed):
        """Test handling of Web API errors."""
        mock_get_installed.return_value = [
            {'appid': 12345, 'name': 'Local Game', 'installdir': 'LocalGame'},
        ]
        
        # Mock API error
        mock_api_class.side_effect = SteamWebAPIError("API unavailable")
        
        library = SteamLibrary()
        games = library.get_library()
        
        # Should still return local games
        assert len(games) == 1
        assert games[0].installed is True
        assert games[0].name == 'Local Game'
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_library_no_local_games(self, mock_api_class, mock_get_installed):
        """Test with no local games installed."""
        mock_get_installed.return_value = []
        
        mock_api = MagicMock()
        mock_api.get_owned_games.return_value = [
            {'appid': 12345, 'name': 'Web Game', 'playtime_forever': 60},
        ]
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_library()
        
        assert len(games) == 1
        assert games[0].installed is False
        assert games[0].playtime_hours == 1.0
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_library_no_web_games(self, mock_api_class, mock_get_installed):
        """Test with no web games (API error)."""
        mock_get_installed.return_value = [
            {'appid': 12345, 'name': 'Local Game', 'installdir': 'LocalGame'},
        ]
        
        mock_api = MagicMock()
        mock_api.get_owned_games.side_effect = SteamWebAPIError("API error")
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_library()
        
        assert len(games) == 1
        assert games[0].installed is True
        assert games[0].playtime_hours == 0.0
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_installed_only(self, mock_api_class, mock_get_installed):
        """Test get_installed_only method."""
        mock_get_installed.return_value = [
            {'appid': 12345, 'name': 'Installed Game', 'installdir': 'Game1'},
        ]
        
        mock_api = MagicMock()
        mock_api.get_owned_games.return_value = [
            {'appid': 12345, 'name': 'Game 1', 'playtime_forever': 60},
            {'appid': 67890, 'name': 'Game 2', 'playtime_forever': 0},
        ]
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_installed_only()
        
        assert len(games) == 1
        assert games[0].installed is True
        assert games[0].appid == 12345
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_recently_played(self, mock_api_class, mock_get_installed):
        """Test get_recently_played method."""
        mock_get_installed.return_value = [
            {'appid': 12345, 'name': 'Local Game', 'installdir': 'Game1'},
        ]
        
        mock_api = MagicMock()
        mock_api.get_recently_played_games.return_value = [
            {
                'appid': 12345,
                'name': 'Recent Game',
                'playtime_2weeks': 60,
                'playtime_forever': 300
            }
        ]
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_recently_played(count=5)
        
        assert len(games) == 1
        assert games[0].installed is True
        assert games[0].playtime_hours == 5.0  # 300 minutes
        mock_api.get_recently_played_games.assert_called_once_with(5)
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_recently_played_api_error(self, mock_api_class, mock_get_installed):
        """Test get_recently_played with API error."""
        mock_api = MagicMock()
        mock_api.get_recently_played_games.side_effect = SteamWebAPIError("API error")
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_recently_played()
        
        assert games == []
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_get_library_sorted_by_name(self, mock_api_class, mock_get_installed):
        """Test that library is sorted by name."""
        mock_get_installed.return_value = []
        
        mock_api = MagicMock()
        mock_api.get_owned_games.return_value = [
            {'appid': 3, 'name': 'Zelda', 'playtime_forever': 0},
            {'appid': 1, 'name': 'Alpha', 'playtime_forever': 0},
            {'appid': 2, 'name': 'Beta', 'playtime_forever': 0},
        ]
        mock_api_class.return_value = mock_api
        
        library = SteamLibrary()
        games = library.get_library()
        
        assert games[0].name == 'Alpha'
        assert games[1].name == 'Beta'
        assert games[2].name == 'Zelda'


# =============================================================================
# CLI Tests
# =============================================================================

class TestPrintLibraryTable:
    """Tests for print_library_table CLI function."""
    
    def test_print_empty_library(self, capsys):
        """Test printing empty library."""
        print_library_table([])
        captured = capsys.readouterr()
        assert "No games found" in captured.out
    
    def test_print_library_with_games(self, capsys):
        """Test printing library with games."""
        games = [
            GameInfo(appid=12345, name='Game One', installdir='Game1', installed=True, playtime_hours=2.5),
            GameInfo(appid=67890, name='Game Two', installdir=None, installed=False, playtime_hours=0.0),
        ]
        
        print_library_table(games)
        captured = capsys.readouterr()
        
        assert 'Game One' in captured.out
        assert 'Game Two' in captured.out
        assert '[INSTALLED]' in captured.out
        assert '2.5' in captured.out
        assert 'Total games: 2' in captured.out
        assert 'Installed: 1' in captured.out
    
    def test_print_library_long_name_truncated(self, capsys):
        """Test that long names are truncated."""
        games = [
            GameInfo(appid=1, name='A' * 100, installdir='Game', installed=True, playtime_hours=1.0),
        ]
        
        print_library_table(games)
        captured = capsys.readouterr()
        
        # Name should be truncated to fit table
        assert len(captured.out.split('\n')[2].split()[2]) <= 50


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @patch('steam_library.get_installed_games')
    @patch('steam_library.SteamWebAPI')
    def test_full_workflow(self, mock_api_class, mock_get_installed):
        """Test complete workflow from both sources."""
        # Setup local data
        mock_get_installed.return_value = [
            {'appid': 12345, 'name': 'Local Name', 'installdir': 'LocalDir'},
        ]
        
        # Setup web data
        mock_api = MagicMock()
        mock_api.get_owned_games.return_value = [
            {'appid': 12345, 'name': 'Web Name', 'playtime_forever': 180},
            {'appid': 67890, 'name': 'Web Only', 'playtime_forever': 0},
        ]
        mock_api_class.return_value = mock_api
        
        # Run workflow
        library = SteamLibrary()
        games = library.get_library()
        
        # Verify merged results
        assert len(games) == 2
        
        # Verify game 12345 is properly merged
        merged_game = next(g for g in games if g.appid == 12345)
        assert merged_game.installed is True
        assert merged_game.name == 'Web Name'  # Web name preferred
        assert merged_game.installdir == 'LocalDir'  # Local installdir
        assert merged_game.playtime_hours == 3.0  # 180 minutes
        
        # Verify game 67890 is web-only
        web_only = next(g for g in games if g.appid == 67890)
        assert web_only.installed is False
        assert web_only.installdir is None
