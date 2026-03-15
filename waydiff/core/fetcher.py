import asyncio
import aiohttp
import requests
import logging

from .config import CDX_API, REQUEST_TIMEOUT, MAX_SNAPSHOTS, MAX_CONCURRENT_FETCH
from .cleaner import clean_html

logger = logging.getLogger(__name__)


# ==========================================================
# SNAPSHOT LIST FETCH (Wayback CDX)
# ==========================================================

def fetch_snapshot_list(domain, start, end):
    params = {
        "url": domain,
        "output": "json",
        "fl": "timestamp,original",
        "from": start,
        "to": end,
        "collapse": "digest",
        "filter": "statuscode:200",
    }

    try:
        r = requests.get(CDX_API, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

    except requests.Timeout:
        logger.error(f"[Wayback Timeout] Domain: {domain}")
        return []

    except requests.RequestException as e:
        logger.error(f"[Wayback Request Error] {e}")
        return []

    except ValueError:
        logger.error("[Wayback JSON Parse Error]")
        return []

    except Exception as e:
        logger.exception(f"[Unexpected Wayback Error] {e}")
        return []

    if not isinstance(data, list) or len(data) <= 1:
        logger.warning(f"[Wayback] No snapshots found for {domain}")
        return []

    # data[0] is the header row, skip it
    return data[1:MAX_SNAPSHOTS+1]


# ==========================================================
# ASYNC HTML FETCH WITH HEADER CAPTURE
# ==========================================================

async def fetch_html(session, url):
    """
    Fetch a single URL asynchronously.
    Uses the session-level timeout; no per-request timeout override needed.
    """
    try:
        async with session.get(url) as resp:
            status = resp.status

            if status != 200:
                logger.warning(f"[Fetch] Non-200 response {status} for {url}")
                return None

            raw_text = await resp.text()
            cleaned_html = clean_html(raw_text)

            return {
                "html": cleaned_html,
                "headers": dict(resp.headers),
                "status": status,
                "url": url
            }

    except asyncio.TimeoutError:
        logger.warning(f"[Fetch Timeout] {url}")
        return None

    except aiohttp.ClientError as e:
        logger.warning(f"[Fetch Client Error] {url} | {e}")
        return None

    except Exception as e:
        logger.exception(f"[Unexpected Fetch Error] {url} | {e}")
        return None


# ==========================================================
# SINGLE SNAPSHOT FETCH (NEW - for localsnap)
# ==========================================================

async def fetch_single_snapshot(
    url: str,
    headers: dict = None
):
    """
    Fetch a single snapshot from any URL (internal or external domain).
    
    Used by localsnap module to capture internal domain snapshots.
    
    Args:
        url: URL to fetch (e.g., https://internal.local/admin)
        headers: Optional HTTP headers for request
    
    Returns:
        Dict with html, headers, status, url; or None on failure
    
    Example:
        >>> import asyncio
        >>> result = asyncio.run(fetch_single_snapshot("https://example.com"))
        >>> if result:
        ...     print(f"Fetched {len(result['html'])} lines")
    """
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    connector = aiohttp.TCPConnector(limit=1)
    
    try:
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers or {}
        ) as session:
            result = await fetch_html(session, url)
            return result
    
    except Exception as e:
        logger.exception(f"Error fetching single snapshot: {url}")
        return None


# ==========================================================
# FETCH SELECTED SNAPSHOTS + LIVE SITE
# ==========================================================

async def fetch_selected_snapshots(domain, selected_snapshots):
    """
    Fetch all selected Wayback snapshots and the live site concurrently.

    Returns:
        (snapshot_results, live_result) where snapshot_results is a list
        aligned with selected_snapshots, and live_result is the live fetch.
    """
    # aiohttp requires ClientTimeout object — not a raw int
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_FETCH)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:

        # Fetch historical snapshots
        tasks = [
            fetch_html(session, f"https://web.archive.org/web/{ts}/{orig}")
            for ts, orig in selected_snapshots
        ]

        snapshot_results = await asyncio.gather(*tasks, return_exceptions=True)

        clean_snapshots = []
        for result in snapshot_results:
            if isinstance(result, Exception):
                logger.warning(f"[Snapshot Fetch Error] {result}")
                clean_snapshots.append(None)
            else:
                clean_snapshots.append(result)

        # Fetch live version (try https first, fall back to http)
        live_result = None
        for scheme in ["https://", "http://"]:
            live_result = await fetch_html(session, scheme + domain)
            if live_result:
                break

        if not live_result:
            logger.warning(f"[Live Fetch Failed] Could not fetch live site for {domain}")

    return clean_snapshots, live_result
