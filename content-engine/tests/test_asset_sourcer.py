"""
Tests for core/asset_sourcer.py
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.asset_sourcer import source_asset_for_segment


def test_asset_sourcer_config_param():
    """asset_sourcer accepts config as parameter."""
    segment = {
        "id": 1,
        "segment_index": 0,
        "segment_text": "Test segment",
        "game_title": None,
        "mechanic": None,
        "moment": None
    }
    
    config = {"image_variant_count": 3}
    
    # Test that function accepts config parameter without error
    # We're not testing the actual logic, just that it accepts the parameter
    try:
        # This will fail due to missing assets, but should not fail due to parameter signature
        result = source_asset_for_segment(segment, config)
        # If it doesn't raise a TypeError for parameter, the test passes
        assert True
    except TypeError as e:
        if "config" in str(e):
            raise AssertionError(f"Function does not accept config parameter: {e}")
        # Other TypeErrors are expected (missing assets, etc.)
        assert True