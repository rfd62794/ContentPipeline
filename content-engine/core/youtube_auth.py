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
from typing import List, Optional, Any


# Google API imports
_google_api_available = False
_Credentials = None
_Request = None
_default = None
_build = None
try:
    from google.oauth2.credentials import Credentials as _Credentials
    from google.auth.transport.requests import Request as _Request
    from google.auth import default as _default
    from googleapiclient.discovery import build as _build
    from google_auth_oauthlib.flow import InstalledAppFlow
    _google_api_available = True
except ImportError:
    pass


TOKEN_FILE = Path(__file__).resolve().parent.parent / ".youtube_token.json"
CLIENT_SECRET_FILE = Path(__file__).resolve().parent.parent.parent / "secrets" / "client_secret_871059870702-etom8bslm61ouukn3jfun9klcq9kk29o.apps.googleusercontent.com.json"


def get_credentials(scopes: List[str]) -> Optional[_Credentials]:
    """
    Load Google OAuth credentials.

    Tries ADC first; falls back to .youtube_token.json with auto-refresh.
    If no token exists, uses client_secret.json for OAuth flow.

    Args:
        scopes: List of OAuth scope strings required by the caller.

    Returns:
        Valid Credentials object, or None if Google API not available.

    Raises:
        RuntimeError: If no valid credentials can be obtained.
    """
    if not _google_api_available:
        return None
    
    try:
        credentials, _ = _default(scopes=scopes)
        return credentials
    except Exception:
        pass

    if TOKEN_FILE.exists():
        try:
            credentials = _Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(_Request())
                TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
            return credentials
        except Exception:
            pass

    # If no valid token, use client_secret for OAuth flow
    if CLIENT_SECRET_FILE.exists():
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), scopes=scopes)
        credentials = flow.run_local_server(port=8080)
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    raise RuntimeError(
        f"No valid credentials found. Either run "
        f"'gcloud auth application-default login' or ensure "
        f"{CLIENT_SECRET_FILE} exists."
    )


def build_service(api_name: str, api_version: str, scopes: List[str]) -> Optional[Any]:
    """
    Build and return an authenticated Google API service client.

    Args:
        api_name: API name (e.g., 'youtube', 'youtubeAnalytics').
        api_version: API version string (e.g., 'v3', 'v2').
        scopes: List of OAuth scope strings.

    Returns:
        Authenticated googleapiclient Resource object, or None if Google API not available.
    """
    if not _google_api_available:
        return None
    
    credentials = get_credentials(scopes)
    if credentials is None:
        return None
    
    return _build(api_name, api_version, credentials=credentials)
