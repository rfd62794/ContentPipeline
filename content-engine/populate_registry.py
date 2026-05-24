#!/usr/bin/env python3
"""
Populate game_registry.json with all installed Steam games.
One-time setup script to scan all installed games and cache their executable names.
"""

import sys
from pathlib import Path

# Add parent directory to PATH for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stream_launcher import load_game_registry, save_game_registry, find_game_exe, update_game_registry_entry

def populate_all_games():
    """Scan all installed Steam games and populate registry."""
    try:
        from steam_library import SteamLibrary
        
        # Initialize Steam library
        steam_path = Path("C:/Program Files (x86)/Steam")
        steam_lib = SteamLibrary(steam_path)
        
        # Get all installed games
        games = steam_lib.get_installed_only()
        print(f"Found {len(games)} installed games")
        
        # Load existing registry
        registry = load_game_registry()
        print(f"Existing registry entries: {len(registry)}")
        
        # Process each game
        updated_count = 0
        for game in games:
            appid = game.appid
            game_name = game.name
            
            print(f"\nProcessing: {game_name} (appid: {appid})")
            
            # Try to find executable
            exe_name = find_game_exe(appid, steam_path)
            
            if exe_name:
                # Get existing entry to preserve session_count
                existing_entry = registry.get(str(appid), {})
                session_count = existing_entry.get("session_count", 0)
                
                # Update registry
                registry = update_game_registry_entry(
                    registry, appid,
                    exe_name=exe_name,
                    install_path=Path("C:/Program Files (x86)/Steam/steamapps/common") / game.installdir if game.installdir else "",
                    session_count=session_count
                )
                updated_count += 1
                print(f"  [OK] Found: {exe_name}")
            else:
                print(f"  [SKIP] No executable found")
        
        # Save updated registry
        save_game_registry(registry)
        print(f"\n[OK] Registry updated with {updated_count} games")
        print(f"[OK] Total registry entries: {len(registry)}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    populate_all_games()