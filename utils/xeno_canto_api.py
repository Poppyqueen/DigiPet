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
Recording metadata is fetched once per day in a "daily pool" of
_PAGES_PER_DAY consecutive pages from the xeno-canto catalogue. The pool
is persisted to .cache/xeno_canto_pool_<lat>_<lon>.json and reused for
all time-tag refreshes within the same day — morning, afternoon, night all
read from the same pool file without re-fetching.

The page cursor (which page to start from next) lives inside the pool file
itself under the "next_page" key. It advances once per daily refresh and
wraps back to 1 when the end of the catalogue is reached. There is no
separate cursor file.

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
import os
import time as _time

import requests_cache
from requests import Request
from retry_requests import retry


# ---------------------------------------------------------------------------
# Cache setup
# ---------------------------------------------------------------------------

os.makedirs(".cache", exist_ok=True)

_DAILY_POOL_CACHE_DIR = ".cache"
_DAILY_POOL_TTL: int = 86400  # 24 hours — how long a fetched metadata pool is considered fresh



# Metadata session — JSON API responses, 24-hour expiry.
_meta_cache = requests_cache.CachedSession(
    ".cache/xeno_canto_meta",
    backend="filesystem",
    expire_after=_DAILY_POOL_TTL,
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


def _pool_path(lat: float, long: float) -> str:
    return os.path.join(
        _DAILY_POOL_CACHE_DIR,
        f"xeno_canto_pool_{_round_coord(lat)}_{_round_coord(long)}.json"
    )


def _save_pool(recordings: list[dict], next_page: int, lat: float, long: float) -> None:
    """
    Persist today's recording pool and the cursor for the next daily refresh.
    next_page is the page the NEXT refresh should start from.
    """
    path = _pool_path(lat, long)
    try:
        payload = {
            "saved_at":   _time.time(),
            "next_page":  next_page,
            "recordings": recordings,
        }
        with open(path, "w") as f:
            json.dump(payload, f)
        print(f"[XenoCantoAPI] Daily pool saved: {len(recordings)} recordings, "
              f"next_page={next_page} → {path}")
    except Exception as e:
        print(f"[XenoCantoAPI] Could not save daily pool: {e}")


def _load_pool(lat: float, long: float) -> tuple[list[dict], int] | tuple[None, int]:
    """
    Load today's recording pool from disk.

    Returns (recordings, next_page) if the pool exists and is less than 24h old.
    Returns (None, 1) if missing, expired, or unreadable — caller should refresh.
    The next_page value is the cursor: which page to start from on the next refresh.
    """
    path = _pool_path(lat, long)
    try:
        with open(path) as f:
            payload = json.load(f)

        age        = _time.time() - payload.get("saved_at", 0)
        recordings = payload.get("recordings", [])
        next_page  = max(1, int(payload.get("next_page", 1)))

        if age > _DAILY_POOL_TTL:
            print(f"[XenoCantoAPI] Daily pool expired ({age/3600:.1f}h old) — refresh needed.")
            return None, next_page  # Pass cursor forward even on expiry

        print(f"[XenoCantoAPI] Daily pool loaded: {len(recordings)} recordings, "
              f"{age/3600:.1f}h old, next_page={next_page}.")
        return recordings, next_page

    except FileNotFoundError:
        print(f"[XenoCantoAPI] No daily pool file found at {path} — refresh needed.")
        return None, 1
    except Exception as e:
        print(f"[XenoCantoAPI] Could not load daily pool: {e}")
        return None, 1

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _round_coord(value: float) -> float:
    return round(value, _LAT_LON_ROUND_PRECISION)


# ---------------------------------------------------------------------------
# Page cursor — persists the sliding window across daily pulls
# ---------------------------------------------------------------------------

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
        print(f"[XenoCantoAPI] Warning: recording {recording_id!r} has no file URL — skipping.")
        return None

    if file_url.startswith("//"):
        file_url = "https:" + file_url

    # Check cache before sleeping — no point in delaying a cache hit.
    try:
        req       = Request("GET", file_url).prepare()
        cache_key = _audio_cache.cache.create_key(req)
        if _audio_cache.cache.contains(cache_key):
            response = _audio_session.get(file_url, timeout=15)
            print(f"[XenoCantoAPI] Audio XC{recording_id} [cached]")
            return response.content
    except Exception:
        pass  # Fall through to live fetch below

    # Live fetch — sleep first as a courtesy to the server.
    _time.sleep(0.5)
    try:
        response = _audio_session.get(file_url, timeout=15)
        response.raise_for_status()
        print(f"[XenoCantoAPI] Audio XC{recording_id} [live]")
        return response.content
    except Exception as e:
        print(f"[XenoCantoAPI] Failed to fetch audio for XC{recording_id}: {e}")
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
            print(f"[XenoCantoAPI] API error on page {page}: {data['error']}")
            return [], 0

        recordings = data.get("recordings", [])
        num_pages  = int(data.get("numPages", 1))
        cached     = "[cached]" if getattr(response, "from_cache", False) else "[live]"

        print(f"[XenoCantoAPI] Page {page}/{num_pages}: {len(recordings)} recordings {cached}")
        return recordings, num_pages

    except Exception as e:
        print(f"[XenoCantoAPI] Request failed on page {page}: {e}")
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
            print(f"[XenoCantoAPI] Early stop: page {page} exceeds catalogue total ({num_pages_total}), stopping.")
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

    Metadata is fetched in a daily pool — a fixed window of pages from the
    xeno-canto catalogue, persisted to disk and reused across all time-tag
    refreshes within the same day. The pool is only re-fetched when it
    expires (24h) or is missing.

    The page cursor advances once per daily pool refresh, cycling through
    the full catalogue over time. It never advances mid-session.

    Audio (6h) is cached separately via requests_cache.
    """

    def __init__(self, lat: float, long: float, api_key: str):
        self.lat     = float(lat)
        self.long    = float(long)
        self.api_key = api_key

    def refresh_daily_pool(
        self,
        sound_type:    str | None = None,
        per_page:      int = 100,
        pages_per_day: int = _PAGES_PER_DAY,
    ) -> list[dict]:
        """
        Fetch a fresh window of recording metadata and persist it as today's pool.

        This is the ONLY place the page cursor advances. Called at most once
        per day — get_recordings() handles that gate automatically.

        Reads the current cursor from the pool file itself (no separate cursor
        file), fetches pages_per_day consecutive pages, advances the cursor,
        wraps to 1 at end of catalogue, and writes the pool file.
        """
        # Read cursor from pool file — no separate cursor file needed
        _, start_page = _load_pool(self.lat, self.long)

        query = _build_lat_lon_query(self.lat, self.long, sound_type)

        print(f"[XenoCantoAPI] Daily refresh: lat={self.lat}, long={self.long} "
            f"— pages {start_page}..{start_page + pages_per_day - 1}")

        all_recordings, num_pages_total = _fetch_pages(
            query=query,
            api_key=self.api_key,
            start_page=start_page,
            pages_per_day=pages_per_day,
            per_page=per_page,
        )

        if not all_recordings:
            print(f"[XenoCantoAPI] No results — widening search to ~110km radius.")
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
            print(f"[XenoCantoAPI] Cursor wrapped to 1 "
                f"(catalogue has {num_pages_total} page(s)).")

        _save_pool(all_recordings, next_page, self.lat, self.long)
        return all_recordings

    def get_recordings(self) -> list[dict]:
        """
        Return today's pool of recording metadata.

        Loads from the pool file if fresh (< 24h). Triggers a full daily
        refresh if missing or expired. Pure read from the provider's perspective
        — no cursor logic, no pagination, no side effects on a cache hit.
        """
        recordings, _ = _load_pool(self.lat, self.long)
        if recordings is None:
            recordings = self.refresh_daily_pool()
        return recordings