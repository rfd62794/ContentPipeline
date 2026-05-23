"""
Tests for YouTube Upload Client

Only pure functions are tested. Integration functions (upload_video, get_authenticated_service, main) are not called from tests.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from youtube_upload import build_video_resource


# =============================================================================
# Build Video Resource Tests
# =============================================================================

class TestBuildVideoResource:
    """Tests for build_video_resource pure function."""
    
    def test_build_video_resource_fields(self):
        """Test returns dict with snippet, status keys."""
        metadata = {
            'title': 'Test Title',
            'description': 'Test Description',
            'tags': ['tag1', 'tag2'],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert 'snippet' in result
        assert 'status' in result
    
    def test_build_video_resource_privacy(self):
        """Test privacy value maps correctly to YouTube status."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': [],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['status']['privacyStatus'] == 'public'
    
    def test_build_video_resource_privacy_unlisted(self):
        """Test unlisted privacy maps correctly."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': [],
            'privacy': 'unlisted',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['status']['privacyStatus'] == 'unlisted'
    
    def test_build_video_resource_privacy_private(self):
        """Test private privacy maps correctly."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': [],
            'privacy': 'private',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['status']['privacyStatus'] == 'private'
    
    def test_build_video_resource_tags(self):
        """Test tags list present in snippet."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': ['tag1', 'tag2', 'tag3'],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['snippet']['tags'] == ['tag1', 'tag2', 'tag3']
    
    def test_build_video_resource_title(self):
        """Test title present in snippet."""
        metadata = {
            'title': 'My Video Title',
            'description': 'Test',
            'tags': [],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['snippet']['title'] == 'My Video Title'
    
    def test_build_video_resource_description(self):
        """Test description present in snippet."""
        metadata = {
            'title': 'Test',
            'description': 'My video description',
            'tags': [],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['snippet']['description'] == 'My video description'
    
    def test_build_video_resource_category_id(self):
        """Test category_id present in snippet."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': [],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['snippet']['categoryId'] == '20'
    
    def test_build_video_resource_made_for_kids(self):
        """Test made_for_kids present in status."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': [],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': True
        }
        
        result = build_video_resource(metadata)
        
        assert result['status']['selfDeclaredMadeForKids'] is True
    
    def test_build_video_resource_made_for_kids_false(self):
        """Test made_for_kids false in status."""
        metadata = {
            'title': 'Test',
            'description': 'Test',
            'tags': [],
            'privacy': 'public',
            'category_id': '20',
            'made_for_kids': False
        }
        
        result = build_video_resource(metadata)
        
        assert result['status']['selfDeclaredMadeForKids'] is False
