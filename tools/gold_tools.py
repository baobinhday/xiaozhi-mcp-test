"""Gold price tool functions for fetching gold prices from VNAppMob API."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger("gold_tools")

# Base URL for the gold price API
BASE_URL = "https://api.vnappmob.com"

# API key expires after 15 days
API_KEY_EXPIRY_DAYS = 15

# Cache for API key with timestamp: (api_key, fetched_at)
_api_key_cache: Tuple[Optional[str], Optional[datetime]] = (None, None)


def _get_api_key() -> Optional[str]:
    """Get API key from VNAppMob API.
    
    Fetches the API key required for gold price API calls.
    The key is cached for subsequent calls and auto-refreshed after 15 days.
    
    Returns:
        API key string if successful, None otherwise.
    """
    global _api_key_cache
    
    cached_key, fetched_at = _api_key_cache
    
    # Check if cached key is still valid (not expired)
    if cached_key and fetched_at:
        expiry_time = fetched_at + timedelta(days=API_KEY_EXPIRY_DAYS)
        if datetime.now() < expiry_time:
            return cached_key
        else:
            logger.info("API key expired, fetching new key...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/request_api_key",
            params={"scope": "gold"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        api_key = data.get("results")
        _api_key_cache = (api_key, datetime.now())
        logger.info("Successfully fetched API key for gold prices")
        return api_key
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch API key: {e}")
        return None


def _fetch_gold_price(provider: str) -> Dict[str, Any]:
    """Internal function to fetch gold price from a specific provider.
    
    Args:
        provider: Gold provider name (sjc, doji, pnj).
        
    Returns:
        Dict with 'success' status and 'data' or 'error' message.
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "Failed to obtain API key"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/gold/{provider}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"Successfully fetched {provider.upper()} gold prices")
        return {"success": True, "provider": provider.upper(), "data": data.get("results", [])}
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {provider} gold price: {e}")
        return {"success": False, "error": str(e)}


def get_sjc_gold_price() -> Dict[str, Any]:
    """Get SJC Gold Price.
    
    Fetches the current gold prices from SJC (Saigon Jewelry Company).
    
    Returns:
        Dict with 'success' status and gold price data or 'error' message.
        Data includes 'buy_1l' (buy price) and 'sell_1l' (sell price) in VND.
        
    Examples:
        >>> get_sjc_gold_price()
        {'success': True, 'provider': 'SJC', 'data': [{'buy_1l': 42550000.00, 'sell_1l': 42550000.00}]}
    """
    return _fetch_gold_price("sjc")


def get_doji_gold_price() -> Dict[str, Any]:
    """Get DOJI Gold Price.
    
    Fetches the current gold prices from DOJI Gold & Gems.
    
    Returns:
        Dict with 'success' status and gold price data or 'error' message.
        Data includes 'buy_1l' (buy price) and 'sell_1l' (sell price) in VND.
        
    Examples:
        >>> get_doji_gold_price()
        {'success': True, 'provider': 'DOJI', 'data': [{'buy_1l': 42550000.00, 'sell_1l': 42550000.00}]}
    """
    return _fetch_gold_price("doji")


def get_pnj_gold_price() -> Dict[str, Any]:
    """Get PNJ Gold Price.
    
    Fetches the current gold prices from PNJ (Phu Nhuan Jewelry).
    
    Returns:
        Dict with 'success' status and gold price data or 'error' message.
        Data includes 'buy_1l' (buy price) and 'sell_1l' (sell price) in VND.
        
    Examples:
        >>> get_pnj_gold_price()
        {'success': True, 'provider': 'PNJ', 'data': [{'buy_1l': 42550000.00, 'sell_1l': 42550000.00}]}
    """
    return _fetch_gold_price("pnj")


def get_all_gold_prices() -> Dict[str, Any]:
    """Get gold prices from all providers (SJC, DOJI, PNJ).
    
    Fetches current gold prices from all major Vietnamese gold providers.
    
    Returns:
        Dict with 'success' status and combined gold price data from all providers.
        
    Examples:
        >>> get_all_gold_prices()
        {'success': True, 'data': {'SJC': [...], 'DOJI': [...], 'PNJ': [...]}}
    """
    providers = ["sjc", "doji", "pnj"]
    results = {}
    errors = []
    
    for provider in providers:
        result = _fetch_gold_price(provider)
        if result["success"]:
            results[provider.upper()] = result["data"]
        else:
            errors.append(f"{provider.upper()}: {result['error']}")
    
    if not results:
        return {"success": False, "error": "; ".join(errors)}
    
    return {
        "success": True,
        "data": results,
        "errors": errors if errors else None
    }

