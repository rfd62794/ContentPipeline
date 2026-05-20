# ContentPipeline

A faceless content pipeline for game analysis Shorts. Give it a beat structure and a video file. It produces a YouTube Short.

Built because manual video editing is friction. You see something interesting in a game, you want to share it, but the editing step stops you. This removes that step.

## What it does

```bash
# Produce a Short from YAML config
python content-engine/produce_short.py content-engine/shorts/eic_short_1_evolution.yaml

# Watch your own game and auto-capture
python content-engine/pipeline_watch.py --game "Everything is Crab.exe" --scene "Game_Capture"

# Download clips from YouTube and assemble
python content-engine/pipeline_watch.py --source "https://youtube.com/watch?v=xxx" --topic "mechanics"
```

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/GameReviewAgent.git
cd GameReviewAgent

# Install dependencies
cd content-engine
pip install -r requirements.txt

# Configure OBS WebSocket
cp config.yaml.example config.yaml
# Edit config.yaml with your OBS WebSocket credentials

# Produce a test Short
python produce_short.py shorts/eic_short_1_evolution.yaml
```

## Installation

```bash
# Python 3.14+ required
python --version

# Install FFmpeg (required for video processing)
# Windows: Download from https://ffmpeg.org/download.html
# Add to PATH

# Install Python dependencies
cd content-engine
pip install -r requirements.txt

# Configure OBS WebSocket (optional, for live capture)
# Edit config.yaml:
# obs_host: localhost
# obs_port: 4455
# obs_password: your_password
```

## Directory Structure

```
GameReviewAgent/
├── content-engine/
│   ├── core/
│   │   ├── assembler.py          # Video assembly and text overlay
│   │   ├── clip_sourcer.py      # YouTube clip download
│   │   ├── obs_capture.py       # OBS WebSocket control
│   │   ├── process_watcher.py   # Process monitoring
│   │   └── ...
│   ├── shorts/
│   │   ├── eic_short_1_evolution.yaml
│   │   ├── eic_short_2_predator.yaml
│   │   └── ...
│   ├── tests/
│   │   ├── test_assembler.py
│   │   ├── test_produce_short.py
│   │   └── ...
│   ├── config.yaml              # Main configuration
│   ├── config/game_folders.json  # Game process mappings
│   ├── produce_short.py         # YAML-driven short production
│   ├── pipeline_watch.py        # Live capture pipeline
│   └── requirements.txt
├── README.md
└── docs/
    ├── adr/                     # Architecture Decision Records
    ├── state/
    │   └── current.md           # Current development state
    └── sdd/                     # System Design Document
```

## Producing a Short

```bash
# Create a YAML config in shorts/ directory
cat > shorts/my_short.yaml << EOF
name: my_short
source: /path/to/video.mp4
attribution: null
music_path: assets/music/Pixelated_Passion.mp3
music_start: 0
stack_text: false
max_visible_lines: 5
beats:
  - clip_start: "0:10"
    clip_end: "0:15"
    duration: 5
    line: "First observation"
  - clip_start: "0:20"
    clip_end: "0:25"
    duration: 5
    line: "Second observation"
EOF

# Produce the Short
python produce_short.py shorts/my_short.yaml

# Output appears in output/shorts/my_short.mp4
```

## Pipeline Watch (own-game capture)

```bash
# Basic capture with focus detection
python pipeline_watch.py --game "Everything is Crab.exe" --scene "Game_Capture"

# With game launch
python pipeline_watch.py --game "Everything is Crab.exe" --launch --scene "Game_Capture"

# With focus pause (pauses recording when game loses focus)
python pipeline_watch.py --game "Everything is Crab.exe" --focus-pause --scene "Game_Capture"

# Full pipeline with all options
python pipeline_watch.py \
  --game "Everything is Crab.exe" \
  --launch \
  --scene "Game_Capture" \
  --focus-pause \
  --topic "mechanics"
```

## YAML Schema Reference

```yaml
# Short name (used for output filename)
name: short_name

# Video source (local file path or YouTube URL)
source: /path/to/video.mp4
# OR
source: https://www.youtube.com/watch?v=VIDEO_ID

# Attribution text (null for own footage, string for third-party)
attribution: null
# OR
attribution: "Gameplay via: CreatorName"

# Background music path
music_path: assets/music/Pixelated_Passion.mp3

# Music start offset in seconds (optional, default: 0)
music_start: 0

# Enable text stacking with sliding window (optional, default: false)
stack_text: false

# Maximum visible lines when stacking (optional, default: 5)
max_visible_lines: 5

# Beat array — each beat is a video segment with text overlay
beats:
  # Video segment start timestamp (MM:SS or HH:MM:SS format)
  - clip_start: "0:33"
    
    # Video segment end timestamp
    clip_end: "0:35"
    
    # Segment duration in seconds (controls text timing)
    duration: 2
    
    # Text line to display (supports \n for multiline)
    line: "You feed."
```

## Backlog

**Planned:**
- Tower migration and remote trigger
- YouTube publish (P9) — automated upload
- Steam API integration — auto-populate game library
- OBS auto-launch
- Telegram bot trigger layer
- GitHub Issues workflow

**Deferred:**
- Blur fill background (technical issue on Windows FFmpeg)
- Aider integration — separate project
- Live streaming support

## License

MIT License

Copyright (c) 2026 GameReviewAgent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
