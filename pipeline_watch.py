"""
Pipeline Watch CLI — Entry point for process watching

Usage:
    python pipeline_watch.py --game "Everything is Crab.exe"
    python pipeline_watch.py --game "Everything is Crab.exe" --scene "EIC_Capture"
    python pipeline_watch.py --game "Everything is Crab.exe" --poll 10
"""

import argparse
import sys
from pathlib import Path

# Add content-engine to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent / "content-engine"))

from core.obs_manager import OBSManager
from core.process_watcher import ProcessWatcher
from core.focus_watcher import FocusWatcher
from core.game_launcher import GameLauncher
from core.logger import Logger


def main():
    """Main entry point for pipeline watch command."""
    parser = argparse.ArgumentParser(
        description="Watch for game process and trigger OBS recording"
    )
    parser.add_argument(
        '--game',
        required=True,
        help='Game process name to watch for (e.g., "Everything is Crab.exe")'
    )
    parser.add_argument(
        '--scene',
        default=None,
        help='OBS scene to switch to before recording (optional)'
    )
    parser.add_argument(
        '--poll',
        type=int,
        default=5,
        help='Poll interval in seconds (default: 5)'
    )
    parser.add_argument(
        '--focus-pause',
        action='store_true',
        default=False,
        help='Pause recording when game loses focus. Resume when game regains focus.'
    )
    parser.add_argument(
        '--launch',
        action='store_true',
        default=False,
        help='Launch the game before watching for it. Requires steam_id or executable in config/game_folders.json.'
    )
    
    args = parser.parse_args()
    
    logger = Logger()
    
    # Connect to OBS
    logger.info("Connecting to OBS...")
    try:
        obs = OBSManager()
        if not obs.connect():
            logger.stage_error("OBS Connection", "Failed to connect")
            print("Error: Failed to connect to OBS", file=sys.stderr)
            sys.exit(1)
        logger.info("Connected to OBS successfully")
    except Exception as e:
        logger.stage_error("OBS Connection", str(e))
        print(f"Error: Failed to connect to OBS: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create process watcher
    watcher = ProcessWatcher(obs=obs, logger=logger)
    
    # Create focus watcher if --focus-pause flag is set
    focus_watcher = None
    if args.focus_pause:
        focus_watcher = FocusWatcher(logger=logger)
    
    # Launch game if --launch flag is set
    if args.launch:
        launcher = GameLauncher(logger=logger)
        success = launcher.launch(args.game)
        if not success:
            logger.info("Launch failed or not configured — watching anyway")

    
    # Watch for process
    try:
        filepath = watcher.watch(
            process_name=args.game,
            scene=args.scene,
            poll_interval=args.poll,
            focus_watcher=focus_watcher
        )
        
        if filepath:
            print(f"Recording saved: {filepath}")
        else:
            print("Recording stopped without saving")
            
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        obs.disconnect()


if __name__ == "__main__":
    main()