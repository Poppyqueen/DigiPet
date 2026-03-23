from dataclasses import dataclass
import random
from utils.loc_datetime import datetime



from .config import (_DEFAULT_TICKS_PER_RECORDING, 
                     _SECONDS_PER_TICK, _MIN_TICKS_PER_RECORDING, 
                     _MAX_TICKS_PER_RECORDING, _RAIN_THRESHOLD_MODIFIERS,
                     _SELECTION_SIZE_WIND_THRESHOLD, _WIND_THRESHOLD_MODIFIERS,
                     _TIME_PREFERENCES, _TIME_PROXIMITY_WEIGHT,
                     _RAIN_SCORE_MODIFIERS, _WIND_SCORE_MODIFIERS,
                     _ALWAYS_EXCLUDE_TOKENS, _TIME_BLACKLIST,
                     _SELECTION_SIZE_BY_TAG, _SELECTION_SIZE_DEFAULT,
                     _SELECTION_SIZE_RAIN_FACTOR, _SELECTION_SIZE_WIND_FACTOR)

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
# Scoring
# ---------------------------------------------------------------------------



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
        # type_bonus  0–4.0 — best-matching token from _TIME_PREFERENCES
        type_bonus = max((preferred.get(tok, 0.0) for tok in tokens), default=0.0)
        base += type_bonus

    rec_time = recording.get("time", "") # At what time was this recording made.
    if rec_time:
        try:
            now_hour = datetime.now().hour
            rec_hour = int(rec_time.split(":")[0])
            distance = min(abs(now_hour - rec_hour), 24 - abs(now_hour - rec_hour))
            
            # time_prox 0–1.0 — how close the recording's time-of-day is to now
            # This creates a steep drop-off and a hard penalty for being 'late'
            time_factor = max(0.0, 1.0 - (distance / 3.0)**2) 
            prox_bonus = time_factor * _TIME_PROXIMITY_WEIGHT
            base += prox_bonus
            
        except Exception as e:
            print(f"  [Time Prox]: Error calculating proximity: {e}")

    # quality +0.25 for grade A, 0 for B
    q_val = {"A": 0.25, "B": 0.0}.get(recording.get("q", ""), 0.0)
    base += q_val

    # also_rich 0–0.15 — bonus for background species richness
    richness_bonus = min(len(recording.get("also", [])), 3) * 0.05
    base += richness_bonus


    if weather:
        # Layer 1: Global wind multiplier (WeatherContext.score_multiplier)
        # scales the whole score — a broad floor that affects everything in high wind.
        old_base = base
        base *= weather.score_multiplier

        # Layer 2: Per-type binary condition modifiers (_RAIN_SCORE_MODIFIERS,
        # _WIND_SCORE_MODIFIERS) are applied via _apply_condition_modifier()
        if weather.is_raining:
            rain_mod = _apply_condition_modifier(tokens, _RAIN_SCORE_MODIFIERS)
            base *= rain_mod

        if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
            wind_mod = _apply_condition_modifier(tokens, _WIND_SCORE_MODIFIERS)
            base *= wind_mod

    return base



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
# Group hint helpers
# ---------------------------------------------------------------------------

def _build_grp_hint(selection: list[dict]) -> str:
    seen:   set[str]  = set()
    groups: list[str] = []
    for r in selection:
        # The crash happens here because r.get("grp") returns None for a record in the list
        val = r.get("grp")
        if val is None:
            # We skip the debug print to keep it clean, just default to empty
            val = ""
            
        grp = val.strip().lower()
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

