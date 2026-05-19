"""
ContentEngine Logger

Single responsibility: stage status output.
Stdlib only (datetime, sys). Zero external dependencies.
"""

from datetime import datetime
from typing import Dict, Any


class Logger:
    """Logger class for stage status output."""
    
    def stage_start(self, stage: str) -> None:
        """Log the start of a pipeline stage."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] STAGE START: {stage}")
    
    def stage_complete(self, stage: str, details: Dict[str, Any]) -> None:
        """Log the completion of a pipeline stage with details."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] STAGE COMPLETE: {stage}")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    def stage_error(self, stage: str, error: str) -> None:
        """Log an error during a pipeline stage."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] STAGE ERROR: {stage}")
        print(f"  Error: {error}")
    
    def info(self, message: str) -> None:
        """Log an informational message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] INFO: {message}")