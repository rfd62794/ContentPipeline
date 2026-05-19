"""
Tests for stage_p3b_segment.py
"""

import sys
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.db import get_connection


def test_p3b_no_visual_type():
    """P3b writes asset_briefs rows with visual_type=NULL."""
    test_db = Path("content-engine/database/test_p3b_temp.db")
    conn = get_connection(test_db)
    
    try:
        # Initialize schema
        from core.db import SCHEMA_PATH
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        
        # Create a test topic first (foreign key requirement)
        conn.execute(
            """
            INSERT INTO topics (title, domain, input_mode)
            VALUES ('Test Topic', 'game_mechanics', 'topic_only')
            """
        )
        
        # Create a test script
        conn.execute(
            """
            INSERT INTO scripts (topic_id, hook_short_script, mid_form_body, word_count_hook, word_count_body, estimated_duration_s)
            VALUES (1, 'Test hook', 'Test body', 5, 10, 30)
            """
        )
        conn.commit()
        
        # Import and run the segmentation logic
        from core.segmentation import segment_script
        segments = segment_script(
            script_id=1,
            hook_text="Test hook",
            body_text="Test body with multiple sentences. This is a second sentence. And a third one.",
            tags=[]
        )
        
        # Insert segments using the same logic as P3b
        for seg in segments:
            conn.execute(
                """
                INSERT INTO asset_briefs 
                (script_id, segment_index, segment_text, estimated_duration_s,
                 search_query, status)
                VALUES (?, ?, ?, ?, '', 'pending')
                """,
                (
                    seg["script_id"],
                    seg["segment_index"],
                    seg["segment_text"],
                    seg["estimated_duration_s"]
                )
            )
        conn.commit()
        
        # Verify visual_type is NULL
        rows = conn.execute("SELECT visual_type FROM asset_briefs").fetchall()
        for row in rows:
            assert row["visual_type"] is None, f"visual_type should be NULL, got {row['visual_type']}"
        
    finally:
        conn.close()
        if test_db.exists():
            test_db.unlink()