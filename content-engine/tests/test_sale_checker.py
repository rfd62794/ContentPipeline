"""
Tests for sale_checker.py

All HTTP calls are mocked. No network required.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from sale_checker import (
    parse_lookup_response,
    parse_price_overview,
    is_on_sale,
    format_sale_result,
    lookup_game_ids,
    fetch_price_overview,
    get_sale_info,
)


# =============================================================================
# Pure Function Tests
# =============================================================================

class TestParseLookupResponse:
    """Test parse_lookup_response pure function."""

    def test_found_game(self):
        raw = {"found": True, "game": {"id": "018d937f-33f0-7200-80fc-87f769196c84", "title": "Hades"}}
        result = parse_lookup_response(raw, "Hades")
        assert result == "018d937f-33f0-7200-80fc-87f769196c84"

    def test_not_found_returns_none(self):
        raw = {"found": False}
        result = parse_lookup_response(raw, "FakeGame9999")
        assert result is None

    def test_found_false_with_game_key_returns_none(self):
        raw = {"found": False, "game": None}
        assert parse_lookup_response(raw, "X") is None

    def test_missing_id_in_game_returns_none(self):
        raw = {"found": True, "game": {"title": "WeirdGame"}}
        assert parse_lookup_response(raw, "WeirdGame") is None


class TestParsePriceOverview:
    """Test parse_price_overview pure function."""

    def test_basic_parse(self):
        raw = {"prices": [
            {
                "id": "abc123",
                "current": {
                    "price": {"amount": 4.99},
                    "cut": 75,
                    "shop": {"name": "Steam"},
                    "url": "https://store.steampowered.com/app/1145360",
                },
                "lowest": {
                    "price": {"amount": 1.24},
                },
            }
        ]}
        id_to_name = {"abc123": "Hades"}
        results = parse_price_overview(raw, id_to_name)
        assert len(results) == 1
        r = results[0]
        assert r["name"] == "Hades"
        assert r["current_price"] == 4.99
        assert r["current_discount_pct"] == 75
        assert r["historical_low"] == 1.24
        assert r["on_sale"] is True
        assert r["store_name"] == "Steam"

    def test_no_current_price(self):
        raw = {"prices": [{"id": "abc123", "current": None, "lowest": None}]}
        id_to_name = {"abc123": "SomeGame"}
        results = parse_price_overview(raw, id_to_name)
        r = results[0]
        assert r["current_price"] is None
        assert r["current_discount_pct"] == 0
        assert r["historical_low"] is None
        assert r["on_sale"] is False

    def test_full_price_not_on_sale(self):
        raw = {"prices": [
            {
                "id": "xyz",
                "current": {
                    "price": {"amount": 29.99},
                    "cut": 0,
                    "shop": {"name": "Steam"},
                    "url": "",
                },
                "lowest": {"price": {"amount": 7.49}},
            }
        ]}
        id_to_name = {"xyz": "Risk of Rain 2"}
        results = parse_price_overview(raw, id_to_name)
        assert results[0]["on_sale"] is False
        assert results[0]["current_discount_pct"] == 0

    def test_unknown_id_uses_id_as_name(self):
        raw = {"prices": [{"id": "unknown-id", "current": None, "lowest": None}]}
        results = parse_price_overview(raw, {})
        assert results[0]["name"] == "unknown-id"


class TestIsOnSale:
    """Test is_on_sale pure function."""

    def test_zero_discount_not_on_sale(self):
        assert is_on_sale(0) is False

    def test_positive_discount_on_sale(self):
        assert is_on_sale(10) is True
        assert is_on_sale(75) is True
        assert is_on_sale(100) is True

    def test_fractional_discount(self):
        assert is_on_sale(0.1) is True


class TestFormatSaleResult:
    """Test format_sale_result pure function."""

    def test_on_sale_game(self):
        game = {
            "name": "Hades",
            "current_price": 4.99,
            "current_discount_pct": 75,
            "historical_low": 1.24,
            "on_sale": True,
            "store_name": "Steam",
            "store_url": "",
        }
        result = format_sale_result(game)
        assert "Hades" in result
        assert "$4.99" in result
        assert "75% off" in result
        assert "$1.24" in result
        assert "Steam" in result

    def test_full_price_game(self):
        game = {
            "name": "Risk of Rain 2",
            "current_price": 29.99,
            "current_discount_pct": 0,
            "historical_low": 7.49,
            "on_sale": False,
            "store_name": "Steam",
            "store_url": "",
        }
        result = format_sale_result(game)
        assert "full price" in result
        assert "$29.99" in result

    def test_not_found_game(self):
        game = {"name": "FakeGame", "error": "not found on ITAD"}
        result = format_sale_result(game)
        assert "FakeGame" in result
        assert "not found on ITAD" in result

    def test_no_price_available(self):
        game = {
            "name": "SomeGame",
            "current_price": None,
            "current_discount_pct": 0,
            "historical_low": None,
            "on_sale": False,
            "store_name": "",
            "store_url": "",
        }
        result = format_sale_result(game)
        assert "N/A" in result


# =============================================================================
# Network Call Tests (all mocked)
# =============================================================================

class TestLookupGameIds:
    """Test lookup_game_ids with mocked HTTP."""

    def test_successful_lookup(self):
        def mock_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            title = params.get("title", "")
            responses = {
                "Hades": {"found": True, "game": {"id": "abc123", "title": "Hades"}},
                "Skyrim": {"found": True, "game": {"id": "def456", "title": "Skyrim"}},
            }
            resp.json.return_value = responses.get(title, {"found": False})
            return resp

        with patch("sale_checker.requests.get", side_effect=mock_get) as mock_g:
            result = lookup_game_ids(["Hades", "Skyrim"], "test-key")

        assert result == {"Hades": "abc123", "Skyrim": "def456"}
        assert mock_g.call_count == 2

    def test_partial_lookup(self):
        def mock_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            title = params.get("title", "")
            if title == "Hades":
                resp.json.return_value = {"found": True, "game": {"id": "abc123"}}
            else:
                resp.json.return_value = {"found": False}
            return resp

        with patch("sale_checker.requests.get", side_effect=mock_get):
            result = lookup_game_ids(["Hades", "FakeGame"], "test-key")

        assert "Hades" in result
        assert "FakeGame" not in result


class TestFetchPriceOverview:
    """Test fetch_price_overview with mocked HTTP."""

    def test_successful_fetch(self):
        mock_raw = {"prices": [
            {
                "id": "abc123",
                "current": {
                    "price": {"amount": 4.99},
                    "cut": 75,
                    "shop": {"name": "Steam"},
                    "url": "",
                },
                "lowest": {"price": {"amount": 1.24}},
            }
        ]}
        mock_response = MagicMock()
        mock_response.json.return_value = mock_raw
        mock_response.raise_for_status = MagicMock()

        with patch("sale_checker.requests.post", return_value=mock_response) as mock_post:
            result = fetch_price_overview(["abc123"], "test-key", country="US")

        assert result == mock_raw
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["params"]["country"] == "US"


class TestGetSaleInfo:
    """Test get_sale_info end-to-end with mocked HTTP."""

    def test_full_flow_found_games(self):
        lookup_responses = {
            "Hades": {"found": True, "game": {"id": "abc123", "title": "Hades"}},
            "Skyrim": {"found": True, "game": {"id": "def456", "title": "Skyrim"}},
        }
        prices_raw = {"prices": [
            {
                "id": "abc123",
                "current": {
                    "price": {"amount": 4.99},
                    "cut": 75,
                    "shop": {"name": "Steam"},
                    "url": "",
                },
                "lowest": {"price": {"amount": 1.24}},
            },
            {
                "id": "def456",
                "current": {
                    "price": {"amount": 39.99},
                    "cut": 0,
                    "shop": {"name": "Steam"},
                    "url": "",
                },
                "lowest": {"price": {"amount": 9.99}},
            },
        ]}

        def mock_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = lookup_responses.get(params.get("title", ""), {"found": False})
            return resp

        def mock_post(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = prices_raw
            return resp

        with patch("sale_checker.requests.get", side_effect=mock_get):
            with patch("sale_checker.requests.post", side_effect=mock_post):
                with patch.dict("os.environ", {"ITAD_API_KEY": "test-key"}):
                    results = get_sale_info(["Hades", "Skyrim"])

        names = [r["name"] for r in results]
        assert "Hades" in names
        assert "Skyrim" in names

        hades = next(r for r in results if r["name"] == "Hades")
        assert hades["on_sale"] is True
        assert hades["current_discount_pct"] == 75

    def test_not_found_game_included(self):
        def mock_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"found": False}
            return resp

        with patch("sale_checker.requests.get", side_effect=mock_get):
            with patch.dict("os.environ", {"ITAD_API_KEY": "test-key"}):
                results = get_sale_info(["FakeGame9999"])

        assert len(results) == 1
        assert results[0]["name"] == "FakeGame9999"
        assert results[0]["error"] == "not found on ITAD"

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove ITAD_API_KEY if present
            import os
            os.environ.pop("ITAD_API_KEY", None)
            with pytest.raises(ValueError, match="ITAD_API_KEY"):
                get_sale_info(["Hades"])

    def test_mixed_found_and_not_found(self):
        lookup_responses = {
            "Hades": {"found": True, "game": {"id": "abc123"}},
            "FakeGame": {"found": False},
        }
        prices_raw = {"prices": [
            {
                "id": "abc123",
                "current": {
                    "price": {"amount": 4.99},
                    "cut": 75,
                    "shop": {"name": "Steam"},
                    "url": "",
                },
                "lowest": {"price": {"amount": 1.24}},
            }
        ]}

        def mock_get(url, params=None, headers=None, timeout=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = lookup_responses.get(params.get("title", ""), {"found": False})
            return resp

        def mock_post(url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = prices_raw
            return resp

        with patch("sale_checker.requests.get", side_effect=mock_get):
            with patch("sale_checker.requests.post", side_effect=mock_post):
                with patch.dict("os.environ", {"ITAD_API_KEY": "test-key"}):
                    results = get_sale_info(["Hades", "FakeGame"])

        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "Hades" in names
        assert "FakeGame" in names
        fake = next(r for r in results if r["name"] == "FakeGame")
        assert "error" in fake
