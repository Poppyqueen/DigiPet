"""
xeno_canto_api.py
-----------------
Wrapper around the Xeno-canto API v3.
Handles metadata fetching AND audio file fetching through requests_cache,
so expiry and on-disk cleanup are fully managed by the library.

Two separate CachedSessions with different expiry windows:
  _meta_session  — JSON metadata, 24-hour expiry
  _audio_session — MP3 binary responses, 6-hour expiry

Both sessions call .cache.delete(expired=True) at import time to evict
stale entries accumulated from previous runs.

Pagination
----------
Rather than fetching all available pages at once, each daily pull fetches
a fixed window of pages (_PAGES_PER_DAY, default 2) starting from a
persisted cursor in .cache/xeno_canto_page_cursor_<lat>_<lon>.json. After
each pull the cursor advances by _PAGES_PER_DAY and wraps back to 1 when
the end of the available pages is reached. This gives a fresh pool of up to
200 recordings per day that cycles through the full catalogue over time,
without ever pulling more than needed in a single call.

Query building
--------------
Query strings are constructed manually and concatenated directly into the URL.
xeno-canto's query parser expects its DSL tags in raw form (e.g. lat:4.2,
q:">C") and does not correctly parse the percent-encoded equivalents that
requests' params= approach would produce. Manual construction is intentional.

Audio fetch
-----------
download_audio() only sleeps before a live network request, never on a
cache hit. This removes unnecessary latency when audio is already cached.
"""

from __future__ import annotations

import json
import logging
import os
import time as _time

import requests_cache
from requests import Request
from retry_requests import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache setup
# ---------------------------------------------------------------------------

os.makedirs(".cache", exist_ok=True)

# Metadata session — JSON API responses, 24-hour expiry.
_meta_cache = requests_cache.CachedSession(
    ".cache/xeno_canto_meta",
    backend="filesystem",
    expire_after=86400,
)
_meta_cache.cache.delete(expired=True)
_meta_session = retry(_meta_cache, retries=5, backoff_factor=0.2)

# Audio session — MP3 binary downloads, 6-hour expiry.
# 6 hours covers the longest single time-tag window (morning, ~5 h).
# requests_cache stores raw response bytes transparently on disk;
# callers just read .content as usual.
_audio_cache = requests_cache.CachedSession(
    ".cache/xeno_canto_audio",
    backend="filesystem",
    expire_after=21600,
)
_audio_cache.cache.delete(expired=True)
_audio_session = retry(_audio_cache, retries=3, backoff_factor=0.5)

_XC_API_URL = "https://xeno-canto.org/api/3/recordings"

# ---------------------------------------------------------------------------
# Query constants — single source of truth for quality/length filters.
# ---------------------------------------------------------------------------

_QUALITY_FILTER = ">C"    # quality A or B only (API syntax: greater-than C)
_LEN_MIN        = ">15"   # at least 15 seconds
_LEN_MAX        = "<120"  # at most 2 minutes

# How many consecutive pages to fetch on each daily pull.
# Each page is 100 recordings, so the default pool is 200 per day.
# The starting page advances by this value each day, cycling back to 1
# when the end of the available pages is reached.
_PAGES_PER_DAY = 2

# Coordinate rounding for stable cache keys (~11 km precision).
_LAT_LON_ROUND_PRECISION = 1

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _round_coord(value: float) -> float:
    return round(value, _LAT_LON_ROUND_PRECISION)

def _cursor_path(lat: float, long: float) -> str:
    return f".cache/xeno_canto_page_cursor_{_round_coord(lat)}_{_round_coord(long)}.json"

# ---------------------------------------------------------------------------
# Page cursor — persists the sliding window across daily pulls
# ---------------------------------------------------------------------------

def _read_cursor(lat: float, long: float) -> int:
    """Return the next starting page to fetch (1-based). Defaults to 1."""
    try:
        with open(_cursor_path(lat, long)) as f:
            return max(1, int(json.load(f).get("next_page", 1)))
    except Exception:
        return 1


def _write_cursor(lat: float, long: float, next_page: int) -> None:
    """Persist the next starting page for tomorrow's pull."""
    try:
        with open(_cursor_path(lat, long), "w") as f:
            json.dump({"next_page": next_page}, f)
    except Exception as e:
        logger.warning("Could not write page cursor to %s: %s", _cursor_path(lat, long), e)


def _build_lat_lon_query(lat: float, long: float, sound_type: str | None = None) -> str:
    """
    Build a xeno-canto v3 query string for a lat/lon location.

    Uses lat+lon tags (each searches within ~1°, roughly 110 km radius).
    Filter tags are pulled from the module-level constants to stay in sync.
    """
    parts = [
        f"lat:{_round_coord(lat)}",
        f"lon:{_round_coord(long)}",
        f'q:"{_QUALITY_FILTER}"',
        f'len:"{_LEN_MIN}"',
        f'len:"{_LEN_MAX}"',
    ]
    if sound_type:
        quoted = f'"{sound_type}"' if " " in sound_type else sound_type
        parts.append(f"type:{quoted}")
    return "+".join(parts)


# ---------------------------------------------------------------------------
# Audio fetch
# ---------------------------------------------------------------------------

def download_audio(recording: dict) -> bytes | None:
    """
    Fetch the audio bytes for a recording.

    The response is cached by _audio_session for 6 hours. On a cache hit,
    bytes are returned from disk instantly — no sleep, no network request.
    On a cache miss, a 0.5-second courtesy sleep precedes the live fetch
    to avoid hammering the xeno-canto servers.

    Xeno-canto returns protocol-relative URLs (//xeno-canto.org/…),
    so we prepend https: before fetching.

    Returns raw MP3 bytes on success, None on failure.
    """
    recording_id = recording.get("id")
    file_url     = recording.get("file", "")

    if not recording_id or not file_url:
        logger.warning("Recording %r has no file URL.", recording_id)
        return None

    if file_url.startswith("//"):
        file_url = "https:" + file_url

    # Check cache before sleeping — no point in delaying a cache hit.
    try:
        req       = Request("GET", file_url).prepare()
        cache_key = _audio_cache.cache.create_key(req)
        if _audio_cache.cache.contains(cache_key):
            response = _audio_session.get(file_url, timeout=15)
            logger.debug("Audio XC%s [cached]", recording_id)
            return response.content
    except Exception:
        pass  # Fall through to live fetch below

    # Live fetch — sleep first as a courtesy to the server.
    _time.sleep(0.5)
    try:
        response = _audio_session.get(file_url, timeout=15)
        response.raise_for_status()
        logger.debug("Audio XC%s [live]", recording_id)
        return response.content
    except Exception as e:
        logger.error("Failed to fetch audio for XC%s: %s", recording_id, e)
        return None


# ---------------------------------------------------------------------------
# Single-page fetch helper
# ---------------------------------------------------------------------------

def _fetch_page(
    query:    str,
    api_key:  str,
    page:     int,
    per_page: int = 100,
) -> tuple[list[dict], int]:
    """
    Fetch a single page of results for a given query.

    URL construction note: xeno-canto's query parser expects its DSL tags
    in raw form (e.g. lat:4.2, q:">C") — it does not parse percent-encoded
    equivalents correctly. For this reason we construct the URL manually
    rather than using params= (which would encode colons, quotes, and angle
    brackets). This is intentional and has been verified against the API.

    # DO NOT switch to params= — xeno-canto rejects percent-encoded queries.

    Returns (recordings, num_pages) on success, ([], 0) on error.
    """
    url = f"{_XC_API_URL}?query={query}&key={api_key}&per_page={per_page}&page={page}"
    try:
        response = _meta_session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            logger.error("API error on page %d: %s", page, data["error"])
            return [], 0

        recordings = data.get("recordings", [])
        num_pages  = int(data.get("numPages", 1))
        cached     = "[cached]" if getattr(response, "from_cache", False) else "[live]"

        logger.debug("Page %d/%d: %d recordings %s", page, num_pages, len(recordings), cached)
        return recordings, num_pages

    except Exception as e:
        logger.error("Request failed on page %d: %s", page, e)
        return [], 0


# ---------------------------------------------------------------------------
# Paginated fetch helper
# ---------------------------------------------------------------------------

def _fetch_pages(
    query:         str,
    api_key:       str,
    start_page:    int,
    pages_per_day: int,
    per_page:      int = 100,
) -> tuple[list[dict], int]:
    """
    Fetch pages_per_day consecutive pages starting from start_page.

    Returns (deduplicated_recordings, num_pages_total).
    Stops early if a page returns fewer recordings than per_page.
    """
    all_recordings: list[dict] = []
    seen_ids:       set[str]   = set()
    num_pages_total = 1  # updated from first response

    for offset in range(pages_per_day):
        page = start_page + offset

        # Don't request past the last known page
        if page > num_pages_total and offset > 0:

            # In _fetch_pages(), replace logger.debug with:
            # print(f"[XenoCantoAPI] Page {page}/{num_pages_total}: {len(recordings)} recordings {'[cached]' if ... else '[live]'}")
            # print(f"[XenoCantoAPI] Early stop: page returned {len(recordings)} < per_page {per_page}")
            break

        recordings, num_pages_total = _fetch_page(
            query=query, api_key=api_key, page=page, per_page=per_page,
        )

        for r in recordings:
            rid = r.get("id", "")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                all_recordings.append(r)

        # Short page means we've hit the end
        if len(recordings) == 0:
            break

    return all_recordings, num_pages_total


# ---------------------------------------------------------------------------
# Main API class
# ---------------------------------------------------------------------------

class XenoCantoLoc:
    """
    Fetches and caches xeno-canto recording metadata for a lat/lon location.

    Both metadata (24 h) and audio (6 h) are cached via requests_cache
    filesystem sessions. Expiry and cleanup are handled entirely by the
    library — no manual purge logic required here.

    Pagination
    ----------
    get_recordings() fetches _PAGES_PER_DAY pages per call, returning up to
    _PAGES_PER_DAY × per_page deduplicated recordings. The full result set
    is cached at the page level — repeated calls within 24 hours cost nothing.
    """

    def __init__(self, lat: float, long: float, api_key: str):
        self.lat     = float(lat)
        self.long    = float(long)
        self.api_key = api_key

    # ------------------------------------------------------------------
    # Metadata fetch — paginated
    # ------------------------------------------------------------------
    def get_recordings(
        self,
        sound_type:    str | None = None,
        per_page:      int = 100,
        pages_per_day: int = _PAGES_PER_DAY,
    ) -> list[dict]:
        """
        Fetch today's window of recordings for this location.

        Each daily pull fetches pages_per_day consecutive pages starting
        from the cursor stored in .cache/xeno_canto_page_cursor_<lat>_<lon>.json.
        After fetching, the cursor advances by pages_per_day and wraps back
        to 1 when the end of the available pages is reached — so each day's
        pool is a fresh slice of the full xeno-canto catalogue for this location.

        Example with pages_per_day=2 and 5 total pages available:
        Day 1: pages 1–2  → cursor written as 3
        Day 2: pages 3–4  → cursor written as 5
        Day 3: page  5    → cursor wraps, written as 1
        Day 4: pages 1–2  → cursor written as 3  (cycle repeats)

        If no recordings are found, the search is retried with a wider geographic
        radius (~110 km vs ~11 km) to ensure something is always returned.

        Results are deduplicated by recording id before returning.
        Returns a list of recording dicts, or [] on error / no results.
        """
        query      = _build_lat_lon_query(self.lat, self.long, sound_type)
        start_page = _read_cursor(self.lat, self.long)

        # print(f"[XenoCantoAPI] Daily pull: lat={self.lat}, long={self.long} — pages {start_page}..{start_page + pages_per_day - 1}")


        all_recordings, num_pages_total = _fetch_pages(
            query=query,
            api_key=self.api_key,
            start_page=start_page,
            pages_per_day=pages_per_day,
            per_page=per_page,
        )

        if not all_recordings:
            logger.warning("No results for lat=%s, lon=%s — widening search. ~110 km", self.lat, self.long)
            fallback_query = (
                f"lat:{round(self.lat)}+lon:{round(self.long)}"
                f'+q:"{_QUALITY_FILTER}"+len:"{_LEN_MIN}"+len:"{_LEN_MAX}"'
            )
            all_recordings, num_pages_total = _fetch_pages(
                query=fallback_query, api_key=self.api_key,
                start_page=1, pages_per_day=pages_per_day, per_page=per_page,
            )

        next_page = start_page + pages_per_day
        if next_page > num_pages_total:
            next_page = 1
            logger.info("Page cursor wrapped back to 1 (total pages: %d).", num_pages_total)
        _write_cursor(self.lat, self.long, next_page)

        # print(f"[XenoCantoAPI] Daily pool: {len(all_recordings)} recordings (next pull starts at page {next_page})")

        return all_recordings