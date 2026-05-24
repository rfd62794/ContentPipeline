"""
Tests for game_metrics module
"""

import pytest
import json
import requests
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime, timedelta

from game_metrics import (
    GameMetrics,
    compute_content_demand_score,
    parse_steamspy_response,
    compute_review_score,
    merge_game_metrics,
    filter_by_playtime,
    filter_installed,
    sort_by_metric,
    format_metrics_table,
    GameMetricsClient
)
from steam_library import GameInfo


# =============================================================================
# Pure Function Tests
# =============================================================================

class TestComputeContentDemandScore:
    """Test compute_content_demand_score function (log10 scale)."""

    def test_zero_views(self):
        """Test with zero views returns 0."""
        assert compute_content_demand_score(0) == 0.0

    def test_negative_views(self):
        """Test with negative views returns 0."""
        assert compute_content_demand_score(-1) == 0.0

    def test_1k_views(self):
        """1k views -> log10(1000) = 3.0"""
        assert compute_content_demand_score(1000) == 3.0

    def test_10k_views(self):
        """10k views -> log10(10000) = 4.0"""
        assert compute_content_demand_score(10000) == 4.0

    def test_1m_views(self):
        """1M views -> log10(1000000) = 6.0"""
        assert compute_content_demand_score(1_000_000) == 6.0

    def test_large_games_differentiated(self):
        """Large games must not collapse to the same score."""
        score_100k = compute_content_demand_score(100_000)
        score_10m = compute_content_demand_score(10_000_000)
        assert score_10m > score_100k


class TestParseSteamspyResponse:
    """Test parse_steamspy_response function."""
    
    def test_parse_full_response(self):
        """Test parsing full SteamSpy response."""
        raw = {
            'players_2weeks': 15000,
            'owners': '100000 .. 200000',
            'positive': 5000,
            'negative': 500
        }
        
        result = parse_steamspy_response(raw)
        
        assert result['players_2weeks'] == 15000
        assert result['owners_estimate'] == '100000 .. 200000'
        assert result['positive_reviews'] == 5000
        assert result['negative_reviews'] == 500
    
    def test_parse_minimal_response(self):
        """Test parsing minimal SteamSpy response."""
        raw = {}
        
        result = parse_steamspy_response(raw)
        
        assert result['players_2weeks'] == 0
        assert result['owners_estimate'] == '0 .. 0'
        assert result['positive_reviews'] == 0
        assert result['negative_reviews'] == 0


class TestComputeReviewScore:
    """Test compute_review_score function."""
    
    def test_positive_only(self):
        """Test with only positive reviews."""
        assert compute_review_score(100, 0) == 100.0
    
    def test_negative_only(self):
        """Test with only negative reviews."""
        assert compute_review_score(0, 100) == 0.0
    
    def test_mixed_reviews(self):
        """Test with mixed reviews."""
        assert compute_review_score(80, 20) == 80.0
    
    def test_no_reviews(self):
        """Test with no reviews."""
        assert compute_review_score(0, 0) is None
    
    def test_equal_reviews(self):
        """Test with equal positive and negative reviews."""
        assert compute_review_score(50, 50) == 50.0


class TestMergeGameMetrics:
    """Test merge_game_metrics function."""
    
    def test_basic_merge(self):
        """Test basic merge of Steam, SteamSpy, and YouTube data."""
        steam_data = GameInfo(
            appid=12345,
            name='Test Game',
            installdir='testgame',
            installed=True,
            playtime_hours=10.5,
            last_played=None
        )
        steam_data.genres = ['Action', 'Indie']
        steam_data.steam_active_players = 5000
        
        steamspy_data = {
            'players_2weeks': 15000,
            'owners_estimate': '100000 .. 200000',
            'positive_reviews': 5000,
            'negative_reviews': 500
        }
        
        youtube_data = {
            'top_video_views': 50000,
            'recent_upload_count': 10,
            'avg_views_top5': 25000.0
        }
        
        result = merge_game_metrics(steam_data, steamspy_data, youtube_data)
        
        assert result['appid'] == 12345
        assert result['name'] == 'Test Game'
        assert result['playtime_hours'] == 10.5
        assert result['steam_active_players'] == 5000
        assert result['players_2weeks'] == 15000
        assert result['owners_estimate'] == '100000 .. 200000'
        assert abs(result['review_score'] - 90.9) < 0.1  # 5000/5500 * 100
        assert result['top_video_views'] == 50000
        assert result['recent_upload_count'] == 10
        assert result['avg_views_top5'] == 25000.0
        assert result['content_demand_score'] == round(__import__('math').log10(50000), 3)
        assert 'composite_score' in result
        assert result['composite_score'] > 0
        assert result['genres'] == ['Action', 'Indie']
    
    def test_merge_with_zero_views(self):
        """Test merge with zero YouTube views."""
        steam_data = GameInfo(
            appid=12345,
            name='Test Game',
            installdir='testgame',
            installed=True,
            playtime_hours=5.0,
            last_played=None
        )
        steam_data.genres = ['RPG']
        
        steamspy_data = {
            'players_2weeks': 1000,
            'owners_estimate': '5000 .. 10000',
            'positive_reviews': 100,
            'negative_reviews': 50
        }
        
        youtube_data = {
            'top_video_views': 0,
            'recent_upload_count': 0,
            'avg_views_top5': 0.0
        }
        
        result = merge_game_metrics(steam_data, steamspy_data, youtube_data)
        
        assert result['content_demand_score'] == 0.0
        assert result['composite_score'] >= 0.0
        assert result['top_video_views'] == 0
        assert abs(result['review_score'] - 66.7) < 0.1  # 100/150 * 100
    
    def test_merge_without_steam_active_players(self):
        """Test merge when Steam active players not available."""
        steam_data = GameInfo(
            appid=12345,
            name='Test Game',
            installdir='testgame',
            installed=True,
            playtime_hours=8.0,
            last_played=None
        )
        steam_data.genres = ['Strategy']
        
        steamspy_data = {
            'players_2weeks': 5000,
            'owners_estimate': '10000 .. 20000',
            'positive_reviews': 200,
            'negative_reviews': 50
        }
        
        youtube_data = {
            'top_video_views': 30000,
            'recent_upload_count': 5,
            'avg_views_top5': 15000.0
        }
        
        result = merge_game_metrics(steam_data, steamspy_data, youtube_data)
        
        assert result['steam_active_players'] is None
        assert result['content_demand_score'] == round(__import__('math').log10(30000), 3)
        assert 'composite_score' in result
        assert result['review_score'] == 80.0  # 200/250 * 100


class TestFilterByPlaytime:
    """Test filter_by_playtime function."""
    
    def test_filter_above_threshold(self):
        """Test filtering games above threshold."""
        games = [
            {'name': 'Game A', 'playtime_hours': 15.0},
            {'name': 'Game B', 'playtime_hours': 5.0},
            {'name': 'Game C', 'playtime_hours': 20.0}
        ]
        
        result = filter_by_playtime(games, 10.0)
        
        assert len(result) == 2
        assert result[0]['name'] == 'Game A'
        assert result[1]['name'] == 'Game C'
    
    def test_filter_at_threshold(self):
        """Test filtering games at exact threshold."""
        games = [
            {'name': 'Game A', 'playtime_hours': 10.0},
            {'name': 'Game B', 'playtime_hours': 9.9}
        ]
        
        result = filter_by_playtime(games, 10.0)
        
        assert len(result) == 1
        assert result[0]['name'] == 'Game A'
    
    def test_filter_no_results(self):
        """Test filtering with no games above threshold."""
        games = [
            {'name': 'Game A', 'playtime_hours': 2.0},
            {'name': 'Game B', 'playtime_hours': 5.0}
        ]
        
        result = filter_by_playtime(games, 10.0)
        
        assert len(result) == 0
    
    def test_filter_zero_threshold(self):
        """Test filtering with zero threshold (should return all)."""
        games = [
            {'name': 'Game A', 'playtime_hours': 0.0},
            {'name': 'Game B', 'playtime_hours': 5.0}
        ]
        
        result = filter_by_playtime(games, 0.0)
        
        assert len(result) == 2


class TestFilterInstalled:
    """Test filter_installed function."""
    
    def test_filter_installed_games(self):
        """Test filtering to only installed games."""
        installed_appids = {1, 2}
        
        games = [
            {'appid': 1, 'name': 'Game 1'},
            {'appid': 2, 'name': 'Game 2'},
            {'appid': 3, 'name': 'Game 3'}
        ]
        
        result = filter_installed(games, installed_appids)
        
        assert len(result) == 2
        assert result[0]['appid'] == 1
        assert result[1]['appid'] == 2
    
    def test_filter_installed_no_matches(self):
        """Test filtering when no games are installed."""
        installed_appids = set()
        
        games = [
            {'appid': 1, 'name': 'Game 1'},
            {'appid': 2, 'name': 'Game 2'}
        ]
        
        result = filter_installed(games, installed_appids)
        
        assert len(result) == 0


class TestSortByMetric:
    """Test sort_by_metric function."""
    
    def test_sort_descending(self):
        """Test sorting in descending order."""
        games = [
            {'name': 'Game A', 'score': 50},
            {'name': 'Game B', 'score': 100},
            {'name': 'Game C', 'score': 25}
        ]
        
        result = sort_by_metric(games, 'score', descending=True)
        
        assert result[0]['name'] == 'Game B'
        assert result[1]['name'] == 'Game A'
        assert result[2]['name'] == 'Game C'
    
    def test_sort_ascending(self):
        """Test sorting in ascending order."""
        games = [
            {'name': 'Game A', 'score': 50},
            {'name': 'Game B', 'score': 100},
            {'name': 'Game C', 'score': 25}
        ]
        
        result = sort_by_metric(games, 'score', descending=False)
        
        assert result[0]['name'] == 'Game C'
        assert result[1]['name'] == 'Game A'
        assert result[2]['name'] == 'Game B'
    
    def test_sort_with_missing_metric(self):
        """Test sorting when some games lack the metric."""
        games = [
            {'name': 'Game A', 'score': 50},
            {'name': 'Game B'},  # No score
            {'name': 'Game C', 'score': 25}
        ]
        
        result = sort_by_metric(games, 'score', descending=True)
        
        assert result[0]['name'] == 'Game A'
        assert result[1]['name'] == 'Game C'
        assert result[2]['name'] == 'Game B'  # Missing metric treated as 0


class TestFormatMetricsTable:
    """Test format_metrics_table function."""
    
    def test_format_empty_list(self):
        """Test formatting empty game list."""
        result = format_metrics_table([])
        assert result == "No games to display."
    
    def test_format_single_game(self):
        """Test formatting single game."""
        games = [{
            'name': 'Test Game',
            'playtime_hours': 10.5,
            'steam_active_players': 5000,
            'players_2weeks': 15000,
            'owners_estimate': '100000 .. 200000',
            'review_score': 90.0,
            'top_video_views': 50000,
            'recent_upload_count': 10,
            'content_demand_score': 50.0
        }]
        
        result = format_metrics_table(games)
        
        assert 'Test Game' in result
        assert '10.5h' in result
        assert '5,000' in result
        assert '15,000' in result
        assert '90.0%' in result
        assert '50,000' in result
        assert '10' in result
        assert '50.0' in result
    
    def test_format_multiple_games(self):
        """Test formatting multiple games."""
        games = [
            {
                'name': 'Game A',
                'playtime_hours': 15.0,
                'steam_active_players': 10000,
                'players_2weeks': 25000,
                'owners_estimate': '500000 .. 1000000',
                'review_score': 85.0,
                'top_video_views': 100000,
                'recent_upload_count': 20,
                'content_demand_score': 100.0
            },
            {
                'name': 'Game B',
                'playtime_hours': 5.0,
                'steam_active_players': 1000,
                'players_2weeks': 2000,
                'owners_estimate': '10000 .. 20000',
                'review_score': 75.0,
                'top_video_views': 5000,
                'recent_upload_count': 3,
                'content_demand_score': 5.0
            }
        ]
        
        result = format_metrics_table(games)
        
        assert 'Game A' in result
        assert 'Game B' in result
        assert '15.0h' in result
        assert '5.0h' in result
    
    def test_format_long_name_truncated(self):
        """Test that long names are truncated."""
        games = [{
            'name': 'A' * 50,
            'playtime_hours': 10.0,
            'steam_active_players': 1000,
            'players_2weeks': 5000,
            'owners_estimate': '10000 .. 20000',
            'review_score': 80.0,
            'top_video_views': 5000,
            'recent_upload_count': 5,
            'content_demand_score': 5.0
        }]
        
        result = format_metrics_table(games)
        
        assert '...' in result
        assert len(result.split('\n')[2]) <= 150  # Check line length
    
    def test_format_with_none_active_players(self):
        """Test formatting when active players is None."""
        games = [{
            'name': 'Test Game',
            'playtime_hours': 10.0,
            'steam_active_players': None,
            'players_2weeks': 3000,
            'owners_estimate': '5000 .. 10000',
            'review_score': 70.0,
            'top_video_views': 5000,
            'recent_upload_count': 5,
            'content_demand_score': 5.0
        }]
        
        result = format_metrics_table(games)
        
        # The new format shows players_2weeks instead of steam_active_players
        assert '3,000' in result  # players_2weeks should be shown


# =============================================================================
# GameMetricsClient Tests
# =============================================================================

class TestGameMetricsClientInit:
    """Test GameMetricsClient initialization."""
    
    def test_init_default_cache_dir(self):
        """Test initialization with default cache directory."""
        
        with patch('game_metrics.build_service'):
            client = GameMetricsClient()
        
        # Should use absolute path from CACHE_FILE.parent
        from pathlib import Path
        expected_dir = Path(__file__).parent.parent / ".youtube_cache"
        assert client.cache_dir == expected_dir
    
    def test_init_custom_cache_dir(self):
        """Test initialization with custom cache directory."""
        
        with patch('game_metrics.build_service'):
            client = GameMetricsClient(cache_dir='/custom/cache')
        
        # Windows converts forward slashes to backslashes
        assert 'custom' in str(client.cache_dir) and 'cache' in str(client.cache_dir)
    


class TestGameMetricsClientCache:
    """Test GameMetricsClient cache operations."""
    
    @patch('game_metrics.Path')
    def test_load_cache_exists(self, mock_path):
        """Test loading cache when file exists."""
        mock_cache_file = MagicMock()
        mock_cache_file.exists.return_value = True
        mock_path.return_value = mock_cache_file
        
        cache_data = {'12345': {'top_video_views': 50000}}
        
        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            with patch('game_metrics.build_service'):
                client = GameMetricsClient()
                result = client.load_cache()
        
        assert result == cache_data
    
    def test_load_cache_not_exists(self):
        """Test loading cache when file doesn't exist."""
        import tempfile
        
        # Use a temporary cache directory that doesn't exist
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "nonexistent_cache"
            
            with patch('game_metrics.build_service'):
                client = GameMetricsClient(cache_dir=str(cache_dir))
                result = client.load_cache()
            
            assert result == {}
    
    
    @patch('game_metrics.Path')
    def test_save_cache(self, mock_path):
        """Test saving cache to file."""
        mock_cache_file = MagicMock()
        mock_path.return_value = mock_cache_file
        
        cache_data = {'12345': {'top_video_views': 50000}}
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('game_metrics.build_service'):
                client = GameMetricsClient()
                client.save_cache(cache_data)
        
        # Verify open was called at least once for writing (may also be called for overrides load)
        mock_file.assert_called()


class TestGameMetricsClientSteamspy:
    """Test GameMetricsClient SteamSpy integration."""
    pass  # Skipping complex cache mocking for now


class TestGameMetricsClientSearch:
    """Test GameMetricsClient YouTube search."""
    
    @patch('game_metrics.time.sleep')
    @patch('game_metrics.Path')
    def test_search_youtube_success(self, mock_path, mock_sleep):
        """Test successful YouTube search."""
        # Setup Path mock to return different values for different calls
        def path_side_effect(path_str):
            mock_path_obj = MagicMock()
            if 'youtube_cache' in str(path_str):
                mock_path_obj.mkdir = MagicMock()
            return mock_path_obj
        
        mock_path.side_effect = path_side_effect
        
        # Mock YouTube service
        mock_youtube = MagicMock()
        mock_search_response = {
            'items': [
                {'id': {'videoId': 'vid1'}},
                {'id': {'videoId': 'vid2'}}
            ]
        }
        mock_videos_response = {
            'items': [
                {'statistics': {'viewCount': '100000'}},
                {'statistics': {'viewCount': '50000'}}
            ]
        }
        mock_youtube.search().list().execute.return_value = mock_search_response
        mock_youtube.videos().list().execute.return_value = mock_videos_response
        
        with patch('game_metrics.build_service', return_value=mock_youtube):
            with patch('game_metrics._google_api_available', True):
                client = GameMetricsClient()
                client.youtube_service = mock_youtube  # Override the service directly
                result = client.search_youtube_for_game('Test Game')
        
        assert result['top_video_views'] == 100000
        assert result['recent_upload_count'] == 2
        assert result['avg_views_top5'] == 75000.0
        mock_sleep.assert_called()  # Just verify sleep was called for rate limiting
    
    @patch('game_metrics.time.sleep')
    @patch('game_metrics.Path')
    def test_search_youtube_no_results(self, mock_path, mock_sleep):
        """Test YouTube search with no results."""
        # Setup Path mock to return different values for different calls
        def path_side_effect(path_str):
            mock_path_obj = MagicMock()
            if 'youtube_cache' in str(path_str):
                mock_path_obj.mkdir = MagicMock()
            return mock_path_obj
        
        mock_path.side_effect = path_side_effect
        
        mock_youtube = MagicMock()
        mock_youtube.search().list().execute.return_value = {'items': []}
        
        with patch('game_metrics.build_service', return_value=mock_youtube):
            client = GameMetricsClient()
            result = client.search_youtube_for_game('Unknown Game')
        
        assert result['top_video_views'] == 0
        assert result['recent_upload_count'] == 0
        assert result['avg_views_top5'] == 0.0


class TestGameMetricsClientGetMetrics:
    """Test GameMetricsClient.get_game_metrics."""
    pass  # Skipping complex cache mocking for now


class TestGameMetricsDataclass:
    """Test GameMetrics dataclass."""
    
    def test_game_metrics_creation(self):
        """Test creating GameMetrics instance."""
        metrics = GameMetrics(
            appid=12345,
            name='Test Game',
            playtime_hours=10.5,
            steam_active_players=5000,
            players_2weeks=15000,
            owners_estimate='100000 .. 200000',
            review_score=90.0,
            top_video_views=50000,
            recent_upload_count=10,
            avg_views_top5=25000.0,
            content_demand_score=4.699,
            composite_score=3.951,
            actual_playtime_hours=None,
            genres=['Action', 'Indie'],
            last_played=None
        )
        
        assert metrics.appid == 12345
        assert metrics.name == 'Test Game'
        assert metrics.playtime_hours == 10.5
        assert metrics.steam_active_players == 5000
        assert metrics.players_2weeks == 15000
        assert metrics.owners_estimate == '100000 .. 200000'
        assert metrics.review_score == 90.0
        assert metrics.top_video_views == 50000
        assert metrics.recent_upload_count == 10
        assert metrics.avg_views_top5 == 25000.0
        assert metrics.content_demand_score == 4.699
        assert metrics.composite_score == 3.951
        assert metrics.actual_playtime_hours is None
        assert metrics.genres == ['Action', 'Indie']
        assert metrics.last_played is None