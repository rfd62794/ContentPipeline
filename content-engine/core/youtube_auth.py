"""
Shared YouTube OAuth credential loader.

Single source of truth for all Google API authentication in this project.
Strategy:
  1. Try gcloud Application Default Credentials (ADC) — preferred for local dev.
  2. Fall back to .youtube_token.json (OAuth refresh token file).

Usage:
    from core.youtube_auth import get_credentials, TOKEN_FILE
    credentials = get_credentials(scopes=[...])
"""

import sys
from pathlib import Path
from typing import List, Optional

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth import default
    from googleapiclient.discovery import build
except ImportError:
    print("Error: Google API libraries not installed.")
    print("Run: pip install google-auth google-auth-oauthlib google-api-python-client")
    sys.exit(1)


TOKEN_FILE = Path(__file__).resolve().parent.parent / ".youtube_token.json"
CLIENT_SECRET_FILE = Path(__file__).resolve().parent.parent / "client_secret.json"


def get_credentials(scopes: List[str]) -> Credentials:
    """
    Load Google OAuth credentials.

    Tries ADC first; falls back to .youtube_token.json with auto-refresh.

    Args:
        scopes: List of OAuth scope strings required by the caller.

    Returns:
        Valid Credentials object.

    Raises:
        RuntimeError: If no valid credentials can be obtained.
    """
    try:
        credentials, _ = default(scopes=scopes)
        return credentials
    except Exception:
        pass

    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"No valid credentials found. Either run "
            f"'gcloud auth application-default login' or ensure "
            f"{TOKEN_FILE} exists."
        )

    credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def build_service(api_name: str, api_version: str, scopes: List[str]):
    """
    Build and return an authenticated Google API service client.

    Args:
        api_name: API name (e.g., 'youtube', 'youtubeAnalytics').
        api_version: API version string (e.g., 'v3', 'v2').
        scopes: List of OAuth scope strings.

    Returns:
        Authenticated googleapiclient Resource object.
    """
    credentials = get_credentials(scopes)
    return build(api_name, api_version, credentials=credentials)
