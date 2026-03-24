_SELECTION_CACHE_PATH = ".cache/xeno_canto_selection.json"
_SELECTION_TTL        = 21600  # 6 hours

_SELECTION_CACHE_DIR = ".cache"
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
    "morning": 10,
    "noon": 4,
}
_SELECTION_SIZE_DEFAULT: int = 8

# How much bad weather can shrink the selection (proportional to conditions).
# Rain or strong wind mean fewer species are audible, so a smaller pool
# is more realistic than sampling the same N recordings with lower scores.
_SELECTION_SIZE_RAIN_FACTOR: float = 0.6    # e.g. 10 → 6 in rain
_SELECTION_SIZE_WIND_THRESHOLD: float = 25.0  # km/h above which wind shrinks pool
_SELECTION_SIZE_WIND_FACTOR: float = 0.75   # e.g. 10 → 7-8 in strong wind


# ---------------------------------------------------------------------------
# Time proximity — primary scoring signal
# ---------------------------------------------------------------------------

# Sigmoid steepness. Higher = harder gate. At k=3.0 a recording 2h away
# scores ~0.05, which is effectively excluded from weighted_sample.
_TIME_PROXIMITY_SIGMOID_K: float = 3.0

# The ±h window around now where a recording is considered "on time".
# Beyond this the sigmoid is already near zero.
_TIME_PROXIMITY_GATE_HOURS: float = 2.0

# Multiplier given to recordings with no time metadata at all.
# Clearly sub-par but not zero — it exists for a reason, we just can't place it.
_NO_TIME_PENALTY: float = 0.30

# REMOVED: _TIME_PROXIMITY_WEIGHT = 1.0
# Time is no longer an additive bonus — it is a multiplicative gate.
# Deleting this constant so nothing silently imports a stale value.

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
    "late night":     {"dawn song"},
    "early morning":  {"nocturnal flight call"},
    "morning":        {"nocturnal flight call"},
    "noon":           {"nocturnal flight call", "dawn song"},
    "afternoon":      {"nocturnal flight call", "dawn song"},
    "late afternoon": {"nocturnal flight call"},
    "night":         {"dawn song"}
}



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



# ---------------------------------------------------------------------------
# Wildlife activity thresholds
# ---------------------------------------------------------------------------

_ACTIVITY_THRESHOLD_FULL: dict[str, float] = {
    "late night":     2 / 4,
    "early morning":  9 / 10,
    "morning":        3 / 5,
    "noon":           3 / 5,
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



