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
_SELECTION_TTL        = 21600  # 6 hours 

# ---------------------------------------------------------------------------
# Tick constants
# ---------------------------------------------------------------------------

# Scaling divisor for converting recording length (seconds) into a tick count.
# Tune this to control how many ticks a typical recording occupies —
# lower = more ticks per recording, higher = fewer.
#_SECONDS_PER_TICK: int = 60
_SECONDS_PER_TICK: int = 120


# Fallback tick count when a recording has no parseable length field.
_DEFAULT_TICKS_PER_RECORDING: int = 3

# Floor and ceiling so no recording stays too briefly or too long.
_MIN_TICKS_PER_RECORDING: int = 2
_MAX_TICKS_PER_RECORDING: int = 5


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
# ---------------------------------------------------------------------------

_TIME_PREFERENCES: dict[str, dict[str, float]] = {
    "late night": {
        "nocturnal flight call": 1.5,
        "call":                  0.2,
        "social call":           0.2,
        "echolocation":          0.8,
        "feeding buzz":          0.6,
    },
    "early morning": {
        "dawn song":    2.0,
        "song":         1.0,
        "flight song":  0.5,
        "call":         0.3,
        "duet":         0.4,
    },
    "morning": {
        "song":             1.0,
        "call":             0.5,
        "flight call":      0.3,
        "duet":             0.4,
        "territorial call": 0.3,
    },
    "noon": {
        "call":       0.5,
        "song":       0.3,
        "alarm call": 0.2,
    },
    "afternoon": {
        "call":             0.5,
        "song":             0.3,
        "territorial call": 0.4,
        "alarm call":       0.2,
    },
    "late afternoon": {
        "call":        0.5,
        "song":        0.4,
        "flight call": 0.3,
        "subsong":     0.4,
    },
    "night": {
        "nocturnal flight call": 1.2,
        "call":                  0.4,
        "song":                  0.2,
        "echolocation":          0.8,
        "feeding buzz":          0.6,
    },
}

# ---------------------------------------------------------------------------
# Wildlife activity thresholds
#
# tick() rolls _activity_level as a float in [0, 1) each tick.
# A value at or below the threshold means wildlife is perceptible right now.
# Higher threshold → more often perceptible.
#
# Full perception has a higher threshold than limited — a direct look/listen
# is more likely to catch something than a fleeting impression through a window.
# ---------------------------------------------------------------------------

_ACTIVITY_THRESHOLD_FULL: dict[str, float] = {
    "late night":     1 / 3,
    "early morning":  1 / 1,
    "morning":        1 / 1,
    "noon":           1 / 3,
    "afternoon":      1 / 2,
    "late afternoon": 1 / 1,
    "night":          2 / 3,
}

_ACTIVITY_THRESHOLD_LIMITED: dict[str, float] = {
    "late night":     1 / 6,
    "early morning":  1 / 4,
    "morning":        1 / 4,
    "noon":           1 / 6,
    "afternoon":      1 / 5,
    "late afternoon": 1 / 4,
    "night":          1 / 5,
}


# ---------------------------------------------------------------------------
# Tick duration helpers
# ---------------------------------------------------------------------------

def _parse_length_seconds(length_str: str) -> int | None:
    """
    Parse a xeno-canto length string like "1:23" into total seconds.
    Returns None if the string is absent or malformed.
    """
    if not length_str:
        return None
    try:
        parts = length_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def _ticks_for_recording(recording: dict) -> int:
    """
    Derive how many ticks the given recording should occupy the current index.
    Proportional to recording length; clamped to [_MIN, _MAX].
    Falls back to _DEFAULT_TICKS_PER_RECORDING if length is absent or unparseable.
    """
    seconds = _parse_length_seconds(recording.get("length", ""))
    if seconds is None:
        return _DEFAULT_TICKS_PER_RECORDING
    ticks = max(1, round(seconds / _SECONDS_PER_TICK))
    return max(_MIN_TICKS_PER_RECORDING, min(_MAX_TICKS_PER_RECORDING, ticks))


# ---------------------------------------------------------------------------
# Weighting helpers
# ---------------------------------------------------------------------------

def _score_recording(recording: dict, time_tag: str) -> float:
    base = 1.0

    sound_type = recording.get("type", "").lower()
    preferred  = _TIME_PREFERENCES.get(time_tag, {})
    base += preferred.get(sound_type, 0.0)

    rec_time = recording.get("time", "")
    if rec_time:
        try:
            from utils.loc_datetime import datetime as loc_datetime
            now_hour = loc_datetime.now().hour
            rec_hour  = int(rec_time.split(":")[0])
            distance  = min(abs(now_hour - rec_hour), 24 - abs(now_hour - rec_hour))
            base += max(0.0, 1.0 - (distance / 12.0))
        except Exception:
            pass

    return base


def _filter_recordings(recordings: list[dict], time_tag: str) -> list[dict]:
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
    if not recordings:
        print("[XenoCantoProvider] Weighted sample: no recordings to sample from.")
        return []

    k = min(k, len(recordings))

    if k == len(recordings):
        print(f"[XenoCantoProvider] Weighted sample: pool size == k ({k}), returning all.")
        return list(recordings)

    weights = [_score_recording(r, time_tag) for r in recordings]

    oversample = random.choices(recordings, weights=weights, k=k * 4)
    seen:   set[str]   = set()
    result: list[dict] = []
    for r in oversample:
        rid = r.get("id", "")
        if rid and rid not in seen:
            seen.add(rid)
            result.append(r)
        if len(result) == k:
            break

    if len(result) < k:
        remaining = [r for r in recordings if r.get("id", "") not in seen]
        result.extend(remaining[: k - len(result)])
        print(f"[XenoCantoProvider] Weighted sample: topped up to {len(result)} "
              f"(oversampling fell short).")

    print(f"[XenoCantoProvider] Weighted sample: drew {len(result)} from "
          f"{len(recordings)} candidates.")
    return result


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

    tick()
        Advances _selection_index when the current recording has been held
        for its allotted number of ticks (proportional to recording length).
        Also rolls _activity_level — a float in [0, 1) representing how active
        wildlife is at this moment — and snapshots the current time tag into
        _active_time_tag_for_activity.
        This is the only place any of these fields mutate.

    get_limited_perception()
        Pure reader. Compares _activity_level against _ACTIVITY_THRESHOLD_LIMITED
        for the current time tag. Returns ambient text if perceptible, silence
        text otherwise. No state mutation.

    get_full_perception()
        Pure reader. Compares _activity_level against _ACTIVITY_THRESHOLD_FULL
        for the current time tag. Returns (text, popup, audio) for the recording
        at the current index if perceptible, silence text otherwise.
        No state mutation, no index advancement.
    """

    outdoors_type = "xeno-canto"

    # OutdoorsProvider tick cadence — every outdoors tick.
    tick_every: int = 1

    def __init__(self, xeno_canto_loc: XenoCantoLoc):
        print("[XenoCantoProvider] Initialising provider.")
        self._loc                               = xeno_canto_loc
        self._active_selection: list[dict]      = []
        self._selection_index: int              = 0
        self._active_time_tag: str | None       = None
        self._ticks_on_current: int             = 0
        self._activity_level: float             = 0.0
        self._active_time_tag_for_activity: str = "morning"
        self._lock                              = threading.Lock()
        print(f"[XenoCantoProvider] Ready. lat={xeno_canto_loc.lat}, "
              f"lon={xeno_canto_loc.lon}")

    # ------------------------------------------------------------------
    # Tick — only mutator of _selection_index and _activity_level
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """
        Called by OutdoorsPerception on every outdoors tick.

        1. Increments the tick counter for the current recording. When the
           counter reaches the recording's allotted duration (derived from its
           length field), the index advances to the next recording in the
           selection and the counter resets.

        2. Rolls a fresh _activity_level float in[0, 1) and snapshots the
           current time tag into _active_time_tag_for_activity. Perception
           methods read these values to decide whether wildlife is perceptible
           without performing any roll themselves.

        Does not trigger perception, audio fetches, or selection refreshes.
        Those remain lazy — _ensure_selection() is still called on demand
        from the perception methods.
        """
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
                    # Initialize tracking if missing, or if the selection list was refreshed
                    if not hasattr(self, '_seen_indices') or getattr(self, '_selection_id', None) != id(selection):
                        self._seen_indices = set()
                        self._selection_id = id(selection)
                    
                    # Mark the current recording as seen
                    self._seen_indices.add(self._selection_index)
                    
                    # Gather all indices that haven't been seen yet
                    unseen =[i for i in range(len(selection)) if i not in self._seen_indices]
                    
                    # If the bag is empty (all have been seen), reset it
                    if not unseen:
                        self._seen_indices.clear()
                        # Add the current index back in so we don't repeat it back-to-back across resets
                        self._seen_indices.add(self._selection_index)
                        unseen =[i for i in range(len(selection)) if i != self._selection_index]
                    
                    # Draw randomly from the unseen bag
                    self._selection_index = random.choice(unseen)
                else:
                    self._selection_index = 0
                
                next_rec = selection[self._selection_index]
                bag_status = f"({len(self._seen_indices)}/{len(selection)} seen)" if hasattr(self, '_seen_indices') else ""
                print(f"[XenoCantoProvider] Index randomly changed {bag_status} → {self._selection_index} "
                      f"(XC{next_rec.get('id')} — {next_rec.get('en', '?')})")

            # Roll activity level for this tick — perception methods read this.
            time_tag                           = get_time_tag_from_now() or "morning"
            self._active_time_tag_for_activity = time_tag
            self._activity_level               = random.random()

            threshold_full    = _ACTIVITY_THRESHOLD_FULL.get(time_tag, 1 / 4)
            threshold_limited = _ACTIVITY_THRESHOLD_LIMITED.get(time_tag, 1 / 6)
            print(f"[XenoCantoProvider] Activity level: {self._activity_level:.3f} "
                  f"(tag={time_tag!r}, "
                  f"full≤{threshold_full:.3f}, "
                  f"limited≤{threshold_limited:.3f}, "
                  f"full={'yes' if self._activity_level <= threshold_full else 'no'}, "
                  f"limited={'yes' if self._activity_level <= threshold_limited else 'no'})")

    # ------------------------------------------------------------------
    # Selection management (lazy, called from perception methods)
    # ------------------------------------------------------------------

    def _evict_selection_audio(self, selection: list[dict]) -> None:
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

        restored = _load_selection(time_tag)
        if restored:
            with self._lock:
                old_selection = list(self._active_selection)
            self._evict_selection_audio(old_selection)
            with self._lock:
                self._active_selection = restored
                self._selection_index  = random.randrange(len(restored)) if restored else 0
                self._ticks_on_current = 0
                self._active_time_tag  = time_tag
            print(f"[XenoCantoProvider] Restored selection from disk — "
                  f"skipping fresh draw and prefetch.")
            return

        recordings = self._loc.get_recordings_with_fallback()
        filtered   = _filter_recordings(recordings, time_tag)
        selection  = _weighted_sample(filtered, time_tag, k=_SELECTION_SIZE)

        with self._lock:
            old_selection = list(self._active_selection)
        self._evict_selection_audio(old_selection)

        with self._lock:
            self._active_selection = selection
            self._selection_index  = random.randrange(len(selection)) if selection else 0
            self._ticks_on_current = 0
            self._active_time_tag  = time_tag

        _save_selection(selection, time_tag)

        if selection:
            print(f"[XenoCantoProvider] New selection ({len(selection)} recordings) "
                  f"for time_tag={time_tag!r}:")
            for r in selection:
                ticks = _ticks_for_recording(r)
                print(f"  XC{r.get('id')} — {r.get('en', '?')} "
                      f"({r.get('gen', '')} {r.get('sp', '')}) "
                      f"type={r.get('type', '?')} q={r.get('q', '?')} "
                      f"length={r.get('length', '?')} → {ticks} tick(s)")
            self._prefetch_audio_async(selection)
        else:
            print("[XenoCantoProvider] Selection is empty — no recordings available.")

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
    # OutdoorsProvider interface — pure readers, no state mutation
    # ------------------------------------------------------------------

    def get_limited_perception(self) -> tuple[str, str | None]:
        """
        Short ambient text for window_perception().

        Pure reader — reads _activity_level and _active_time_tag_for_activity
        set by the last tick(). No state mutation.
        """
        print("[XenoCantoProvider] get_limited_perception() called.")
        self._ensure_selection()

        with self._lock:
            selection      = list(self._active_selection)
            activity_level = self._activity_level
            time_tag       = self._active_time_tag_for_activity

        if not selection:
            return (
                "The outside world sounds quiet — no wildlife stirs near this opening.",
                None,
            )

        threshold = _ACTIVITY_THRESHOLD_LIMITED.get(time_tag, 1 / 6)
        if activity_level > threshold:
            print(f"[XenoCantoProvider] Limited: quiet "
                  f"(level={activity_level:.3f} > threshold={threshold:.3f}).")
            return (
                "Coming from the outdoors is the stillness of animals, "
                "insects and other living creatures.",
                None,
            )

        grp_hint = _build_grp_hint(selection)
        mood     = _TIME_MOOD.get(time_tag, "alive with the sounds of nature")

        text = (
            f"Through the opening, the outside world feels {mood}. "
            f"You catch a fleeting impression of wildlife nearby"
            + (f" — {grp_hint}" if grp_hint else "")
            + "."
        )
        print(f"[XenoCantoProvider] Limited perception: {text[:80]}...")
        return text, None

    def get_full_perception(self) -> tuple[str, str | None, tuple[bytes, int] | None]:
        """
        Detailed perception for look_through_aperture / outdoors_area rooms.

        Pure reader — reads _activity_level, _active_time_tag_for_activity,
        and the recording at the current _selection_index set by the last
        tick(). Does not advance the index (tick() owns that). No state
        mutation.

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

        threshold = _ACTIVITY_THRESHOLD_FULL.get(time_tag, 1 / 4)
        if activity_level > threshold:
            print(f"[XenoCantoProvider] Full: quiet "
                  f"(level={activity_level:.3f} > threshold={threshold:.3f}).")
            return (
                "You wait and expect to catch the sounds of wild beasts around, "
                "but they seem to be quiet right now.",
                None,
                None,
            )

        r = selection[index % len(selection)]

        en_name    = r.get("en") or ""
        gen        = r.get("gen", "").strip()
        sp         = r.get("sp", "").strip()
        sci_name   = f"{gen} {sp}".strip() if (gen or sp) else ""
        name       = en_name or sci_name or "Unknown species"
        sound_type = r.get("type", "unknown")
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


def _build_species_hint(selection: list[dict]) -> str:
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
    seen:   set[str]  = set()
    result: list[str] = []
    for r in selection:
        for species in r.get("also", []):
            if species and species not in seen:
                seen.add(species)
                result.append(species)
    return result