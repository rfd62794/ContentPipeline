"""
Tests for SQLite metrics history functionality in game_metrics.py.

All DB interactions use a temporary in-memory SQLite DB — no files written.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from game_metrics import (
    compute_trend_delta,
    compute_composite_with_trend,
    MetricsHistoryDB,
)


# =============================================================================
# Pure Function Tests
# =============================================================================

class TestComputeTrendDelta:
    """Test compute_trend_delta pure function."""

    def test_positive_delta(self):
        assert compute_trend_delta(50000, 10000) == 40000

    def test_negative_delta(self):
        assert compute_trend_delta(5000, 20000) == -15000

    def test_zero_delta(self):
        assert compute_trend_delta(10000, 10000) == 0

    def test_current_none_returns_none(self):
        assert compute_trend_delta(None, 10000) is None

    def test_historical_none_returns_none(self):
        assert compute_trend_delta(10000, None) is None

    def test_both_none_returns_none(self):
        assert compute_trend_delta(None, None) is None

    def test_zero_historical(self):
        assert compute_trend_delta(5000, 0) == 5000

    def test_zero_current(self):
        assert compute_trend_delta(0, 5000) == -5000


class TestComputeCompositeWithTrend:
    """Test compute_composite_with_trend pure function."""

    def test_positive_delta_adds_boost(self):
        import math
        base = 4.0
        delta = 9  # log10(10) * 0.5 = 0.5
        result = compute_composite_with_trend(base, delta)
        assert result == round(base + math.log10(delta + 1) * 0.5, 3)
        assert result > base

    def test_zero_delta_no_boost(self):
        result = compute_composite_with_trend(4.0, 0)
        assert result == 4.0

    def test_negative_delta_no_penalty(self):
        result = compute_composite_with_trend(4.0, -5000)
        assert result == 4.0

    def test_none_delta_no_boost(self):
        result = compute_composite_with_trend(4.0, None)
        assert result == 4.0

    def test_large_delta_log_scaled(self):
        import math
        base = 3.0
        delta = 999999
        result = compute_composite_with_trend(base, delta)
        expected = round(base + math.log10(1000000) * 0.5, 3)
        assert result == expected
        # Even 1M delta only adds 3.0 (log10(1M)=6, *0.5=3)
        assert result < base + 4

    def test_rounding_to_3_decimal_places(self):
        result = compute_composite_with_trend(3.141592, 99)
        assert len(str(result).split('.')[-1]) <= 3


# =============================================================================
# MetricsHistoryDB Tests (in-memory SQLite)
# =============================================================================

class TestMetricsHistoryDB:
    """Test MetricsHistoryDB using a temp file DB."""

    def _make_db(self, tmp_path):
        """Create a temp-file DB for testing."""
        return MetricsHistoryDB(db_path=tmp_path / "test_history.db")

    def test_init_creates_table(self, tmp_path):
        db = self._make_db(tmp_path)
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics_history'"
            ).fetchone()
        assert tables is not None

    def test_write_and_read_today(self, tmp_path):
        db = self._make_db(tmp_path)
        db.write_snapshot(appid=12345, players_2weeks=50000, recent_upload_count=10)
        today = date.today().isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            row = conn.execute(
                "SELECT players_2weeks, recent_upload_count FROM metrics_history "
                "WHERE appid=? AND date=?", (12345, today)
            ).fetchone()
        assert row == (50000, 10)

    def test_write_insert_or_replace(self, tmp_path):
        db = self._make_db(tmp_path)
        db.write_snapshot(appid=12345, players_2weeks=1000, recent_upload_count=5)
        db.write_snapshot(appid=12345, players_2weeks=2000, recent_upload_count=8)
        today = date.today().isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            rows = conn.execute(
                "SELECT players_2weeks FROM metrics_history WHERE appid=? AND date=?",
                (12345, today)
            ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 2000

    def test_read_7d_ago_no_history_returns_none(self, tmp_path):
        db = self._make_db(tmp_path)
        result = db.read_snapshot_7d_ago(appid=99999)
        assert result is None

    def test_read_7d_ago_with_matching_row(self, tmp_path):
        db = self._make_db(tmp_path)
        target_date = (date.today() - timedelta(days=7)).isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "INSERT INTO metrics_history (appid, date, players_2weeks, recent_upload_count) "
                "VALUES (?, ?, ?, ?)",
                (12345, target_date, 30000, 7)
            )
            conn.commit()
        result = db.read_snapshot_7d_ago(appid=12345)
        assert result is not None
        assert result["players_2weeks"] == 30000
        assert result["recent_upload_count"] == 7

    def test_read_7d_ago_wrong_date_returns_none(self, tmp_path):
        db = self._make_db(tmp_path)
        wrong_date = (date.today() - timedelta(days=6)).isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "INSERT INTO metrics_history (appid, date, players_2weeks, recent_upload_count) "
                "VALUES (?, ?, ?, ?)",
                (12345, wrong_date, 30000, 7)
            )
            conn.commit()
        result = db.read_snapshot_7d_ago(appid=12345)
        assert result is None

    def test_read_7d_ago_wrong_appid_returns_none(self, tmp_path):
        db = self._make_db(tmp_path)
        target_date = (date.today() - timedelta(days=7)).isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "INSERT INTO metrics_history (appid, date, players_2weeks, recent_upload_count) "
                "VALUES (?, ?, ?, ?)",
                (11111, target_date, 30000, 7)
            )
            conn.commit()
        result = db.read_snapshot_7d_ago(appid=99999)
        assert result is None

    def test_write_none_players_2weeks(self, tmp_path):
        db = self._make_db(tmp_path)
        db.write_snapshot(appid=12345, players_2weeks=None, recent_upload_count=5)
        today = date.today().isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            row = conn.execute(
                "SELECT players_2weeks FROM metrics_history WHERE appid=? AND date=?",
                (12345, today)
            ).fetchone()
        assert row[0] is None

    def test_multiple_games_isolated(self, tmp_path):
        db = self._make_db(tmp_path)
        target_date = (date.today() - timedelta(days=7)).isoformat()
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            conn.executemany(
                "INSERT INTO metrics_history VALUES (?, ?, ?, ?)",
                [(111, target_date, 1000, 3), (222, target_date, 5000, 12)]
            )
            conn.commit()
        r1 = db.read_snapshot_7d_ago(111)
        r2 = db.read_snapshot_7d_ago(222)
        assert r1["players_2weeks"] == 1000
        assert r2["players_2weeks"] == 5000
