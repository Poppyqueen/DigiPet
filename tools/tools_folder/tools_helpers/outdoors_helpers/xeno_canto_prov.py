"""
xeno_canto_prov.py
------------------
OutdoorsProvider implementation for Xeno-canto wildlife sounds.

Plugs into the OutdoorsPerception framework exactly like EarthWeatherProvider.
outdoors_type identifier: "xeno-canto"

Responsibilities
----------------
- Fetch and filter recording metadata via XenoCantoLoc
- Maintain an active selection of N recordings (randomly weighted by time of day)
- Track a playback index so each look_through_aperture call plays a different sound
- Provide get_limited_perception() and get_full_perception() text
- Expose get_sound_bytes() for look_through_aperture to fire play_sound signal

Cache behaviour
---------------
Metadata  : requests_cache, 24-hour filesystem cache (handled by XenoCantoLoc)
Audio     : requests_cache, 24-hour filesystem cache (handled by XenoCantoLoc)
            Both expire and are cleaned up automatically — no manual purge needed.
Selection : in-memory, re-drawn on each time-tag transition.
            The underlying metadata cache (24h) is a separate concern —
            the same 100 recordings are reused across tag transitions within a day,
            only the weighted random draw changes.
"""

from __future__ import annotations

import random
import threading

from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider
from utils.xeno_canto_api import (
    XenoCantoLoc,
    download_audio,
    _audio_cache,
)
from utils.time_manager import get_time_tag_from_now
import json
import time

_SELECTION_CACHE_PATH = ".cache/xeno_canto_selection.json"
_SELECTION_TTL = 86400  # 24 hours — matches metadata cache


def _save_selection(selection: list[dict], time_tag: str) -> None:
    try:
        payload = {
            "time_tag":  time_tag,
            "saved_at":  time.time(),
            "selection": selection,
        }
        with open(_SELECTION_CACHE_PATH, "w") as f:
            json.dump(payload, f)
        print(f"[XenoCantoProvider] Selection persisted to disk "
              f"({len(selection)} recordings, tag={time_tag!r}).")
    except Exception as e:
        print(f"[XenoCantoProvider] Could not persist selection: {e}")


def _load_selection(current_time_tag: str) -> list[dict] | None:
    try:
        with open(_SELECTION_CACHE_PATH) as f:
            payload = json.load(f)
        age     = time.time() - payload.get("saved_at", 0)
        tag     = payload.get("time_tag")
        saved   = payload.get("selection", [])

        if age > _SELECTION_TTL:
            print("[XenoCantoProvider] Persisted selection expired.")
            return None
        if tag != current_time_tag:
            print(f"[XenoCantoProvider] Persisted selection time tag mismatch "
                  f"({tag!r} vs {current_time_tag!r}).")
            return None

        print(f"[XenoCantoProvider] Loaded persisted selection "
              f"({len(saved)} recordings, tag={tag!r}, "
              f"age={int(age)}s).")
        return saved
    except FileNotFoundError:
        print("[XenoCantoProvider] No persisted selection found.")
        return None
    except Exception as e:
        print(f"[XenoCantoProvider] Could not load persisted selection: {e}")
        return None

# ---------------------------------------------------------------------------
# Selection parameters
# ---------------------------------------------------------------------------

_SELECTION_SIZE = 8   # how many recordings to keep in the active pool

# ---------------------------------------------------------------------------
# Always-excluded sound types (applied before any scoring)
# ---------------------------------------------------------------------------

_ALWAYS_EXCLUDE: set[str] = {
    "imitation",
    "distress call",
}

# ---------------------------------------------------------------------------
# Time-of-day blacklist — types excluded only during certain periods
# ---------------------------------------------------------------------------

_TIME_BLACKLIST: dict[str, set[str]] = {
    "late night":     set(),
    "early morning":  {"nocturnal flight call"},
    "morning":        {"nocturnal flight call"},
    "noon":           {"nocturnal flight call", "dawn song"},
    "afternoon":      {"nocturnal flight call", "dawn song"},
    "late afternoon": {"nocturnal flight call", "dawn song"},
    "night":          set(),
}

# ---------------------------------------------------------------------------
# Time-of-day preference weights
# Additive bumps on top of a 1.0 baseline — nothing is ever forced,
# just made more likely. Higher value = stronger preference.
# ---------------------------------------------------------------------------

_TIME_PREFERENCES: dict[str, dict[str, float]] = {
    "late night": {
        "nocturnal flight call": 1.5,
        "call":                  0.5,
        "social call":           0.3,
        "echolocation":          0.8,   # bats are very active at night
        "feeding buzz":          0.6,
    },
    "early morning": {
        "dawn song":    2.0,   # strong pull — iconic dawn chorus moment
        "song":         1.0,
        "flight song":  0.5,
        "call":         0.3,
        "duet":         0.4,
    },
    "morning": {
        "song":         1.0,
        "call":         0.5,
        "flight call":  0.3,
        "duet":         0.4,
        "territorial call": 0.3,
    },
    "noon": {
        "call":         0.5,
        "song":         0.3,
        "alarm call":   0.2,
    },
    "afternoon": {
        "call":         0.5,
        "song":         0.3,
        "territorial call": 0.4,
        "alarm call":   0.2,
    },
    "late afternoon": {
        "call":         0.5,
        "song":         0.4,
        "flight call":  0.3,
        "subsong":      0.4,   # birds winding down — quieter, more meandering
    },
    "night": {
        "nocturnal flight call": 1.2,
        "call":                  0.4,
        "song":                  0.2,   # some species do sing at night
        "echolocation":          0.8,
        "feeding buzz":          0.6,
    },
}


# ---------------------------------------------------------------------------
# Weighting helpers
# ---------------------------------------------------------------------------

def _score_recording(recording: dict, time_tag: str) -> float:
    base = 1.0

    # Type-based preference bump (existing)
    sound_type = recording.get("type", "").lower()
    preferred  = _TIME_PREFERENCES.get(time_tag, {})
    base += preferred.get(sound_type, 0.0)

    # Time proximity bump — recordings made near the current hour score higher
    rec_time = recording.get("time", "")
    if rec_time:
        try:
            from utils.loc_datetime import datetime as loc_datetime
            now_hour = loc_datetime.now().hour
            rec_hour  = int(rec_time.split(":")[0])
            distance  = min(abs(now_hour - rec_hour), 24 - abs(now_hour - rec_hour))
            # max bump of 1.0 for exact match, 0 for 12 hours away
            base += max(0.0, 1.0 - (distance / 12.0))
        except Exception:
            pass  # malformed time field — just skip the bump

    return base


def _filter_recordings(recordings: list[dict], time_tag: str) -> list[dict]:
    """
    Remove always-excluded types and time-specific blacklisted types.
    Returns the filtered list.
    """
    time_blacklist = _TIME_BLACKLIST.get(time_tag, set())
    before = len(recordings)
    result = []
    for r in recordings:
        sound_type = r.get("type", "").lower()
        if sound_type in _ALWAYS_EXCLUDE:
            continue
        if sound_type in time_blacklist:
            continue
        result.append(r)
    print(f"[XenoCantoProvider] Filter: {before} → {len(result)} recordings "
          f"(time_tag={time_tag!r})")
    return result


def _weighted_sample(recordings: list[dict], time_tag: str, k: int) -> list[dict]:
    """
    Draw k unique recordings from the list using time-of-day preference weights.
    Falls back to unweighted sample if k >= len(recordings).
    """
    if not recordings:
        print("[XenoCantoProvider] Weighted sample: no recordings to sample from.")
        return []

    k = min(k, len(recordings))

    if k == len(recordings):
        print(f"[XenoCantoProvider] Weighted sample: pool size == k ({k}), returning all.")
        return list(recordings)

    weights = [_score_recording(r, time_tag) for r in recordings]

    # random.choices allows replacement — oversample then deduplicate
    oversample = random.choices(recordings, weights=weights, k=k * 4)
    seen:   set[str]  = set()
    result: list[dict] = []
    for r in oversample:
        rid = r.get("id", "")
        if rid and rid not in seen:
            seen.add(rid)
            result.append(r)
        if len(result) == k:
            break

    # Top-up with anything remaining if we fell short (rare)
    if len(result) < k:
        remaining = [r for r in recordings if r.get("id", "") not in seen]
        result.extend(remaining[: k - len(result)])
        print(f"[XenoCantoProvider] Weighted sample: topped up to {len(result)} "
              f"(oversampling fell short).")

    print(f"[XenoCantoProvider] Weighted sample: drew {len(result)} from "
          f"{len(recordings)} candidates.")
    return result


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class XenoCantoProvider(OutdoorsProvider):
    """
    Outdoors provider for Xeno-canto wildlife sound recordings.

    outdoors_type identifier: "xeno-canto"

    get_limited_perception()  — short ambient text, no sound played
    get_full_perception()     — species list with sound type detail
    get_sound_bytes()         — returns audio bytes for the current selection
                                index; advances the index. Overrides the ABC
                                default (returns None) to provide actual audio.
    """

    outdoors_type = "xeno-canto"

    def __init__(self, xeno_canto_loc: XenoCantoLoc):
        print("[XenoCantoProvider] Initialising provider.")
        self._loc                          = xeno_canto_loc
        self._active_selection: list[dict] = []
        self._selection_index: int         = 0
        self._active_time_tag: str | None  = None   # tracks last draw's time tag
        self._lock                         = threading.Lock()
        print(f"[XenoCantoProvider] Ready. lat={xeno_canto_loc.lat}, "
              f"lon={xeno_canto_loc.lon}")

    # ------------------------------------------------------------------
    # Selection management
    # ------------------------------------------------------------------

    def _evict_selection_audio(self, selection: list[dict]) -> None:
        """
        Explicitly evict audio cache entries for the given selection.
        Called before overwriting _active_selection so stale audio bytes
        are freed immediately rather than waiting for the 24-hour TTL.
        Safe to call with an empty list — the guard handles it cleanly.
        """
        if not selection:
            return
        urls = []
        for r in selection:
            file_url = r.get("file", "")
            if file_url.startswith("//"):
                file_url = "https:" + file_url
            if file_url:
                urls.append(file_url)
        if urls:
            try:
                _audio_cache.cache.delete(urls=urls)
                print(f"[XenoCantoProvider] Evicted {len(urls)} audio cache entries "
                      f"for previous selection.")
            except Exception as e:
                print(f"[XenoCantoProvider] Audio eviction error (non-fatal): {e}")

    def _refresh_selection(self) -> None:
        time_tag = get_time_tag_from_now() or "morning"
        print(f"[XenoCantoProvider] Current time tag: {time_tag!r}")

        # Try to restore selection from disk before doing a fresh draw
        restored = _load_selection(time_tag)
        if restored:
            with self._lock:
                old_selection = list(self._active_selection)
            self._evict_selection_audio(old_selection)
            with self._lock:
                self._active_selection = restored
                self._selection_index  = 0
                self._active_time_tag  = time_tag
            print(f"[XenoCantoProvider] Restored selection from disk — "
                f"skipping fresh draw and prefetch.")
            return

        # No valid persisted selection — do a fresh draw
        recordings = self._loc.get_recordings_with_fallback()
        filtered   = _filter_recordings(recordings, time_tag)
        selection  = _weighted_sample(filtered, time_tag, k=_SELECTION_SIZE)

        with self._lock:
            old_selection = list(self._active_selection)
        self._evict_selection_audio(old_selection)

        with self._lock:
            self._active_selection = selection
            self._selection_index  = 0
            self._active_time_tag  = time_tag

        # Persist the new selection so restarts can reuse it
        _save_selection(selection, time_tag)

        if selection:
            print(f"[XenoCantoProvider] New selection ({len(selection)} recordings) "
                f"for time_tag={time_tag!r}:")
            for r in selection:
                print(f"  XC{r.get('id')} — {r.get('en', '?')} "
                    f"({r.get('gen', '')} {r.get('sp', '')}) "
                    f"type={r.get('type', '?')} q={r.get('q', '?')}")
            self._prefetch_audio_async(selection)
        else:
            print("[XenoCantoProvider] Selection is empty — no recordings available.")

    def _prefetch_audio_async(self, selection: list[dict]) -> None:
        """Warm the audio cache for the active selection in a background thread."""
        print(f"[XenoCantoProvider] Starting background audio prefetch "
              f"for {len(selection)} recordings...")
        def _download_all():
            for recording in selection:
                print(f"[XenoCantoProvider] Prefetching XC{recording.get('id')}...")
                download_audio(recording)
            print("[XenoCantoProvider] Background audio prefetch complete.")
        threading.Thread(target=_download_all, daemon=True).start()

    def _ensure_selection(self) -> None:
        """
        Populate or refresh the selection if:
          - it is empty (first call / cold start), or
          - the current time tag has changed since the last draw.
        """
        current_tag = get_time_tag_from_now() or "morning"
        with self._lock:
            needs_refresh = (
                not self._active_selection
                or self._active_time_tag != current_tag
            )
        if needs_refresh:
            print(f"[XenoCantoProvider] Selection needs refresh "
                  f"(active_tag={self._active_time_tag!r}, "
                  f"current_tag={current_tag!r})")
            self._refresh_selection()
        else:
            print(f"[XenoCantoProvider] Selection still valid for "
                  f"time_tag={current_tag!r} "
                  f"({len(self._active_selection)} recordings, "
                  f"index={self._selection_index})")

    # ------------------------------------------------------------------
    # OutdoorsProvider interface
    # ------------------------------------------------------------------

    def get_limited_perception(self) -> str:
        """
        Short ambient text for window_perception().
        The agent is near a window but has not actively looked through it.
        Returns a brief sense of wildlife presence without species detail.
        """
        print("[XenoCantoProvider] get_limited_perception() called.")
        self._ensure_selection()

        with self._lock:
            selection = list(self._active_selection)

        if not selection:
            return "The outside world sounds quiet — no wildlife stirs near this opening."

        time_tag     = get_time_tag_from_now() or "morning"
        species_hint = _build_species_hint(selection)
        mood         = _TIME_MOOD.get(time_tag, "alive with the sounds of nature")

        result = (
            f"Through the opening, the outside world feels {mood}. "
            f"You catch a fleeting impression of wildlife nearby"
            + (f" — {species_hint}" if species_hint else "")
            + "."
        )
        print(f"[XenoCantoProvider] Limited perception: {result[:80]}...")
        return result

    def get_full_perception(self) -> str:
        self._ensure_selection()

        with self._lock:
            selection = list(self._active_selection)
            index     = self._selection_index

        if not selection:
            return "No wildlife sounds are detectable in this area."

        r          = selection[index % len(selection)]
        name       = r.get("en") or f"{r.get('gen', '')} {r.get('sp', '')}".strip()
        sound_type = r.get("type", "unknown")
        grp        = r.get("grp", "")
        group_note = f" [{grp}]" if grp and grp != "birds" else ""

        return f"Nearby you can hear a {name}{group_note} — {sound_type}."

    # ------------------------------------------------------------------
    # Sound playback — overrides OutdoorsProvider.get_sound_bytes()
    # ------------------------------------------------------------------

    def get_sound_bytes(self) -> bytes | None:
        """
        Return the raw MP3 bytes for the current selection index,
        then advance the index (cycling with wraparound).

        Overrides the ABC default (returns None) to provide actual audio.
        Audio is served from requests_cache — no manual file management.
        Returns None if the selection is empty or the fetch fails.

        Called exclusively from OutdoorsPerception.look_through_aperture().
        """
        print("[XenoCantoProvider] get_sound_bytes() called.")
        self._ensure_selection()

        with self._lock:
            selection = list(self._active_selection)
            index     = self._selection_index

        if not selection:
            print("[XenoCantoProvider] get_sound_bytes: selection empty, returning None.")
            return None

        recording  = selection[index % len(selection)]
        next_index = (index + 1) % len(selection)

        with self._lock:
            self._selection_index = next_index

        print(f"[XenoCantoProvider] get_sound_bytes: fetching index {index} → "
              f"XC{recording.get('id')} — {recording.get('en', '?')} "
              f"({recording.get('type', '?')}). "
              f"Next index will be {next_index}.")

        audio_bytes = download_audio(recording)
        smp = int(recording.get("smp", 44100))

        if audio_bytes:
            print(f"[XenoCantoProvider] Audio ready: {len(audio_bytes)} bytes.")
        else:
            print(f"[XenoCantoProvider] Audio unavailable for "
                  f"XC{recording.get('id')} — skipping sound.")
        return audio_bytes, smp


# ---------------------------------------------------------------------------
# Perception text helpers
# ---------------------------------------------------------------------------

_TIME_MOOD: dict[str, str] = {
    "late night":     "hushed, with only the faintest nocturnal stirrings",
    "early morning":  "alive with the swelling of the dawn chorus",
    "morning":        "bright and full of birdsong",
    "noon":           "warm and punctuated by occasional calls",
    "afternoon":      "settled, with scattered wildlife activity",
    "late afternoon": "gently winding down as the day cools",
    "night":          "quiet, with the occasional cry in the darkness",
}


def _build_species_hint(selection: list[dict]) -> str:
    """
    Build a short natural-language species hint from the selection,
    e.g. 'a wren, two sparrows, and a bat'.
    Returns an empty string if no recognisable names are available.
    """
    names = []
    for r in selection:
        name = r.get("en", "").strip()
        if name:
            names.append(name.lower())

    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _collect_also_species(selection: list[dict]) -> list[str]:
    """
    Collect unique background species names from the 'also' field
    across all recordings in the selection.
    """
    seen:   set[str]  = set()
    result: list[str] = []
    for r in selection:
        for species in r.get("also", []):
            if species and species not in seen:
                seen.add(species)
                result.append(species)
    return result