# ADR-STR-002: HTML Browser Sources for Overlays

**Status:** Accepted  
**Date:** May 2026  
**Context:** Stream Launcher Phase STR-2

## Context

OBS Studio overlays can be implemented using several approaches:
- Static images (PNG/JPG) - require external tools to update, not version-controlled
- Video files (MP4/WebM) - larger files, harder to customize, not version-controlled
- Browser sources (HTML/CSS/JS) - fully customizable, version-controlled, portable

The stream launcher needs professional overlays for:
- Starting Soon scene (before stream)
- BRB scene (on focus loss)
- Game Info card (during gameplay)
- Ending scene (stream conclusion)

These overlays need to display dynamic data (game name, session count, commit count) and match the brand identity consistently.

## Decision

All overlays will be implemented as local HTML files in `content-engine/overlays/`. OBS will point to these files using `file://` paths as browser sources.

### Design Tokens

All overlays share a common CSS token set for consistent branding:
```css
:root {
    --bg: #0a0a0a;
    --primary: #00ff41;
    --secondary: #00cc33;
    --dark-green: #003300;
    --text: #e0e0e0;
    --font: 'Courier New', Courier, monospace;
}
```

### Overlay Files

1. **starting_soon.html** - Full-screen overlay shown before stream starts
   - Static text with CSS-animated progress bar
   - No JavaScript

2. **brb.html** - Full-screen overlay shown on focus loss
   - Terminal-style cursor blink via CSS animation
   - No JavaScript

3. **game_info.html** - Small card (400x160px) for Gaming scene
   - Bottom-left positioning
   - Dynamic data via URL query parameters
   - Minimal JavaScript for URL param reading only
   - Updated every 60 seconds via OBS websocket

4. **ending.html** - Full-screen overlay shown when stream ends
   - Static text with commit count via URL param
   - Minimal JavaScript for URL param reading only

### JavaScript Restriction

JavaScript is restricted to URL parameter reading in `game_info.html` and `ending.html` only. No other JavaScript is permitted in overlay files. All animations must be CSS-only.

### Data Injection

Dynamic data is injected via URL query parameters:
```
file:///path/to/game_info.html?game=Dorfromantik&session=3&commits=7
```

The stream launcher constructs these URLs and updates them via OBS websocket calls.

## Consequences

### Positive
- Overlays are version-controlled in the repo
- Brand updates require editing HTML/CSS in one location
- No external dependencies or CDNs required
- Fully offline-capable
- Portable across different machines
- Easy to customize and extend

### Negative
- OBS scene setup is manual (one-time configuration)
- Requires OBS websocket integration for dynamic updates
- Browser sources may have higher resource usage than static images

### Mitigations
- OBS setup will be documented in `docs/obs_setup.md`
- OBS websocket integration already implemented in stream_launcher.py
- Resource usage is minimal for simple HTML overlays

## Alternatives Considered

1. **Static Images** - Rejected due to lack of version control and difficulty updating
2. **CDN-hosted Overlays** - Rejected due to external dependency and offline requirements
3. **OBS Plugin System** - Rejected due to complexity and cross-platform concerns
4. **External Overlay Tools** - Rejected to maintain single-repo simplicity

## References

- Phase STR-2 Directive: Stream Overlays + Test Modes
- OBS Browser Source Documentation: https://obsproject.com/wiki/Browser-Source