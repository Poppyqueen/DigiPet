"""
xeno_canto_api.py
-----------------
Wrapper around the Xeno-canto API v3.
Handles metadata fetching AND audio file fetching through requests_cache,
so expiry and on-disk cleanup are fully managed by the library — no manual
purge logic required.

Two separate CachedSessions with different expiry windows:
  _meta_session  — JSON metadata, 24-hour expiry
  _audio_session — MP3 binary responses, 24-hour expiry (same window so
                   audio files are never older than their metadata)

Both sessions call .cache.delete(expired=True) at import time to evict
stale entries accumulated from previous runs, mirroring the pattern used
by the Wikipedia and OpenMeteo providers in this project.

Parallel in design to OpenMeteoLoc — callers interact with a single
XenoCantoLoc instance initialised with lat/lon coordinates.
"""

from __future__ import annotations

import os

import requests_cache
from retry_requests import retry

import time

# ---------------------------------------------------------------------------
# Cache setup — two sessions, one expiry policy
# ---------------------------------------------------------------------------

os.makedirs(".cache", exist_ok=True)

# Metadata session — JSON API responses, 24-hour expiry.
_meta_cache = requests_cache.CachedSession(
    ".cache/xeno_canto_meta",
    backend="filesystem",
    expire_after=86400,   # 24 hours in seconds
)
_meta_cache.cache.delete(expired=True)
_meta_session = retry(_meta_cache, retries=5, backoff_factor=0.2)

# Audio session — MP3 binary downloads, same 24-hour expiry.
# requests_cache stores the raw response bytes on disk transparently;
# callers just read .content as usual.
_audio_cache = requests_cache.CachedSession(
    ".cache/xeno_canto_audio",
    backend="filesystem",
    expire_after=21600,   # 6 hours — covers longest time tag window (morning, 5h)
)
_audio_cache.cache.delete(expired=True)
_audio_session = retry(_audio_cache, retries=3, backoff_factor=0.5)

_XC_API_URL = "https://xeno-canto.org/api/3/recordings"

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

_LAT_LON_ROUND_PRECISION = 1   # round to 1 decimal ≈ 11 km — stable cache key

def _round_coord(value: float) -> float:
    return round(value, _LAT_LON_ROUND_PRECISION)


def _build_query(lat: float, lon: float, sound_type: str | None = None) -> str:
    """
    Build a xeno-canto v3 tag query string for the given coordinates.

    Uses lat+lon tags (each searches within 1 degree, ~110 km radius).
    Optionally adds a sound type filter.
    Filters for quality A or B and lengths between 15 and 120 seconds.
    Restricts to public-domain recordings where possible (lic:PD), but
    this is intentionally NOT included here — we accept all licenses and
    let the provider decide post-filtering, keeping the cache maximally reusable.
    """
    parts = [
        f"lat:{_round_coord(lat)}",
        f"lon:{_round_coord(lon)}",
        'q:">C"',           # quality A or B only
        'len:">15"',        # at least 15 seconds
        'len:"<120"',       # at most 2 minutes
    ]
    if sound_type:
        # Multi-word types must be quoted
        if " " in sound_type:
            parts.append(f'type:"{sound_type}"')
        else:
            parts.append(f"type:{sound_type}")

    return "+".join(parts)


# ---------------------------------------------------------------------------
# Audio fetch
# ---------------------------------------------------------------------------

def download_audio(recording: dict) -> bytes | None:
    """
    Fetch the audio bytes for a recording.
    The response is cached by _audio_session for 24 hours — on a cache hit
    the bytes are returned from disk with no network request.
    On expiry, requests_cache fetches fresh bytes and updates the cache
    automatically. No manual file management required.

    Xeno-canto returns protocol-relative URLs (//xeno-canto.org/…),
    so we prepend https: before fetching.

    Returns raw MP3 bytes on success, None on failure.
    """
    time.sleep(.5)
    recording_id = recording.get("id")
    file_url     = recording.get("file", "")

    if not recording_id or not file_url:
        print(f"[XenoCantoAPI] Recording {recording_id!r} has no file URL.")
        return None

    if file_url.startswith("//"):
        file_url = "https:" + file_url

    try:
        response = _audio_session.get(file_url, timeout=15)
        response.raise_for_status()
        cached_label = "[cached]" if getattr(response, "from_cache", False) else "[live]"
        print(f"[XenoCantoAPI] Audio for XC{recording_id} {cached_label}")
        return response.content
    except Exception as e:
        print(f"[XenoCantoAPI] Failed to fetch audio for XC{recording_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main API class
# ---------------------------------------------------------------------------

class XenoCantoLoc:
    """
    Fetches and caches xeno-canto recording metadata for a lat/lon location.
    Parallel in design to OpenMeteoLoc.

    Both metadata and audio are cached via requests_cache (24-hour filesystem
    cache). Expiry and cleanup are handled entirely by the library.
    """

    def __init__(self, lat, lon, api_key: str):
        self.lat     = float(lat)
        self.lon     = float(lon)
        self.api_key = api_key

    # ------------------------------------------------------------------
    # Metadata fetch
    # ------------------------------------------------------------------

    def get_recordings(
        self,
        sound_type: str | None = None,
        per_page: int = 100,
    ) -> list[dict]:
        """
        Fetch recordings near this location from the xeno-canto API.
        Results are cached for 24 hours.

        Returns a list of recording dicts as returned by the API.
        Returns an empty list on error or no results.
        """
        query = _build_query(self.lat, self.lon, sound_type)

        # params = {
        #     "query":    query,
        #     "key":      self.api_key,
        #     "per_page": per_page,
        # }

        try:
            url = f"{_XC_API_URL}?query={query}&key={self.api_key}&per_page={per_page}"
            response = _meta_session.get(url, timeout=10)
            #response = _meta_session.get(_XC_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                print(f"[XenoCantoAPI] API error: {data['error']}")
                return []

            recordings = data.get("recordings", [])
            print(
                f"[XenoCantoAPI] Fetched {len(recordings)} recordings "
                f"(total: {data.get('numRecordings', '?')}) "
                f"for lat={self.lat}, lon={self.lon}"
                + (f" type={sound_type}" if sound_type else "")
                + (" [cached]" if getattr(response, "from_cache", False) else " [live]")
            )
            return recordings

        except Exception as e:
            print(f"[XenoCantoAPI] Request failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Geographic fallback chain
    # ------------------------------------------------------------------

    def get_recordings_with_fallback(
        self,
        sound_type: str | None = None,
    ) -> list[dict]:
        """
        Try progressively wider geographic queries until we find results.

        Fallback chain:
          1. lat + lon (implicit ~1° radius)
          2. box ±5° around coordinates
          3. continent area tag
          4. empty list (genuine silence — valid perception state)
        """
        # Stage 1 — standard lat/lon query
        recordings = self.get_recordings(sound_type=sound_type)
        if recordings:
            return recordings

        print(f"[XenoCantoAPI] No results for lat/lon, trying wider box...")

        # Stage 2 — ±5° bounding box
        lat_min = round(self.lat - 5, 1)
        lat_max = round(self.lat + 5, 1)
        lon_min = round(self.lon - 5, 1)
        lon_max = round(self.lon + 5, 1)
        box_query = f"box:{lat_min},{lon_min},{lat_max},{lon_max}"
        if sound_type:
            type_tag = f'type:"{sound_type}"' if " " in sound_type else f"type:{sound_type}"
            box_query += f"+{type_tag}"
        box_query += '+q:">C"+len:">15"+len:"<120"'

        try:

            url = f"{_XC_API_URL}?query={box_query}&key={self.api_key}&per_page=100"
            response = _meta_session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            recordings = data.get("recordings", [])
            if recordings:
                print(f"[XenoCantoAPI] Box fallback returned {len(recordings)} recordings.")
                return recordings
        except Exception as e:
            print(f"[XenoCantoAPI] Box fallback failed: {e}")

        print(f"[XenoCantoAPI] No results for box, trying continent area...")

        # Stage 3 — continent area
        area = _lat_lon_to_area(self.lat, self.lon)
        if area:
            area_query = f"area:{area}+q:\">C\"+len:\">15\"+len:\"<120\""
            if sound_type:
                type_tag = f'type:"{sound_type}"' if " " in sound_type else f"type:{sound_type}"
                area_query += f"+{type_tag}"
            try:

                url = f"{_XC_API_URL}?query={area_query}&key={self.api_key}&per_page=100"
                response = _meta_session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                recordings = data.get("recordings", [])
                if recordings:
                    print(f"[XenoCantoAPI] Area fallback ({area}) returned {len(recordings)} recordings.")
                    return recordings
            except Exception as e:
                print(f"[XenoCantoAPI] Area fallback failed: {e}")

        # Stage 4 — genuine silence
        print(f"[XenoCantoAPI] All fallbacks exhausted — no recordings found.")
        return []


# ---------------------------------------------------------------------------
# Continent lookup (simple bounding box, good enough for area tag)
# ---------------------------------------------------------------------------

def _lat_lon_to_area(lat: float, lon: float) -> str | None:
    """
    Very coarse lat/lon → xeno-canto area tag mapping.
    Covers the five valid area values: africa, america, asia, australia, europe.
    Returns None if the point doesn't fall clearly into any region
    (e.g. middle of the ocean).
    """
    if -35 <= lat <= 37 and -20 <= lon <= 52:
        return "africa"
    if -56 <= lat <= 72 and -170 <= lon <= -34:
        return "america"
    if 1 <= lat <= 77 and 26 <= lon <= 180:
        return "asia"
    if -47 <= lat <= -10 and 113 <= lon <= 154:
        return "australia"
    if 35 <= lat <= 72 and -25 <= lon <= 45:
        return "europe"
    # Overlap fallback — broad america catch (covers more of South America)
    if -56 <= lat <= 15 and -82 <= lon <= -34:
        return "america"
    return None