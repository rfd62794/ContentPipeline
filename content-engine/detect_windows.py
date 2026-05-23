"""
Window detection script - scan all visible windows and show titles.
Use this to find the correct window title for game capture configuration.
"""

import sys
try:
    import win32gui
except ImportError:
    print("Error: win32gui not available. Install with: pip install pywin32")
    sys.exit(1)

def scan_windows():
    """Scan all visible windows and return their titles."""
    windows = []
    
    def window_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:  # Only include windows with titles
                windows.append((hwnd, title))
        return True
    
    win32gui.EnumWindows(window_callback, windows)
    return windows

if __name__ == "__main__":
    print("Scanning all visible windows...")
    print("-" * 60)
    
    windows = scan_windows()
    
    # Sort by title for easier reading
    windows.sort(key=lambda x: x[1])
    
    for hwnd, title in windows:
        print(f"{title}")
    
    print("-" * 60)
    print(f"Found {len(windows)} visible windows")
    print("\nLook for your game window title above.")
    print("Use the exact title in your stream YAML window_title field.")