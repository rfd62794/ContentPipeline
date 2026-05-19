"""
ContentEngine P3b — Transcript Segmentation

Reads approved script from the database, segments the body into paragraphs,
assigns visual metadata heuristics, and writes to `asset_briefs`.
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.db import get_connection
from core.segmentation import segment_script
from core.logger import Logger

SCRIPT_ID = 1

def main():
    logger = Logger()
    logger.stage_start("P3b — Transcript Segmentation")

    conn = get_connection()
    row = conn.execute(
        "SELECT id, hook_short_script, mid_form_body, tags "
        "FROM scripts WHERE id = ?",
        (SCRIPT_ID,)
    ).fetchone()

    if not row:
        logger.stage_error("P3b", f"Script ID {SCRIPT_ID} not found.")
        sys.exit(1)

    logger.info(f"Loaded script {SCRIPT_ID}")
    
    tags = []
    try:
        tags = json.loads(row["tags"])
    except:
        pass

    logger.info("Segmenting text...")
    segments = segment_script(
        script_id=row["id"],
        hook_text=row["hook_short_script"],
        body_text=row["mid_form_body"],
        tags=tags
    )

    logger.info(f"Created {len(segments)} segments. Inserting into database...")
    
    # Clear existing briefs for this script to allow safe re-runs
    conn.execute("DELETE FROM asset_briefs WHERE script_id = ?", (SCRIPT_ID,))

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
    conn.close()

    logger.stage_complete("P3b", {"segments_created": len(segments)})

if __name__ == "__main__":
    main()
