"""
IsThereAnyDeal (ITAD) Sale Checker

Looks up current prices and historical lows for games using the ITAD API v2.9.0.

Endpoints used:
  POST /lookup/games/id/title/v1  — resolve game names -> ITAD game IDs
  POST /prices/overview/v1        — current price + historical low per game ID

Requires ITAD_API_KEY in environment (or .env file).
"""

import os
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

ITAD_BASE_URL = "https://api.isthereanydeal.com"
ITAD_API_KEY_ENV = "ITAD_API_KEY"


# =============================================================================
# Pure Functions (Testable Without Network)
# =============================================================================

def parse_lookup_response(raw: dict) -> dict[str, str]:
    """
    Parse the /lookup/games/id/title/v1 response into a name -> game_id map.

    Args:
        raw: Raw API response dict mapping game name -> {id: str} or null

    Returns:
        Dict mapping original game name -> ITAD game ID (only found games)
    """
    result = {}
    for name, data in raw.items():
        if data and isinstance(data, dict) and data.get("id"):
            result[name] = data["id"]
    return result


def parse_price_overview(raw: dict, id_to_name: dict[str, str]) -> list[dict]:
    """
    Parse the /prices/overview/v1 response into a flat list of sale results.

    Args:
        raw: Raw API response — list of game price objects
        id_to_name: Map of ITAD game ID -> original game name

    Returns:
        List of dicts with price info per game
    """
    results = []
    for item in raw:
        game_id = item.get("id", "")
        name = id_to_name.get(game_id, game_id)

        current = item.get("current")
        lowest = item.get("lowest")

        if current:
            price = current.get("price", {})
            current_price = price.get("amount")
            current_discount = current.get("cut", 0)
            store = current.get("shop", {}).get("name", "")
            store_url = current.get("url", "")
        else:
            current_price = None
            current_discount = 0
            store = ""
            store_url = ""

        historical_low = lowest.get("price", {}).get("amount") if lowest else None

        results.append({
            "name": name,
            "game_id": game_id,
            "current_price": current_price,
            "current_discount_pct": current_discount,
            "historical_low": historical_low,
            "on_sale": is_on_sale(current_discount),
            "store_name": store,
            "store_url": store_url,
        })
    return results


def is_on_sale(discount_pct: float) -> bool:
    """
    Return True if the discount percentage indicates an active sale.

    Args:
        discount_pct: Discount as integer percentage (e.g. 75 means 75% off)

    Returns:
        True if discount > 0
    """
    return discount_pct > 0


def format_sale_result(game: dict) -> str:
    """
    Format a single sale result dict into a human-readable string.

    Args:
        game: Dict with price info fields

    Returns:
        Formatted string summary
    """
    if "error" in game:
        return f"{game['name']}: {game['error']}"

    name = game["name"]
    price = game.get("current_price")
    discount = game.get("current_discount_pct", 0)
    low = game.get("historical_low")
    store = game.get("store_name", "")

    price_str = f"${price:.2f}" if price is not None else "N/A"
    low_str = f"${low:.2f}" if low is not None else "N/A"
    discount_str = f"{discount}% off" if discount else "full price"
    store_str = f" on {store}" if store else ""

    return f"{name}: {price_str} ({discount_str}){store_str} | Historical low: {low_str}"


# =============================================================================
# API Client
# =============================================================================

def _get_api_key() -> str:
    """Load ITAD API key from environment. Raises ValueError if missing."""
    key = os.environ.get(ITAD_API_KEY_ENV)
    if not key:
        raise ValueError(
            f"ITAD_API_KEY not set. Add it to your .env file or environment. "
            f"Register at https://isthereanydeal.com/apps/my/"
        )
    return key


def lookup_game_ids(game_names: list[str], api_key: str) -> dict[str, str]:
    """
    Resolve a list of game names to ITAD game IDs.

    Args:
        game_names: List of game title strings
        api_key: ITAD API key

    Returns:
        Dict mapping game name -> ITAD game ID (only found entries)
    """
    url = f"{ITAD_BASE_URL}/lookup/games/id/title/v1"
    headers = {"ITAD-API-Key": api_key, "Content-Type": "application/json"}
    response = requests.post(url, json=game_names, headers=headers, timeout=10)
    response.raise_for_status()
    return parse_lookup_response(response.json())


def fetch_price_overview(game_ids: list[str], api_key: str,
                         country: str = "US") -> list[dict]:
    """
    Fetch current prices and historical lows for a list of ITAD game IDs.

    Args:
        game_ids: List of ITAD game ID strings
        api_key: ITAD API key
        country: ISO 3166-1 alpha-2 country code for pricing

    Returns:
        Raw list of price objects from the API
    """
    url = f"{ITAD_BASE_URL}/prices/overview/v1"
    headers = {"ITAD-API-Key": api_key, "Content-Type": "application/json"}
    params = {"country": country}
    response = requests.post(url, json=game_ids, headers=headers,
                             params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_sale_info(game_names: list[str], country: str = "US") -> list[dict]:
    """
    Look up current sale prices and historical lows for a list of game names.

    Args:
        game_names: List of game title strings to look up
        country: ISO 3166-1 alpha-2 country code (default: "US")

    Returns:
        List of dicts per game with price info. Games not found on ITAD
        are included as {"name": "...", "error": "not found on ITAD"}.
    """
    api_key = _get_api_key()

    # Step 1: resolve names -> ITAD IDs
    name_to_id = lookup_game_ids(game_names, api_key)

    # Track which games weren't found
    not_found = [n for n in game_names if n not in name_to_id]

    results = []

    if name_to_id:
        # Step 2: fetch price overview for found IDs
        id_to_name = {v: k for k, v in name_to_id.items()}
        raw_prices = fetch_price_overview(list(name_to_id.values()), api_key, country)
        results = parse_price_overview(raw_prices, id_to_name)

    # Append not-found entries
    for name in not_found:
        results.append({"name": name, "error": "not found on ITAD"})

    return results
