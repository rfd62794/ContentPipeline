"""
Metadata Builder for YouTube Upload

Implements three-layer metadata override architecture:
- Layer 3: Manual override fields (always win)
- Layer 1: Auto-generated from Steam + short YAML (used when auto_generate true and field empty)
- Layer 2: Templates (deferred)

Pure functions only. No network calls. No file I/O beyond reading YAML.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


def load_short_yaml(short_path: str) -> Dict[str, Any]:
    """
    Load and return short YAML as dict.
    
    Args:
        short_path: Path to short YAML file.
    
    Returns:
        Dictionary with short configuration.
    
    Raises:
        FileNotFoundError: If file doesn't exist.
        yaml.YAMLError: If YAML parsing fails.
    """
    with open(short_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_meta_yaml(meta_path: str) -> Dict[str, Any]:
    """
    Load and return .meta.yaml as dict. Returns defaults if file missing.
    
    Args:
        meta_path: Path to .meta.yaml file.
    
    Returns:
        Dictionary with metadata override configuration.
        Returns default dict if file doesn't exist.
    """
    defaults = {
        'auto_generate': False,
        'title': '',
        'description': '',
        'tags': [],
        'privacy': 'public',
        'schedule': '',
        'category_id': '20',
        'made_for_kids': False
    }
    
    path = Path(meta_path)
    if not path.exists():
        return defaults
    
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = yaml.safe_load(f)
            if meta is None:
                return defaults
            # Merge with defaults to ensure all keys present
            return {**defaults, **meta}
    except (yaml.YAMLError, IOError):
        return defaults


def resolve_metadata(short: Dict[str, Any], meta: Dict[str, Any], steam_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Apply three-layer resolution.
    Layer 3 (manual meta fields) wins if non-empty.
    Layer 1 (auto-generated from steam + short) used when:
      - meta field is empty AND meta['auto_generate'] is True
    Returns resolved dict: title, description, tags, privacy, 
    schedule, category_id, made_for_kids.
    
    Args:
        short: Short YAML configuration dict.
        meta: .meta.yaml configuration dict.
        steam_metadata: Optional Steam Store API metadata dict.
    
    Returns:
        Resolved metadata dict. Does not mutate input dicts.
    """
    auto_generate = meta.get('auto_generate', False)
    
    # Resolve title
    title = meta.get('title', '')
    if not title and auto_generate:
        title = generate_title_layer1(short, steam_metadata)
    
    # Resolve description
    description = meta.get('description', '')
    if not description and auto_generate:
        description = generate_description_layer1(short, steam_metadata)
    
    # Resolve tags
    tags = meta.get('tags', [])
    if not tags and auto_generate:
        tags = generate_tags_layer1(short, steam_metadata)
    
    # Direct fields (no Layer 1 fallback)
    privacy = meta.get('privacy', 'public')
    schedule = meta.get('schedule', '')
    category_id = meta.get('category_id', '20')
    made_for_kids = meta.get('made_for_kids', False)
    
    return {
        'title': title,
        'description': description,
        'tags': tags,
        'privacy': privacy,
        'schedule': schedule,
        'category_id': category_id,
        'made_for_kids': made_for_kids,
        'auto_generate': auto_generate
    }


def generate_title_layer1(short: Dict[str, Any], steam: Optional[Dict[str, Any]]) -> str:
    """
    Generate title from short_id and game name.
    Pattern: '[Game] — [short_id humanized]'
    
    Args:
        short: Short YAML configuration dict.
        steam: Optional Steam Store API metadata dict.
    
    Returns:
        Generated title string.
    """
    short_id = short.get('name', 'unknown')
    
    # Humanize short_id (e.g., eic_short_4_shellephant -> EIC Short 4: Shellephant)
    humanized = short_id.replace('_', ' ').title()
    
    if steam:
        game_name = steam.get('name', 'Unknown Game')
        return f"{game_name} — {humanized}"
    
    return humanized


def generate_description_layer1(short: Dict[str, Any], steam: Optional[Dict[str, Any]]) -> str:
    """
    Generate description from Steam description snippet + segment count.
    
    Args:
        short: Short YAML configuration dict.
        steam: Optional Steam Store API metadata dict.
    
    Returns:
        Generated description string. Max 5000 chars.
    """
    segments = short.get('beats', [])
    segment_count = len(segments)
    
    if steam:
        steam_desc = steam.get('description', '')
        # Truncate to 3000 chars to leave room for segment info
        desc_snippet = steam_desc[:3000] if steam_desc else ''
        base = f"{desc_snippet}\n\n" if desc_snippet else ''
    else:
        base = ""
    
    segment_info = f"Short with {segment_count} segments."
    
    full_desc = f"{base}{segment_info}"
    
    # Enforce 5000 char limit
    return full_desc[:5000]


def generate_tags_layer1(short: Dict[str, Any], steam: Optional[Dict[str, Any]]) -> List[str]:
    """
    Generate tags from Steam genres + tags.
    Max 500 chars total (YouTube limit).
    
    Args:
        short: Short YAML configuration dict.
        steam: Optional Steam Store API metadata dict.
    
    Returns:
        List of tags. Total tag string length never exceeds 500 chars.
    """
    tags = []
    
    if steam:
        genres = steam.get('genres', [])
        steam_tags = steam.get('tags', [])
        tags.extend(genres)
        tags.extend(steam_tags)
    
    # Enforce 500 char total limit
    total_length = 0
    filtered_tags = []
    for tag in tags:
        tag_str = str(tag)
        # Add comma if not first tag
        if filtered_tags:
            tag_str = f",{tag_str}"
        
        if total_length + len(tag_str) <= 500:
            filtered_tags.append(tag)
            total_length += len(tag_str)
        else:
            break
    
    return filtered_tags


def validate_metadata(resolved: Dict[str, Any]) -> List[str]:
    """
    Return list of validation errors. Empty list = valid.
    Check: title not empty, title <= 100 chars, tags total <= 500 chars,
    description <= 5000 chars, privacy valid value.
    
    Args:
        resolved: Resolved metadata dict.
    
    Returns:
        List of validation error strings. Empty if valid.
    """
    errors = []
    
    title = resolved.get('title', '')
    if not title:
        errors.append("Title cannot be empty")
    elif len(title) > 100:
        errors.append(f"Title exceeds 100 characters ({len(title)} chars)")
    
    description = resolved.get('description', '')
    if len(description) > 5000:
        errors.append(f"Description exceeds 5000 characters ({len(description)} chars)")
    
    tags = resolved.get('tags', [])
    tags_string = ','.join(str(t) for t in tags)
    if len(tags_string) > 500:
        errors.append(f"Tags exceed 500 characters total ({len(tags_string)} chars)")
    
    privacy = resolved.get('privacy', '')
    valid_privacy = ['public', 'unlisted', 'private']
    if privacy not in valid_privacy:
        errors.append(f"Invalid privacy value: {privacy}. Must be one of {valid_privacy}")
    
    return errors


def format_schedule(schedule_str: str) -> Optional[str]:
    """
    Convert schedule string to RFC 3339 format for YouTube API.
    Empty string returns None (publish immediately).
    
    Args:
        schedule_str: Schedule string in ISO format or empty.
    
    Returns:
        RFC 3339 formatted datetime string or None.
    
    Raises:
        ValueError: If schedule string is invalid format.
    """
    if not schedule_str:
        return None
    
    # Check if already in RFC 3339 format with timezone offset
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', schedule_str):
        return schedule_str
    
    # Try parsing common formats
    formats = [
        '%Y-%m-%dT%H:%M:%S%z',  # ISO format with T and timezone offset
        '%Y-%m-%dT%H:%M:%S',  # ISO format with T
        '%Y-%m-%d %H:%M:%S',  # Space separator
        '%Y-%m-%d %H:%M',     # Without seconds
        '%Y-%m-%d',           # Date only
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(schedule_str, fmt)
            # Convert to RFC 3339 format
            return dt.isoformat()
        except ValueError:
            continue
    
    raise ValueError(f"Invalid schedule format: {schedule_str}")
