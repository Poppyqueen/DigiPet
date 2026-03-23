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
- Advance _selection_index via tick() — index duration is proportional to recording length
- Provide get_limited_perception() and get_full_perception() as pure readers of current state
- get_full_perception() returns audio bytes directly — no separate get_sound_bytes()

Tick behaviour
--------------
tick() is the only method that mutates _selection_index, _ticks_on_current,
_activity_level, and _active_time_tag_for_activity.
get_limited_perception() and get_full_perception() are fully side-effect free —
they read the current index, activity level, and time tag, then return a result.

Activity level
--------------
tick() rolls a single float in [0, 1) into _activity_level each tick and stores
the current time tag in _active_time_tag_for_activity. Perception methods compare
this value against their respective thresholds:
  - _ACTIVITY_THRESHOLD_FULL    — for get_full_perception()
  - _ACTIVITY_THRESHOLD_LIMITED — for get_limited_perception()
A reading *above* the threshold means wildlife is quiet right now; at or below
means something is perceptible.  Higher threshold → more often perceptible.

Weather integration
-------------------
XenoCantoProvider optionally accepts an OpenMeteoLoc instance at construction.
Weather context is refreshed on each selection rebuild (cached at 15 min by
OpenMeteo, so the call is free). It influences two independent axes:

  score_multiplier (wind-only):
    Scales individual recording scores before sampling, biasing the selection
    away from delicate sounds in high wind. Rain is NO LONGER included here —
    it is handled per-type via the binary modifier tables below.

  Binary condition modifier tables:
    _RAIN_SCORE_MODIFIERS and _RAIN_THRESHOLD_MODIFIERS apply per recording
    type token when rain is active. Types like "advertisement call" (frogs) get
    a boost; delicate types like "subsong" are heavily penalised. Tokens absent
    from a table receive a neutral 1.0 factor.
    This design is easy to extend: add _WIND_SCORE_MODIFIERS, _FROST_*, etc.
    by following the same pattern and calling _apply_condition_modifier() in
    the relevant place.

  threshold_multiplier:
    Now computed per-recording rather than globally. The current recording's
    type tokens are looked up in _RAIN_THRESHOLD_MODIFIERS (and future tables)
    and the best-matching modifier is applied to the base activity threshold.
    This means frogs seem more active in rain while warblers seem quieter,
    rather than everything being suppressed uniformly.

Type matching
-------------
xeno-canto's `type` field is free text and frequently arrives as a
comma-delimited compound string, e.g. "call, flight call, wing beats".
Scoring and filtering both tokenise this field and operate on individual
tokens, so compound types are handled correctly.

The predefined "core" tokens that xeno-canto uses as standard terms are:
  song, call, alarm call, flight call, flight song, nocturnal flight call,
  dawn song, subsong, social call, begging call, drumming, duet,
  territorial call, echolocation, feeding buzz.
All other content is recordist free text and treated as an unknown token
that simply scores 0.0 preference — it does not trigger exclusion.

Cache behaviour
---------------
Metadata  : requests_cache, 24-hour filesystem cache (handled by XenoCantoLoc)
Audio     : requests_cache, 6-hour filesystem cache (handled by XenoCantoLoc)
            Both expire and are cleaned up automatically via .delete(expired=True).
            Audio eviction on selection change uses create_key() — the only
            correct approach for the filesystem backend (delete(urls=...) is
            a SQLite-only API and silently no-ops on filesystem).
Selection : in-memory + persisted JSON (.cache/xeno_canto_selection.json).
            Re-drawn on each time-tag transition.
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from datetime import datetime

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
_SELECTION_TTL        = 21600  # 6 hours

# ---------------------------------------------------------------------------
# Tick constants
# ---------------------------------------------------------------------------

_SECONDS_PER_TICK: int = 120

_DEFAULT_TICKS_PER_RECORDING: int = 3
_MIN_TICKS_PER_RECORDING: int     = 2
_MAX_TICKS_PER_RECORDING: int     = 5

# ---------------------------------------------------------------------------
# Selection parameters
# ---------------------------------------------------------------------------

# Base selection size by time tag — dawn chorus warrants a larger pool.
_SELECTION_SIZE_BY_TAG: dict[str, int] = {
    "early morning": 12,
    "morning":       10,
    "late afternoon": 12,
}
_SELECTION_SIZE_DEFAULT: int = 8

# How much bad weather can shrink the selection (proportional to conditions).
# Rain or strong wind mean fewer species are audible, so a smaller pool
# is more realistic than sampling the same N recordings with lower scores.
_SELECTION_SIZE_RAIN_FACTOR: float = 0.6    # e.g. 10 → 6 in rain
_SELECTION_SIZE_WIND_THRESHOLD: float = 25.0  # km/h above which wind shrinks pool
_SELECTION_SIZE_WIND_FACTOR: float = 0.75   # e.g. 10 → 7-8 in strong wind

# ---------------------------------------------------------------------------
# xeno-canto core type vocabulary
#
# xeno-canto's type field is free text. The terms below are the semi-standard
# predefined tokens used across the database. Any token not in this set is
# recordist free text — it scores 0.0 preference but does NOT trigger exclusion.
# Compound types ("call, flight call") are split and matched token-by-token.
# ---------------------------------------------------------------------------

_XC_CORE_TYPES: frozenset[str] = frozenset({
    "aberrant",
    "advertisement call",
    "agonistic call",
    "alarm call",
    "begging call",
    "call",
    "calling song",
    "courtship song",
    "dawn song",
    "defensive call",
    "distress call",
    "disturbance song",
    "drumming",
    "duet",
    "echolocation",
    "feeding buzz",
    "female song",
    "flight call",
    "flight song",
    "imitation",
    "mating call",
    "mechanical sound",
    "nocturnal flight call",
    "release call",
    "rivalry song",
    "searching song",
    "social call",
    "song",
    "subsong",
    "territorial call",
})

# ---------------------------------------------------------------------------
# Always-excluded sound types (applied before any scoring)
# Matched against individual tokens, not the full compound string.
# ---------------------------------------------------------------------------

_ALWAYS_EXCLUDE_TOKENS: set[str] = {
    "release call"
}

# ---------------------------------------------------------------------------
# Time-of-day blacklist — types excluded only during certain periods.
# Matched against individual tokens.
# ---------------------------------------------------------------------------

_TIME_BLACKLIST: dict[str, set[str]] = {
    "late night":     set(),
    "early morning":  {"nocturnal flight call"},
    "morning":        {"nocturnal flight call"},
    "noon":           {"nocturnal flight call", "dawn song"},
    "afternoon":      {"nocturnal flight call", "dawn song"},
    "late afternoon": {"nocturnal flight call"},
    "night":          set(),
}

# ---------------------------------------------------------------------------
# Time-of-day preference weights
# Keys are individual core type tokens.
# Compound types are split before lookup — the best matching token wins.
# ---------------------------------------------------------------------------

_TIME_PREFERENCES = {
    "late night": {
        "nocturnal flight call": 3.0,
        "flight call":           2.0,
        "echolocation":          2.5,
        "feeding buzz":          2.0,
        "call":                  0.3,
        "song":                  0.2,
        "advertisement call":    1.5,
        "mating call":           1.5,
    },
    "early morning": {
        "dawn song":       4.0,
        "song":            2.5,
        "duet":            3.0,
        "flight song":     1.5,
        "courtship song":  2.0,
        "rivalry song":    1.5,
        "drumming":        2.0,
        "call":            0.8,
        "flight call":     1.0,
        "advertisement call": 1.0,
    },
    "morning": {
        "song":             1.5,
        "territorial call": 3.0,
        "rivalry song":     2.5,
        "agonistic call":   2.0,
        "drumming":         2.5,
        "call":             1.0,
        "flight call":      0.5,
        "duet":             1.5,
        "alarm call":       1.0,
        "female song":      1.0,
    },
    "noon": {
        "call":         0.8,
        "begging call": 2.5,
        "alarm call":   0.5,
        "song":         0.3,
        "calling song": 1.5,
        "mechanical sound": 0.8,
    },
    "afternoon": {
        "call":             1.0,
        "territorial call": 1.5,
        "begging call":     2.0,
        "alarm call":       1.5,
        "calling song":     2.0,
        "song":             0.5,
        "agonistic call":   1.0,
    },
    "late afternoon": {
        "song":           1.5,
        "subsong":        2.0,
        "call":           1.0,
        "social call":    2.0,
        "flight call":    1.0,
        "echolocation":   1.5,
        "feeding buzz":   1.0,
        "advertisement call": 1.5,
        "flight song":    1.0,
    },
    "night": {
        "song":                  1.0,
        "nocturnal flight call": 2.0,
        "flight call":           1.5,
        "echolocation":          2.5,
        "feeding buzz":          2.0,
        "advertisement call":    2.5,
        "mating call":           2.0,
        "social call":           1.0,
        "call":                  0.5,
    },
}

# ---------------------------------------------------------------------------
# Binary condition modifier tables
#
# Each table maps individual type tokens to a float multiplier applied when
# that condition is active.  Values > 1.0 are boosts; < 1.0 are penalties.
# Tokens absent from a table receive a neutral 1.0 (no effect).
#
# SCORE modifiers are applied in _score_recording() instead of the old flat
# rain_multiplier — so harsh conditions suppress fragile types while boosting
# robust or rain-loving ones.
#
# THRESHOLD modifiers are applied per-recording in get_full_perception() and
# get_limited_perception() — the current recording's tokens are looked up and
# the best-matching modifier scales the base activity threshold up or down.
# A boost (> 1.0) means that type seems MORE active under this condition;
# a penalty (< 1.0) means it seems quieter.
#
# To add a new condition (frost, fog, heat, etc.), add a pair of tables and
# call _apply_condition_modifier() in _score_recording() and _threshold_for().
# ---------------------------------------------------------------------------

# Rain — score modifiers
_RAIN_SCORE_MODIFIERS: dict[str, float] = {
    # Amphibian callers surge — rain is their prime cue
    "advertisement call": 2.0,
    "mating call":        1.8,
    # Structurally loud / broadband — rain doesn't mask them much
    "drumming":           1.0,   # neutral: woodpeckers drum in light rain
    "echolocation":       1.0,   # bats unaffected by rain (hunt insects flushed by it)
    "feeding buzz":       1.1,
    # Generalist calls tolerate rain moderately
    "alarm call":         0.8,
    "mechanical sound":   0.8,
    "flight call":        0.6,
    "call":               0.5,
    "nocturnal flight call": 0.5,
    # Melodic / delicate sounds are heavily masked
    "territorial call":   0.4,
    "rivalry song":       0.35,
    "song":               0.3,
    "courtship song":     0.25,
    "dawn song":          0.2,
    "subsong":            0.15,
    "duet":               0.2,
    "female song":        0.25,
}

# Rain — threshold modifiers (applied to base activity threshold per recording)
# > 1.0 → type heard MORE often in rain; < 1.0 → heard LESS often
_RAIN_THRESHOLD_MODIFIERS: dict[str, float] = {
    "advertisement call": 1.6,   # frogs go wild in rain
    "mating call":        1.5,
    "echolocation":       1.1,   # bats slightly more active (flushed insects)
    "feeding buzz":       1.0,
    "drumming":           1.0,
    "alarm call":         0.7,
    "flight call":        0.6,
    "call":               0.5,
    "song":               0.35,
    "dawn song":          0.25,
    "subsong":            0.2,
    "duet":               0.25,
    "courtship song":     0.3,
    "rivalry song":       0.3,
}

# High wind — score modifiers
# Wind masks high-frequency and quiet sounds; broadband / loud sounds survive better.
_WIND_SCORE_MODIFIERS: dict[str, float] = {
    "drumming":           0.9,   # loud mechanical, survives wind reasonably
    "alarm call":         0.85,
    "echolocation":       0.8,
    "mechanical sound":   0.8,
    "flight call":        0.7,
    "call":               0.65,
    "advertisement call": 0.6,
    "mating call":        0.6,
    "song":               0.45,
    "territorial call":   0.45,
    "rivalry song":       0.4,
    "courtship song":     0.35,
    "dawn song":          0.3,
    "subsong":            0.2,
    "duet":               0.3,
    "female song":        0.35,
    "social call":        0.5,
}

# High wind — threshold modifiers
_WIND_THRESHOLD_MODIFIERS: dict[str, float] = {
    "drumming":           0.9,
    "alarm call":         0.8,
    "echolocation":       0.9,
    "flight call":        0.7,
    "call":               0.6,
    "song":               0.4,
    "dawn song":          0.3,
    "subsong":            0.2,
    "advertisement call": 0.55,
    "mating call":        0.55,
}


def _apply_condition_modifier(
    tokens: list[str],
    table: dict[str, float],
    neutral: float = 1.0,
) -> float:
    """
    Return the best (most extreme from neutral) modifier for any token
    in *tokens* found in *table*.  Tokens absent from the table return
    *neutral*.  "Best" is defined as furthest from 1.0 — i.e. the largest
    boost or the largest penalty wins, whichever is more significant.
    """
    best = neutral
    for tok in tokens:
        val = table.get(tok, neutral)
        if abs(val - 1.0) > abs(best - 1.0):
            best = val
    return best


# ---------------------------------------------------------------------------
# Wildlife activity thresholds
# ---------------------------------------------------------------------------

_ACTIVITY_THRESHOLD_FULL: dict[str, float] = {
    "late night":     1 / 4,
    "early morning":  9 / 10,
    "morning":        4 / 5,
    "noon":           2 / 5,
    "afternoon":      1 / 2,
    "late afternoon": 3 / 4,
    "night":          2 / 3,
}

_ACTIVITY_THRESHOLD_LIMITED: dict[str, float] = {
    "late night":     1 / 8,
    "early morning":  3 / 10,
    "morning":        1 / 4,
    "noon":           1 / 5,
    "afternoon":      1 / 5,
    "late afternoon": 1 / 4,
    "night":          1 / 6,
}


def _threshold_for(
    base_table: dict[str, float],
    time_tag: str,
    default: float,
    tokens: list[str],
    weather: WeatherContext,
) -> float:
    """
    Compute the effective activity threshold for a specific recording.

    Starts from the base time-of-day threshold, then applies per-type
    condition modifiers so that rain-loving types (frogs) seem more active
    in rain while delicate singers seem quieter — rather than everything
    being suppressed or boosted uniformly.

    Condition modifiers are applied multiplicatively in priority order:
      rain (binary) → wind (if above threshold)
    Each modifier is derived from the recording's type tokens via
    _apply_condition_modifier(), so compound types are handled correctly.
    """
    threshold = base_table.get(time_tag, default)

    if weather.is_raining:
        threshold *= _apply_condition_modifier(tokens, _RAIN_THRESHOLD_MODIFIERS)

    if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
        threshold *= _apply_condition_modifier(tokens, _WIND_THRESHOLD_MODIFIERS)

    return threshold


# ---------------------------------------------------------------------------
# Weather context
# ---------------------------------------------------------------------------

@dataclass
class WeatherContext:
    """
    Snapshot of current weather conditions used to modulate scoring and
    activity thresholds. Constructed from OpenMeteoLoc.get_structured_weather().
    Defaults represent calm, mild, dry conditions — used when no OpenMeteoLoc
    is available.

    score_multiplier is now wind-only. Rain is handled per-type via
    _RAIN_SCORE_MODIFIERS in _score_recording(), so rain-loving types
    (frogs, bats) are boosted while delicate singers are penalised.
    """
    wind_speed:    float = 0.0    # km/h
    precipitation: float = 0.0    # mm (current reading — binary in effect)
    cloud_cover:   float = 0.0    # 0–100 %
    temperature:   float = 15.0   # °C apparent
    is_day:        bool  = True

    @property
    def is_raining(self) -> bool:
        """True if any meaningful precipitation is occurring."""
        return (self.precipitation or 0.0) > 0.1

    @property
    def wind_multiplier(self) -> float:
        """
        Smooth penalty on score based on wind speed.
        Calm (0 km/h) → 1.0. Moderate (20 km/h) → ~0.75. Strong (40+ km/h) → 0.4.
        Applied as a global score floor — per-type wind detail lives in
        _WIND_SCORE_MODIFIERS which is applied additively in _score_recording().
        """
        spd = self.wind_speed or 0.0
        if spd < 5.0:
            return 1.0
        return max(0.4, 1.0 - (spd / 65.0))

    @property
    def score_multiplier(self) -> float:
        """
        Global score multiplier — wind only.
        Rain is no longer included here; it is applied per-type in
        _score_recording() via _RAIN_SCORE_MODIFIERS.
        """
        return self.wind_multiplier


# ---------------------------------------------------------------------------
# Tick duration helpers
# ---------------------------------------------------------------------------

def _parse_length_seconds(length_str: str) -> int | None:
    if not length_str:
        return None
    try:
        parts = length_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def _ticks_for_recording(recording: dict) -> int:
    seconds = _parse_length_seconds(recording.get("length", ""))
    if seconds is None:
        return _DEFAULT_TICKS_PER_RECORDING
    ticks = max(1, round(seconds / _SECONDS_PER_TICK))
    return max(_MIN_TICKS_PER_RECORDING, min(_MAX_TICKS_PER_RECORDING, ticks))


# ---------------------------------------------------------------------------
# Type tokenisation
# ---------------------------------------------------------------------------

def _tokenise_type(raw_type: str) -> list[str]:
    """
    Split a xeno-canto type string into individual tokens.

    xeno-canto records types as free text, often comma-separated:
      "call"                            → ["call"]
      "call, flight call"               → ["call", "flight call"]
      "call, jet, keer, groan calls,"   → ["call", "jet", "keer", "groan calls"]

    Tokens are lowercased and stripped. Empty tokens after splitting are dropped.
    Multi-word tokens like "flight call" are preserved — they match the
    multi-word keys in _TIME_PREFERENCES and _XC_CORE_TYPES.
    """
    if not raw_type:
        return []
    return [t.strip().rstrip(",") for t in raw_type.lower().split(",") if t.strip().rstrip(",")]


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def _recording_is_excluded(recording: dict, time_tag: str) -> bool:
    tokens = _tokenise_type(recording.get("type", ""))
    for tok in tokens:
        if tok in _ALWAYS_EXCLUDE_TOKENS:
            return True
    blacklist = _TIME_BLACKLIST.get(time_tag, set())
    for tok in tokens:
        if tok in blacklist:
            return True
    return False


def _filter_recordings(recordings: list[dict], time_tag: str) -> list[dict]:
    before = len(recordings)
    result = [r for r in recordings if not _recording_is_excluded(r, time_tag)]
    print(f"[XenoCantoProvider] Filter: {before} → {len(result)} recordings "
          f"(time_tag={time_tag!r})")
    return result


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_recording(
    recording: dict,
    time_tag: str,
    weather: WeatherContext | None = None,
) -> float:
    """
    Compute a weighted score for a recording at the given time tag.

    Components (all additive before weather multipliers):
      base        1.0  — always
      type_bonus  0–4.0 — best-matching token from _TIME_PREFERENCES
      time_prox   0–1.0 — how close the recording's time-of-day is to now
      quality     +0.25 for grade A, 0 for B
      also_rich   0–0.15 — bonus for background species richness

    Weather is then applied in two layers:
      1. Global wind multiplier (WeatherContext.score_multiplier) scales the
         whole score — a broad floor that affects everything in high wind.
      2. Per-type binary condition modifiers (_RAIN_SCORE_MODIFIERS,
         _WIND_SCORE_MODIFIERS) are applied via _apply_condition_modifier(),
         so rain boosts frogs and penalises warblers rather than treating
         all recordings identically.
    """
    base = 1.0

    tokens    = _tokenise_type(recording.get("type", ""))
    preferred = _TIME_PREFERENCES.get(time_tag, {})
    if tokens:
        base += max((preferred.get(tok, 0.0) for tok in tokens), default=0.0)

    rec_time = recording.get("time", "")
    if rec_time:
        try:
            now_hour = datetime.now().hour
            rec_hour = int(rec_time.split(":")[0])
            distance = min(abs(now_hour - rec_hour), 24 - abs(now_hour - rec_hour))
            base += max(0.0, 1.0 - (distance / 12.0))
        except Exception:
            pass

    base += {"A": 0.25, "B": 0.0}.get(recording.get("q", ""), 0.0)
    base += min(len(recording.get("also", [])), 3) * 0.05

    if weather:
        # Layer 1: global wind floor
        base *= weather.score_multiplier

        # Layer 2: per-type binary condition modifiers
        if weather.is_raining:
            base *= _apply_condition_modifier(tokens, _RAIN_SCORE_MODIFIERS)

        if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
            base *= _apply_condition_modifier(tokens, _WIND_SCORE_MODIFIERS)

    return base


# ---------------------------------------------------------------------------
# Weighted sampling with species diversity
# ---------------------------------------------------------------------------

def _weighted_sample(
    recordings: list[dict],
    time_tag: str,
    k: int,
    weather: WeatherContext | None = None,
) -> list[dict]:
    if not recordings:
        print("[XenoCantoProvider] Weighted sample: no recordings.")
        return []

    k = min(k, len(recordings))

    if k == len(recordings):
        print(f"[XenoCantoProvider] Weighted sample: pool size == k ({k}), returning all.")
        return list(recordings)

    weights = [_score_recording(r, time_tag, weather) for r in recordings]

    oversample  = random.choices(recordings, weights=weights, k=k * 4)
    seen_ids:   set[str]   = set()
    candidates: list[dict] = []
    for r in oversample:
        rid = r.get("id", "")
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            candidates.append(r)

    if len(candidates) < k:
        remainder = [r for r in recordings if r.get("id", "") not in seen_ids]
        candidates.extend(remainder[: k - len(candidates)])

    seen_species: set[str]  = set()
    diverse:      list[dict] = []
    overflow:     list[dict] = []
    for r in candidates:
        sp = r.get("en", "").strip() or r.get("id", "")
        if sp not in seen_species:
            seen_species.add(sp)
            diverse.append(r)
        else:
            overflow.append(r)
        if len(diverse) == k:
            break

    while len(diverse) < k and overflow:
        diverse.append(overflow.pop(0))

    print(f"[XenoCantoProvider] Weighted sample: drew {len(diverse)} from "
          f"{len(recordings)} candidates ({len(seen_species)} unique species).")
    return diverse


# ---------------------------------------------------------------------------
# Weather-aware selection size
# ---------------------------------------------------------------------------

def _selection_size_for(time_tag: str, weather: WeatherContext) -> int:
    """
    Compute how many recordings to include in the active selection.

    Base size comes from _SELECTION_SIZE_BY_TAG (or default). Bad weather
    shrinks the pool: rain suppresses most species, so a smaller selection
    better reflects reality than sampling the same N with lower scores.
    Wind applies a milder shrink above the threshold speed.
    Both factors apply multiplicatively if conditions coincide.
    """
    size = _SELECTION_SIZE_BY_TAG.get(time_tag, _SELECTION_SIZE_DEFAULT)

    if weather.is_raining:
        size = round(size * _SELECTION_SIZE_RAIN_FACTOR)

    if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
        size = round(size * _SELECTION_SIZE_WIND_FACTOR)

    # Never drop below 3 — need enough variety for bag-shuffle to be meaningful
    size = max(3, size)

    print(f"[XenoCantoProvider] Selection size: {size} "
          f"(tag={time_tag!r} rain={'yes' if weather.is_raining else 'no'} "
          f"wind={weather.wind_speed:.1f}km/h)")
    return size


# ---------------------------------------------------------------------------
# Selection persistence
# ---------------------------------------------------------------------------

def _save_selection(selection: list[dict], time_tag: str) -> None:
    try:
        payload = {
            "time_tag":  time_tag,
            "saved_at":  time.time(),
            "selection": selection,
        }
        with open(_SELECTION_CACHE_PATH, "w") as f:
            json.dump(payload, f)
        print(f"[XenoCantoProvider] Selection persisted "
              f"({len(selection)} recordings, tag={time_tag!r}).")
    except Exception as e:
        print(f"[XenoCantoProvider] Could not persist selection: {e}")


def _load_selection(current_time_tag: str) -> list[dict] | None:
    try:
        with open(_SELECTION_CACHE_PATH) as f:
            payload = json.load(f)
        age   = time.time() - payload.get("saved_at", 0)
        tag   = payload.get("time_tag")
        saved = payload.get("selection", [])

        if age > _SELECTION_TTL:
            print("[XenoCantoProvider] Persisted selection expired.")
            return None
        if tag != current_time_tag:
            print(f"[XenoCantoProvider] Persisted selection time tag mismatch "
                  f"({tag!r} vs {current_time_tag!r}).")
            return None

        print(f"[XenoCantoProvider] Loaded persisted selection "
              f"({len(saved)} recordings, tag={tag!r}, age={int(age)}s).")
        return saved

    except FileNotFoundError:
        print("[XenoCantoProvider] No persisted selection found.")
        return None
    except Exception as e:
        print(f"[XenoCantoProvider] Could not load persisted selection: {e}")
        return None


# ---------------------------------------------------------------------------
# Audio cache eviction — filesystem-backend-safe
# ---------------------------------------------------------------------------

def _evict_audio_for_selection(selection: list[dict]) -> None:
    """
    Evict audio cache entries for a given selection.

    requests_cache's filesystem backend does NOT support delete(urls=[...])
    — that API is SQLite-only and silently no-ops on filesystem. The correct
    approach is to derive the cache key for each URL using create_key() and
    delete entries individually.
    """
    if not selection:
        return

    try:
        _audio_cache.cache.delete(expired=True)
    except Exception as e:
        print(f"[XenoCantoProvider] Expired audio sweep error (non-fatal): {e}")

    from requests import Request

    evicted = 0
    for r in selection:
        file_url = r.get("file", "")
        if not file_url:
            continue
        if file_url.startswith("//"):
            file_url = "https:" + file_url
        try:
            req       = Request("GET", file_url).prepare()
            cache_key = _audio_cache.cache.create_key(req)
            _audio_cache.cache.delete(cache_key)
            evicted += 1
        except Exception as e:
            print(f"[XenoCantoProvider] Audio eviction error for {file_url!r}: {e}")

    print(f"[XenoCantoProvider] Evicted {evicted}/{len(selection)} audio cache entries.")


# ---------------------------------------------------------------------------
# Group hint helpers
# ---------------------------------------------------------------------------

def _build_grp_hint(selection: list[dict]) -> str:
    seen:   set[str]  = set()
    groups: list[str] = []
    for r in selection:
        grp = r.get("grp", "").strip().lower()
        if grp and grp not in seen:
            seen.add(grp)
            groups.append(grp)
    if not groups:
        return ""
    if len(groups) == 1:
        return groups[0]
    if len(groups) == 2:
        return f"{groups[0]} and {groups[1]}"
    return ", ".join(groups[:-1]) + f", and {groups[-1]}"


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class XenoCantoProvider(OutdoorsProvider):
    """
    Outdoors provider for Xeno-canto wildlife sound recordings.

    outdoors_type identifier: "xeno-canto"

    Constructor
    -----------
    xeno_canto_loc : XenoCantoLoc
        Location instance for fetching recording metadata and audio.
    open_meteo : OpenMeteoLoc | None
        Optional weather provider. When supplied, weather conditions modulate
        both the recording selection (via score and threshold modifiers) and
        the perceived activity level (via per-type threshold logic). The
        15-minute OpenMeteo cache means weather refreshes cost nothing.

    tick()
        Advances _selection_index when the current recording has been held
        for its allotted number of ticks. Rolls _activity_level and snapshots
        the current time tag. Only mutator of these fields.

    get_limited_perception()
        Pure reader. Computes threshold per-recording via _threshold_for(),
        applying type-aware condition modifiers. No state mutation.

    get_full_perception()
        Pure reader. Same per-type threshold logic. Returns (text, popup, audio).
        No state mutation, no index advancement.
    """

    outdoors_type = "xeno-canto"
    tick_every: int = 1

    def __init__(self, xeno_canto_loc: XenoCantoLoc, open_meteo=None):
        print("[XenoCantoProvider] Initialising provider.")
        self._loc                               = xeno_canto_loc
        self._open_meteo                        = open_meteo
        self._weather_context: WeatherContext   = WeatherContext()
        self._active_selection: list[dict]      = []
        self._selection_index: int              = 0
        self._active_time_tag: str | None       = None
        self._ticks_on_current: int             = 0
        self._activity_level: float             = 0.0
        self._active_time_tag_for_activity: str = "morning"
        self._seen_indices: set[int]            = set()
        self._selection_id: int                 = 0
        self._lock                              = threading.Lock()
        print(f"[XenoCantoProvider] Ready. lat={xeno_canto_loc.lat}, "
              f"lon={xeno_canto_loc.long}, "
              f"weather={'yes' if open_meteo else 'no'}")

    # ------------------------------------------------------------------
    # Weather refresh
    # ------------------------------------------------------------------

    def _refresh_weather(self) -> None:
        if not self._open_meteo:
            return
        try:
            d = self._open_meteo.get_structured_weather()
            self._weather_context = WeatherContext(
                wind_speed=    d.get("wind_speed")    or 0.0,
                precipitation= d.get("precipitation") or 0.0,
                cloud_cover=   d.get("cloud_cover")   or 0.0,
                temperature=   d.get("temperature")   or 15.0,
                is_day=        d.get("is_day", True),
            )
            w = self._weather_context
            print(
                f"[XenoCantoProvider] Weather: "
                f"wind={w.wind_speed:.1f}km/h "
                f"rain={'yes' if w.is_raining else 'no'} ({w.precipitation:.2f}mm) "
                f"score_mult={w.score_multiplier:.2f} "
                f"rain={'active' if w.is_raining else 'none'} "
                f"(per-type modifiers apply)"
            )
        except Exception as e:
            print(f"[XenoCantoProvider] Weather refresh failed (neutral context): {e}")

    # ------------------------------------------------------------------
    # Tick — only mutator of _selection_index and _activity_level
    # ------------------------------------------------------------------

    def tick(self) -> None:
        with self._lock:
            selection = self._active_selection
            if not selection:
                return

            current  = selection[self._selection_index]
            allotted = _ticks_for_recording(current)
            self._ticks_on_current += 1

            print(f"[XenoCantoProvider] tick: index={self._selection_index} "
                  f"ticks={self._ticks_on_current}/{allotted} "
                  f"recording=XC{current.get('id')} "
                  f"length={current.get('length', '?')}")

            if self._ticks_on_current >= allotted:
                self._ticks_on_current = 0
                if len(selection) > 1:
                    # Reset bag tracking if the selection object has changed
                    if self._selection_id != id(selection):
                        self._seen_indices = set()
                        self._selection_id = id(selection)

                    self._seen_indices.add(self._selection_index)
                    unseen = [i for i in range(len(selection))
                              if i not in self._seen_indices]

                    if not unseen:
                        self._seen_indices.clear()
                        self._seen_indices.add(self._selection_index)
                        unseen = [i for i in range(len(selection))
                                  if i != self._selection_index]

                    self._selection_index = random.choice(unseen)
                else:
                    self._selection_index = 0

                next_rec = selection[self._selection_index]
                print(f"[XenoCantoProvider] Index → {self._selection_index} "
                      f"({len(self._seen_indices)}/{len(selection)} seen) "
                      f"(XC{next_rec.get('id')} — {next_rec.get('en', '?')})")

            time_tag                           = get_time_tag_from_now() or "morning"
            self._active_time_tag_for_activity = time_tag
            self._activity_level               = random.random()

            # Log what the thresholds would look like for the current recording
            # (perception methods will compute these themselves — this is diagnostic only)
            w        = self._weather_context
            cur_tokens = _tokenise_type(current.get("type", ""))
            t_full    = _threshold_for(_ACTIVITY_THRESHOLD_FULL,    time_tag, 1/4, cur_tokens, w)
            t_limited = _threshold_for(_ACTIVITY_THRESHOLD_LIMITED, time_tag, 1/6, cur_tokens, w)

            print(f"[XenoCantoProvider] Activity: {self._activity_level:.3f} "
                  f"tag={time_tag!r} "
                  f"full≤{t_full:.3f} limited≤{t_limited:.3f} "
                  f"tokens={cur_tokens} "
                  f"rain={'yes' if w.is_raining else 'no'} "
                  f"wind={w.wind_speed:.1f}km/h")

    # ------------------------------------------------------------------
    # Selection management
    # ------------------------------------------------------------------

    def _refresh_selection(self) -> None:
        self._refresh_weather()

        time_tag = get_time_tag_from_now() or "morning"
        print(f"[XenoCantoProvider] Refreshing selection for time_tag={time_tag!r}")

        restored = _load_selection(time_tag)
        if restored:
            with self._lock:
                old_selection = list(self._active_selection)
            if old_selection:
                _evict_audio_for_selection(old_selection)
            with self._lock:
                self._active_selection = restored
                self._selection_index  = random.randrange(len(restored)) if restored else 0
                self._ticks_on_current = 0
                self._active_time_tag  = time_tag
                self._seen_indices     = set()
                self._selection_id     = id(restored)
            print(f"[XenoCantoProvider] Restored {len(restored)}-recording selection "
                  f"from disk — skipping fresh draw.")
            return

        with self._lock:
            old_selection = list(self._active_selection)
        if old_selection:
            _evict_audio_for_selection(old_selection)

        recordings     = self._loc.get_recordings()
        filtered       = _filter_recordings(recordings, time_tag)
        selection_size = _selection_size_for(time_tag, self._weather_context)
        selection      = _weighted_sample(
            filtered, time_tag, k=selection_size, weather=self._weather_context
        )

        with self._lock:
            self._active_selection = selection
            self._selection_index  = random.randrange(len(selection)) if selection else 0
            self._ticks_on_current = 0
            self._active_time_tag  = time_tag
            self._seen_indices     = set()
            self._selection_id     = id(selection)

        _save_selection(selection, time_tag)

        if selection:
            print(f"[XenoCantoProvider] New selection ({len(selection)} recordings, "
                  f"time_tag={time_tag!r}):")
            for r in selection:
                ticks  = _ticks_for_recording(r)
                tokens = _tokenise_type(r.get("type", ""))
                print(f"  XC{r.get('id')} — {r.get('en', '?')} "
                      f"({r.get('gen', '')} {r.get('sp', '')}) "
                      f"tokens={tokens} q={r.get('q', '?')} "
                      f"length={r.get('length', '?')} → {ticks}t")
            self._prefetch_audio_async(selection)
        else:
            print("[XenoCantoProvider] Selection is empty.")

    def _prefetch_audio_async(self, selection: list[dict]) -> None:
        print(f"[XenoCantoProvider] Starting background audio prefetch "
              f"for {len(selection)} recordings...")
        def _download_all():
            for recording in selection:
                print(f"[XenoCantoProvider] Prefetching XC{recording.get('id')}...")
                download_audio(recording)
            print("[XenoCantoProvider] Background audio prefetch complete.")
        threading.Thread(target=_download_all, daemon=True).start()

    def _ensure_selection(self) -> None:
        current_tag = get_time_tag_from_now() or "morning"
        with self._lock:
            needs_refresh = (
                not self._active_selection
                or self._active_time_tag != current_tag
            )
        if needs_refresh:
            print(f"[XenoCantoProvider] Selection refresh triggered "
                  f"(active={self._active_time_tag!r}, current={current_tag!r})")
            self._refresh_selection()
        else:
            print(f"[XenoCantoProvider] Selection valid "
                  f"(tag={current_tag!r}, {len(self._active_selection)} recordings, "
                  f"index={self._selection_index})")

    # ------------------------------------------------------------------
    # Private audio fetch
    # ------------------------------------------------------------------

    def _fetch_sound_bytes(self, recording: dict) -> tuple[bytes, int] | None:
        audio_bytes = download_audio(recording)
        smp         = int(recording.get("smp", 44100))
        if audio_bytes:
            print(f"[XenoCantoProvider] Audio ready: {len(audio_bytes)} bytes.")
            return audio_bytes, smp
        print(f"[XenoCantoProvider] Audio unavailable for XC{recording.get('id')}.")
        return None

    # ------------------------------------------------------------------
    # OutdoorsProvider interface
    # ------------------------------------------------------------------

    def get_limited_perception(self) -> tuple[str, str | None]:
        """
        Short ambient text for window_perception().

        Threshold is computed per-recording via _threshold_for(), so type-aware
        condition modifiers apply — frogs seem more active in rain, warblers less.
        Pure reader — no state mutation.
        """
        print("[XenoCantoProvider] get_limited_perception() called.")
        self._ensure_selection()

        with self._lock:
            selection      = list(self._active_selection)
            index          = self._selection_index
            activity_level = self._activity_level
            time_tag       = self._active_time_tag_for_activity

        if not selection:
            return (
                "The outside world sounds quiet — no wildlife stirs near this opening.",
                None,
            )

        w          = self._weather_context
        r          = selection[index % len(selection)]
        tokens     = _tokenise_type(r.get("type", ""))
        threshold  = _threshold_for(
            _ACTIVITY_THRESHOLD_LIMITED, time_tag, 1/6, tokens, w
        )

        if activity_level > threshold:
            if w.is_raining:
                return (
                    "The rain outside muffles all wildlife sound into a soft, "
                    "continuous wash of white noise.",
                    None,
                )
            print(f"[XenoCantoProvider] Limited: quiet "
                  f"(level={activity_level:.3f} > threshold={threshold:.3f}).")
            return (
                "Coming from the outdoors is the stillness of animals, "
                "insects and other living creatures.",
                None,
            )

        grp_hint = _build_grp_hint(selection)
        mood     = _TIME_MOOD.get(time_tag, "alive with the sounds of nature")

        if w.wind_speed > 20:
            mood = "alive with sound, though the wind carries it in broken gusts"

        text = (
            f"Through the opening, the outside world feels {mood}. "
            f"You catch a fleeting impression of wildlife nearby"
            + (f" — {grp_hint}" if grp_hint else "")
            + "."
        )
        print(f"[XenoCantoProvider] Limited: {text[:80]}...")
        return text, None

    def get_full_perception(self) -> tuple[str, str | None, tuple[bytes, int] | None]:
        """
        Detailed perception for look_through_aperture / outdoors_area rooms.

        Threshold is computed per-recording via _threshold_for(), so
        rain-loving types (advertisement call, mating call) are more likely
        to be heard in rain while delicate singers are less so.
        Pure reader — no state mutation.

        Returns (perception_text, popup_text, audio) where:
          - popup_text is a recordist attribution string, or None
          - audio is (bytes, sample_rate) if a sound plays, or None
        """
        self._ensure_selection()

        with self._lock:
            selection      = list(self._active_selection)
            index          = self._selection_index
            activity_level = self._activity_level
            time_tag       = self._active_time_tag_for_activity

        if not selection:
            return "No wildlife sounds are detectable in this area.", None, None

        w      = self._weather_context
        r      = selection[index % len(selection)]
        tokens = _tokenise_type(r.get("type", ""))
        threshold = _threshold_for(
            _ACTIVITY_THRESHOLD_FULL, time_tag, 1/4, tokens, w
        )

        if activity_level > threshold:
            if w.is_raining:
                return (
                    "Rain sheets across the landscape outside. The wildlife has "
                    "gone quiet — only the percussion of water on leaves and stone.",
                    None,
                    None,
                )
            print(f"[XenoCantoProvider] Full: quiet "
                  f"(level={activity_level:.3f} > threshold={threshold:.3f}).")
            return (
                "You wait and expect to catch the sounds of wild beasts around, "
                "but they seem to be quiet right now.",
                None,
                None,
            )

        en_name    = r.get("en") or ""
        gen        = r.get("gen", "").strip()
        sp         = r.get("sp", "").strip()
        sci_name   = f"{gen} {sp}".strip() if (gen or sp) else ""
        name       = en_name or sci_name or "Unknown species"
        sound_type = r.get("type", "").strip() or "call"
        grp        = r.get("grp", "")
        rec        = r.get("rec", "").strip()
        length     = r.get("length", "")
        seen       = r.get("animal-seen", "")
        also       = r.get("also", [])
        group_note = f" [{grp}]" if grp and grp != "birds" else ""

        freq_note   = ""
        ann_set     = r.get("annotation-set")
        annotations = ann_set.get("annotations", []) if isinstance(ann_set, dict) else []
        if annotations:
            first  = annotations[0]
            f_low  = first.get("frequency_low")
            f_high = first.get("frequency_high")
            if f_low is not None and f_high is not None:
                freq_note = f", freq {f_low}–{f_high} Hz"

        parts = [f"Nearby you can hear a {name}{group_note}"]
        if sci_name and en_name:
            parts[0] += f" ({sci_name})"
        parts.append(f"{sound_type}")
        if length:
            parts.append(f"length {length}")
        if seen.lower() in ("yes", "no"):
            parts.append(f"animal {'seen' if seen.lower() == 'yes' else 'not seen'}")
        text = f"{parts[0]} — {', '.join(parts[1:])}{freq_note}."

        if also:
            also_str = ", ".join(also[:5])
            text += f" Also audible in the background: {also_str}."

        if w.wind_speed > 20:
            text += " The wind makes it hard to hear clearly."

        popup = (
            f"Listening to '{name}' recorded by '{rec}'"
            if rec else
            f"Listening to '{name}'"
        )

        audio = self._fetch_sound_bytes(r)

        return text, popup, audio


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