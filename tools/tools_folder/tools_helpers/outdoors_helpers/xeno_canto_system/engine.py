# engine.py
from dataclasses import dataclass
import random
from utils.loc_datetime import datetime
import math


from .config import (_DEFAULT_TICKS_PER_RECORDING, 
                     _SECONDS_PER_TICK, _MIN_TICKS_PER_RECORDING, 
                     _MAX_TICKS_PER_RECORDING, _RAIN_THRESHOLD_MODIFIERS,
                     _SELECTION_SIZE_WIND_THRESHOLD, _WIND_THRESHOLD_MODIFIERS,
                     _TIME_PREFERENCES,
                     _RAIN_SCORE_MODIFIERS, _WIND_SCORE_MODIFIERS,
                     _ALWAYS_EXCLUDE_TOKENS, _TIME_BLACKLIST,
                     _SELECTION_SIZE_BY_TAG, _SELECTION_SIZE_DEFAULT,
                     _SELECTION_SIZE_RAIN_FACTOR, _SELECTION_SIZE_WIND_FACTOR,
                     _NO_TIME_PENALTY, _TIME_PROXIMITY_SIGMOID_K, _TIME_PROXIMITY_GATE_HOURS)

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


@dataclass
class AbundanceContext:
    """
    Encodes the wildlife density of the environment on a 1–9 Bortle-style scale.

    1  = deep urban core — a single pigeon, occasional starling, almost nothing.
    5  = suburban / degraded habitat — moderate variety, gaps in activity.
    9 = pristine wilderness / rainforest — full biodiversity, rich and constant.

    Abundance is an environmental constant (set at world-creation time), not a
    dynamic reading — unlike weather it never changes mid-session.  It influences
    three levers through the same pipeline weather does:

      selection_size_multiplier  — how many species are in the active pool
      silence_threshold_multiplier — how likely the environment is "quiet"
                                     (lower abundance → threshold easier to exceed
                                     → silence fires more often)
      diversity_weight           — 0.0..1.0 passed to _weighted_sample to control
                                   how hard species-deduplication is enforced.
                                   Bortle 9 = full diversity pass (many species).
                                   Bortle 1  = no diversity pass (dominant species
                                   repeat, just like a real impoverished habitat).
    """
    level: int = 9   # 1–9, clamped on init

    def __post_init__(self) -> None:
        self.level = max(1, min(9, self.level))

    @property
    def _t(self) -> float:
        """Normalised position 0.0 (level=1) → 1.0 (level=9)."""
        return (self.level - 1) / 8.0

    @property
    def selection_size_multiplier(self) -> float:
        """
        Pool size: 0.15 (Bortle 1) → 1.0 (Bortle 9).
        At level 1 a morning pool of 10 collapses to 1–2 recordings.
        """
        return 0.15 + 0.85 * self._t

    @property
    def silence_threshold_multiplier(self) -> float:
        """
        Applied to the base activity threshold.  Values < 1.0 lower the bar
        for triggering 'nothing heard', making silence more common at low abundance.
        0.35 (Bortle 1) → 1.0 (Bortle 9).
        """
        return 0.35 + 0.65 * self._t

    @property
    def diversity_weight(self) -> float:
        """
        0.0 (Bortle 1, no deduplication) → 1.0 (Bortle 9, full deduplication).
        Controls species-diversity enforcement in _weighted_sample.
        """
        return self._t


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


# ---------------------------------------------------------------------------
# Time proximity — PRIMARY scoring signal
# ---------------------------------------------------------------------------

def _time_proximity_multiplier(recording: dict, time_tag: str) -> float:
    """
    Returns a [0.0, 1.0] multiplicative weight expressing how well the
    recording's clock time matches the current moment.

    Curve: sigmoid centred on 0h distance, reflected so that:
      - 0h distance  → 1.0   (perfect match)
      - 2h distance  → ~0.05 (hard gate, effectively excluded)
      - 4h distance  → ~0.00

    Formula: 1 / (1 + exp(k * (distance - gate)))
      k    = _TIME_PROXIMITY_SIGMOID_K   (steepness)
      gate = _TIME_PROXIMITY_GATE_HOURS  (inflection point)

    Missing or unparseable time → _NO_TIME_PENALTY with a printed warning.
    No silent fallbacks — bad formats surface here.
    """
    xc_id    = recording.get("id", "?")
    raw_time = recording.get("time", "")

    if not raw_time:
        # print(f"  [TimePrx] XC{xc_id}: NO time field in metadata "
        #       f"→ penalty ×{_NO_TIME_PENALTY}")
        return _NO_TIME_PENALTY

    # Parse — no try/except swallowing: we want to see exactly what breaks
    parts = raw_time.strip().split(":")
    if len(parts) < 2:
        # print(f"  [TimePrx] XC{xc_id}: UNEXPECTED time format {raw_time!r} "
        #       f"(expected HH:MM, got {len(parts)} part(s)) "
        #       f"→ penalty ×{_NO_TIME_PENALTY}")
        return _NO_TIME_PENALTY

    try:
        rec_hour = int(parts[0])
        rec_min  = int(parts[1])
    except ValueError as e:
        # print(f"  [TimePrx] XC{xc_id}: NON-INTEGER in time {raw_time!r} ({e}) "
        #       f"→ penalty ×{_NO_TIME_PENALTY}")
        return _NO_TIME_PENALTY

    if not (0 <= rec_hour <= 23) or not (0 <= rec_min <= 59):
        # print(f"  [TimePrx] XC{xc_id}: OUT-OF-RANGE time {raw_time!r} "
        #       f"(hour={rec_hour}, min={rec_min}) "
        #       f"→ penalty ×{_NO_TIME_PENALTY}")
        return _NO_TIME_PENALTY

    now         = datetime.now()
    now_decimal = now.hour + now.minute / 60.0
    rec_decimal = rec_hour + rec_min / 60.0

    # Circular distance on 24h clock — always the shorter arc
    raw_dist = abs(now_decimal - rec_decimal)
    distance = min(raw_dist, 24.0 - raw_dist)

    # Sigmoid gate: 1 / (1 + exp(k * (distance - gate)))
    k          = _TIME_PROXIMITY_SIGMOID_K
    gate       = _TIME_PROXIMITY_GATE_HOURS
    multiplier = 1.0 / (1.0 + math.exp(k * (distance - gate)))

    # print(f"  [TimePrx] XC{xc_id}: rec={raw_time} "
    #       f"now={now.strftime('%H:%M')} "
    #       f"dist={distance:.2f}h "
    #       f"gate=±{gate}h k={k} "
    #       f"→ ×{multiplier:.4f}")

    return multiplier


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
    abundance: "AbundanceContext | None" = None,
) -> float:
    """
    Compute the effective activity threshold for a specific recording.

    Starts from the base time-of-day threshold, then applies per-type
    condition modifiers so that rain-loving types (frogs) seem more active
    in rain while delicate singers seem quieter — rather than everything
    being suppressed or boosted uniformly.

    Condition modifiers are applied multiplicatively in priority order:
      rain (binary) -> wind (if above threshold) -> abundance (Bortle scale)

    Each weather modifier is derived from the recording's type tokens via
    _apply_condition_modifier(), so compound types are handled correctly.

    Abundance applies a flat multiplier: low abundance lowers the threshold,
    making the activity_level > threshold condition easier to satisfy — i.e.
    silence fires more often. Bortle 1 -> x0.35; Bortle 9 -> x1.0 (no effect).
    """
    threshold = base_table.get(time_tag, default)

    if weather.is_raining:
        threshold *= _apply_condition_modifier(tokens, _RAIN_THRESHOLD_MODIFIERS)

    if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
        threshold *= _apply_condition_modifier(tokens, _WIND_THRESHOLD_MODIFIERS)

    if abundance is not None:
        threshold *= abundance.silence_threshold_multiplier

    return threshold


def _score_recording(
    recording: dict,
    time_tag: str,
    weather: WeatherContext | None = None,
) -> float:
    """
    Score a recording for selection at the current time_tag.

    Signal priority (explicit, not buried in an additive sum):

      1. TIME PROXIMITY — multiplicative gate applied first.
         A recording made at the wrong hour cannot be rescued by good type
         tokens. Uses a sigmoid with a hard gate at ±2h. If this returns
         near-zero the function exits early — no wasted computation.

      2. ADDITIVE BASE — quality, richness, type affinity.
         Type preferences compressed to [0.0, 0.5] max bonus so they inform
         but cannot overpower a poor time match.

      3. WEATHER multipliers — global wind floor + per-type rain/wind
         modifiers. Applied last, unchanged from before.

    Every component is printed so the selection reasoning is fully observable.
    """
    xc_id = recording.get("id", "?")
    en    = recording.get("en") or recording.get("gen", "?")
    #print(f"  [Score] ── XC{xc_id} ({en}) tag={time_tag!r}")

    # ── 1. TIME PROXIMITY (primary gate) ────────────────────────────────────
    time_mult = _time_proximity_multiplier(recording, time_tag)

    # Early exit — saves scoring overhead for recordings that won't be picked
    if time_mult < 0.02:
        # print(f"  [Score] XC{xc_id}: gated out (time_mult={time_mult:.4f} < 0.02) → 0.0")
        return 0.0

    # ── 2. ADDITIVE BASE ────────────────────────────────────────────────────
    base = 1.0

    # Type affinity — max bonus compressed to 0.5 (was 4.0)
    # Type prefs are secondary: they inform within a valid time window,
    # they do not create one.
    tokens    = _tokenise_type(recording.get("type", ""))
    preferred = _TIME_PREFERENCES.get(time_tag, {})
    if tokens:
        raw_bonus  = max((preferred.get(tok, 0.0) for tok in tokens), default=0.0)
        type_bonus = (raw_bonus / 4.0) * 0.5   # compress [0–4] → [0–0.5]
        base      += type_bonus
        # print(f"  [Score] XC{xc_id}: tokens={tokens} "
        #       f"raw_pref={raw_bonus:.2f} → type_bonus={type_bonus:.3f}")
    # else:
    #     print(f"  [Score] XC{xc_id}: no type tokens — no type bonus")

    # Quality
    q_raw = recording.get("q", "")
    q_val = {"A": 0.25, "B": 0.0}.get(q_raw, 0.0)
    base += q_val
    # print(f"  [Score] XC{xc_id}: quality={q_raw!r} → q_bonus={q_val}")

    # Species richness
    also          = recording.get("also", [])
    richness_bonus = min(len(also), 3) * 0.05
    base          += richness_bonus
    # print(f"  [Score] XC{xc_id}: also={len(also)} species → richness_bonus={richness_bonus:.2f}")

    # Apply time gate to base
    score = base * time_mult
    # print(f"  [Score] XC{xc_id}: base={base:.3f} × time_mult={time_mult:.4f} = {score:.4f}")

    # ── 3. WEATHER ──────────────────────────────────────────────────────────
    if weather:
        pre_weather = score
        score      *= weather.score_multiplier
        # print(f"  [Score] XC{xc_id}: wind_multiplier={weather.score_multiplier:.3f} "
        #       f"→ {score:.4f}")

        if weather.is_raining:
            rain_mod = _apply_condition_modifier(tokens, _RAIN_SCORE_MODIFIERS)
            score   *= rain_mod
            # print(f"  [Score] XC{xc_id}: rain_mod={rain_mod:.3f} → {score:.4f}")

        if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
            wind_mod = _apply_condition_modifier(tokens, _WIND_SCORE_MODIFIERS)
            score   *= wind_mod
            # print(f"  [Score] XC{xc_id}: wind_mod={wind_mod:.3f} → {score:.4f}")

        # print(f"  [Score] XC{xc_id}: post-weather {pre_weather:.4f} → {score:.4f}")

    # print(f"  [Score] XC{xc_id}: ══ FINAL = {score:.4f}")
    return score


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
    abundance: "AbundanceContext | None" = None,
) -> list[dict]:
    """
    Draw k recordings by weighted score, with optional species-diversity enforcement.

    diversity_weight (from AbundanceContext) controls how hard deduplication is applied:
      Bortle 9 (diversity_weight=1.0) — full species-diversity pass, as before.
      Bortle 5  (diversity_weight=0.44) — probabilistic: each candidate is kept in
                the diversity pass only if random() < diversity_weight, otherwise it
                flows through weighted sampling as-is.
      Bortle 1  (diversity_weight=0.0) — no diversity pass at all. Dominant/high-scored
                species repeat freely, exactly as a species-poor habitat sounds.
    """
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

    diversity_weight = abundance.diversity_weight if abundance is not None else 1.0

    if diversity_weight <= 0.0:
        # Bortle 1 — no diversity enforcement whatsoever. Take the first k candidates
        # directly from weighted sampling. The same sparrow will repeat.
        result = candidates[:k]
        unique_species = len({r.get("en", "").strip() or r.get("id", "") for r in result})
        print(f"[XenoCantoProvider] Weighted sample: drew {len(result)} from "
              f"{len(recordings)} candidates ({unique_species} unique species, "
              f"diversity enforcement: none, Bortle={abundance.level if abundance else '?'}).")
        return result

    seen_species: set[str]  = set()
    diverse:      list[dict] = []
    overflow:     list[dict] = []
    for r in candidates:
        sp = r.get("en", "").strip() or r.get("id", "")
        # Probabilistic deduplication: at full weight (1.0) always deduplicate;
        # at partial weight, sometimes let a repeat species slip through.
        if sp not in seen_species or random.random() >= diversity_weight:
            if sp not in seen_species:
                seen_species.add(sp)
            diverse.append(r)
        else:
            overflow.append(r)
        if len(diverse) == k:
            break

    while len(diverse) < k and overflow:
        diverse.append(overflow.pop(0))

    unique_species = len({r.get("en", "").strip() or r.get("id", "") for r in diverse})
    print(f"[XenoCantoProvider] Weighted sample: drew {len(diverse)} from "
          f"{len(recordings)} candidates ({unique_species} unique species, "
          f"diversity_weight={diversity_weight:.2f}, Bortle={abundance.level if abundance else '?'}).")
    return diverse



# ---------------------------------------------------------------------------
# Weather-aware selection size
# ---------------------------------------------------------------------------

def _selection_size_for(
    time_tag: str,
    weather: WeatherContext,
    abundance: "AbundanceContext | None" = None,
) -> int:
    """
    Compute how many recordings to include in the active selection.

    Base size comes from _SELECTION_SIZE_BY_TAG (or default). Two independent
    axes then shrink the pool multiplicatively:

      Weather  — rain suppresses most species; strong wind masks delicate calls.
                 Both factors apply multiplicatively if conditions coincide.

      Abundance (Bortle scale) — low abundance means fewer species are present
                 at all, so a smaller pool better reflects reality than sampling
                 the same N with lower scores. Bortle 9: full pool. Bortle 1:
                 15% of the pool, potentially just 1-2 recordings.

    The floor is 1, not 3 — a deep urban core genuinely may have only one
    representative species audible.
    """
    size = _SELECTION_SIZE_BY_TAG.get(time_tag, _SELECTION_SIZE_DEFAULT)

    if weather.is_raining:
        size = round(size * _SELECTION_SIZE_RAIN_FACTOR)

    if (weather.wind_speed or 0.0) > _SELECTION_SIZE_WIND_THRESHOLD:
        size = round(size * _SELECTION_SIZE_WIND_FACTOR)

    if abundance is not None:
        size = round(size * abundance.selection_size_multiplier)

    size = max(1, size)

    bortle_str = f"Bortle={abundance.level}/9" if abundance is not None else "Bortle=n/a"
    print(f"[XenoCantoProvider] Selection size: {size} "
          f"(tag={time_tag!r} {bortle_str} "
          f"rain={'yes' if weather.is_raining else 'no'} "
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