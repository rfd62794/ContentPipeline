"""
Tests for core/logger.py
"""

import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.logger import Logger


class TestLogger:
    def test_logger_stage_start(self):
        """Logger.stage_start prints stage name with timestamp."""
        logger = Logger()
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger.stage_start("test_stage")
            output = fake_out.getvalue()
            assert "STAGE START: test_stage" in output
            assert "[" in output  # Timestamp prefix
    
    def test_logger_stage_complete(self):
        """Logger.stage_complete prints details dict."""
        logger = Logger()
        with patch('sys.stdout', new=StringIO()) as fake_out:
            details = {"segments": 10, "duration": 300}
            logger.stage_complete("test_stage", details)
            output = fake_out.getvalue()
            assert "STAGE COMPLETE: test_stage" in output
            assert "segments: 10" in output
            assert "duration: 300" in output
    
    def test_logger_stage_error(self):
        """Logger.stage_error prints error message."""
        logger = Logger()
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger.stage_error("test_stage", "Test error message")
            output = fake_out.getvalue()
            assert "STAGE ERROR: test_stage" in output
            assert "Error: Test error message" in output
    
    def test_logger_info(self):
        """Logger.info prints informational message."""
        logger = Logger()
        with patch('sys.stdout', new=StringIO()) as fake_out:
            logger.info("Test info message")
            output = fake_out.getvalue()
            assert "INFO: Test info message" in output