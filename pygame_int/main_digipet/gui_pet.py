# gui_pet.py
#
# Responsibilities
# ----------------
# All rendering of the pet circle, including the per-frame edge oscillation
# that makes the surface feel alive.  Replaces the two pygame.draw.circle
# calls that previously lived in gui.py.
#
# Public API
# ----------
#   draw_pet(screen, cx, cy, current_time_ms)
#       Drop-in replacement for the old circle draw block in gui.py.
#       Reads state.pet_color, state.current_emote, state.pet_radius.
#
# Edge oscillation model
# ----------------------
# The pet perimeter is a polygon of N_POINTS vertices.  Each vertex i at
# angle θ_i is displaced radially by:
#
#   shape_k   = sin(f_k * θ_i + phase_k)           ← fixed peak positions, no rotation
#   breathe   = sin(speed * t + θ_i * pulse_spread) ← in/out oscillation over time
#   wave      = Σ_k  w_k * shape_k * breathe
#
#   r_i = base_radius
#       + A_structured * wave                        ← scallops breathing in place
#       + A_noise      * per_point_noise_i(t)        ← random texture
#       + droop * base_radius * (1 - cos(θ_i)) / 2  ← bottom-sag (sad)
#
# Key property: shape_k has no time term, so the scallop pattern never rotates.
# breathe makes the amplitude of each scallop oscillate over time.
# pulse_spread staggers neighbours — spread=0 means the whole circle pulses
# together (expands/contracts); spread~0.7 gives each point its own phase so
# they bob independently without any rotation.
#
# On an emote change all values blend smoothly over BLEND_DURATION_MS.
#
# Drawing
# -------
# Both the fill polygon and the stroke polygon follow the deformed perimeter
# ("fully organic" mode).  The stroke width matches what gui.py used before
# (config.PET_STROKE_WIDTH if it exists, else 5 px).

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

import pygame

from pygame_int import config, state
from pygame_int.main_digipet.pet_dna import PetDNA, build_profiles

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------

N_POINTS: int = 128          # polygon resolution
_BLEND_DURATION_MS_FALLBACK: int = 400  # used only before state.pet_dna is available

# ---------------------------------------------------------------------------
# Emote profile
# ---------------------------------------------------------------------------

@dataclass
class EmoteProfile:
    """
    All parameters that control the edge oscillation for one emotional state.

    wave_weights   — relative amplitudes for each harmonic (normalised to sum=1).
    wave_freqs     — spatial frequencies (scallop count around perimeter).
    amplitude      — peak radial displacement as a fraction of base_radius.
                     Scaled by actual radius each frame so it stays proportional.
    noise_weight   — fraction of amplitude contributed by per-point noise.
    speed          — oscillation rate: how fast each point bobs in/out.
    droop          — bottom-sag bias [0..1].  0 = symmetric, 1 = strong sag.
    pulse_spread   — phase stagger between neighbours (radians per radian of θ).
                     0   = all points pulse in/out together (whole circle breathes).
                     0.7 = neighbours slightly out of phase (independent bobbing).
                     1.5 = strong wave travelling around perimeter.
    phase_offsets  — per-harmonic phase offset (radians); auto-filled if empty.
    """
    amplitude:     float
    wave_weights:  List[float]
    wave_freqs:    List[float]
    noise_weight:  float
    speed:         float
    droop:         float = 0.0
    pulse_spread:  float = 0.7   # stagger between neighbours
    phase_offsets: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Fill missing phase offsets with deterministic but varied values.
        while len(self.phase_offsets) < len(self.wave_freqs):
            k = len(self.phase_offsets)
            self.phase_offsets.append(k * 1.2732)   # irrational multiplier

        # Normalise wave_weights so they sum to 1.
        total = sum(self.wave_weights) or 1.0
        self.wave_weights = [w / total for w in self.wave_weights]


# ---------------------------------------------------------------------------
# Profiles per emote
# ---------------------------------------------------------------------------
# Tuning guide:
#   amplitude  → how far the surface deforms (pixels, relative to radius)
#   wave_freqs → number of bumps / valleys around the circle
#   noise_weight → how unpredictable / spiky the texture is
#   speed      → oscillation rate (higher = more agitated)
#   droop      → asymmetric downward sag (sadness)


# ---------------------------------------------------------------------------
# Profile cache  (rebuilt whenever state.pet_dna changes)
# ---------------------------------------------------------------------------
# Profiles are not hardcoded here anymore — they are generated from the
# pet's DNA by pet_dna.build_profiles().  The cache is invalidated lazily
# by comparing the stored seed against state.pet_dna.to_seed() each frame.

_cached_profiles: dict[str, EmoteProfile] = {}
_cached_dna_seed: str = ""


def _get_profiles() -> dict[str, EmoteProfile]:
    """
    Return the current profile dict, rebuilding from DNA if it changed.
    Falls back to a safe default if state.pet_dna is not yet set.
    """
    global _cached_profiles, _cached_dna_seed


    dna = getattr(state, "pet_dna", None)

    if dna is None:
        print("[gui_pet] Warning: state.pet_dna not set yet — using fallback profiles")
        # state.pet_dna not set yet — use a safe neutral fallback
        if not _cached_profiles:
            dna = PetDNA(
                wave_freq=12, amplitude=0.12, droop=0.0,
                blend_ms=400, speed_base=1.0, noise_ceiling=0.5,
            )
            _cached_profiles = build_profiles(dna)
            _cached_dna_seed = dna.to_seed()
        return _cached_profiles

    seed = dna.to_seed()
    if seed != _cached_dna_seed:
        print(f"[gui_pet] Rebuilding profiles for DNA seed: {seed}")
        _cached_profiles = build_profiles(dna)
        _cached_dna_seed = seed

    return _cached_profiles


def _get_blend_duration_ms() -> int:
    """Read blend duration from DNA, fall back to constant if not ready."""
    dna = getattr(state, "pet_dna", None)
    return dna.blend_ms if dna is not None else _BLEND_DURATION_MS_FALLBACK



# ---------------------------------------------------------------------------
# Per-point noise seeds  (stable across frames, one set per N_POINTS)
# ---------------------------------------------------------------------------
_rng = random.Random(42)
_NOISE_SEEDS: List[float] = [_rng.uniform(0, math.tau) for _ in range(N_POINTS)]


def _point_noise(i: int, t_s: float, speed: float) -> float:
    """
    Smooth per-point noise in [-1, 1] that evolves slowly over time.
    Uses two harmonics of the seed so adjacent points aren't too correlated.
    """
    s = _NOISE_SEEDS[i]
    return (
        0.6 * math.sin(s       + t_s * speed * 0.9)
      + 0.4 * math.sin(s * 1.7 + t_s * speed * 0.6)
    )


# ---------------------------------------------------------------------------
# EdgeOscillator
# ---------------------------------------------------------------------------

class EdgeOscillator:
    """
    Maintains blend state between emote profiles and generates the polygon
    point list every frame.  Profiles are read from DNA via _get_profiles()
    so they automatically reflect the loaded pet.
    """

    def __init__(self) -> None:
        self._current_emote: str = state.current_emote
        # Profiles are not available at import time — deferred to first frame.
        self._from_profile:  EmoteProfile | None = None
        self._to_profile:    EmoteProfile | None = None
        self._blend_start_ms: int = 0
        self._blend_alpha:    float = 1.0   # 0 = fully from, 1 = fully to

    def _ensure_profiles_ready(self) -> None:
        if self._from_profile is None:
            profiles = _get_profiles()
            # Use the actual current emote, not hardcoded neutral
            emote = getattr(state, "current_emote", "neutral") or "neutral"
            self._current_emote = emote          # sync so _sync_emote sees no change
            profile = profiles.get(emote) or profiles.get("neutral")
            self._from_profile = profile
            self._to_profile   = profile

    # ------------------------------------------------------------------
    # Emote change (called each frame — only triggers a blend when needed)
    # ------------------------------------------------------------------

    def _sync_emote(self, current_time_ms: int) -> None:
        self._ensure_profiles_ready()
        emote = getattr(state, "current_emote", "neutral") or "neutral"
        if emote == self._current_emote:
            return
        profiles = _get_profiles()
        self._from_profile   = self._blended_profile(current_time_ms)
        self._to_profile     = profiles.get(emote) or profiles.get("neutral") or self._from_profile
        self._blend_start_ms = current_time_ms
        self._blend_alpha    = 0.0
        self._current_emote  = emote
        print(f"[gui_pet] emote transition → {emote!r}")

    def _blended_profile(self, current_time_ms: int) -> EmoteProfile:
        """Return a snapshot of the currently interpolated profile."""
        a = self._blend_alpha
        f, t_ = self._from_profile, self._to_profile
        # We only need the scalar fields for the snapshot.
        snapped = EmoteProfile(
            amplitude    = _lerpf(f.amplitude,    t_.amplitude,    a),
            wave_weights = f.wave_weights,
            wave_freqs   = f.wave_freqs,
            noise_weight = _lerpf(f.noise_weight, t_.noise_weight, a),
            speed        = _lerpf(f.speed,        t_.speed,        a),
            droop        = _lerpf(f.droop,        t_.droop,        a),
            pulse_spread = _lerpf(f.pulse_spread, t_.pulse_spread, a),
            phase_offsets= f.phase_offsets,
        )
        return snapped

    # ------------------------------------------------------------------
    # Main per-frame call
    # ------------------------------------------------------------------

    def get_points(
        self,
        cx: float,
        cy: float,
        base_radius: float,
        current_time_ms: int,
    ) -> List[Tuple[int, int]]:
        """
        Return the N_POINTS polygon vertices for this frame.
        cx, cy       — centre of the pet (post animation offset)
        base_radius  — state.pet_radius at this moment
        """
        self._sync_emote(current_time_ms)

        # Advance blend alpha using DNA's blend duration.
        elapsed = current_time_ms - self._blend_start_ms
        self._blend_alpha = min(1.0, elapsed / _get_blend_duration_ms())
        a = _ease_in_out(self._blend_alpha)

        f_p = self._from_profile
        t_p = self._to_profile

        # Interpolate scalar parameters.
        amplitude    = _lerpf(f_p.amplitude,    t_p.amplitude,    a)
        noise_weight = _lerpf(f_p.noise_weight, t_p.noise_weight, a)
        speed        = _lerpf(f_p.speed,        t_p.speed,        a)
        droop        = _lerpf(f_p.droop,        t_p.droop,        a)
        pulse_spread = _lerpf(f_p.pulse_spread, t_p.pulse_spread, a)

        # Use the to-profile's wave structure once blend > 0.5, otherwise from.
        # This avoids artefacts from mixing two different freq arrays.
        profile = t_p if a >= 0.5 else f_p
        wave_weights  = profile.wave_weights
        wave_freqs    = profile.wave_freqs
        phase_offsets = profile.phase_offsets

        t_s = current_time_ms / 1000.0
        A   = amplitude * base_radius           # absolute pixel displacement
        A_structured = A * (1.0 - noise_weight)
        A_noise      = A * noise_weight

        points: List[Tuple[int, int]] = []

        for i in range(N_POINTS):
            theta = (i / N_POINTS) * math.tau

            # Shape x breathe model — no rotation.
            #
            # shape(theta)  — defines fixed peak/valley positions around the
            #                 perimeter. Never changes over time so the scallop
            #                 pattern stays locked in place.
            #
            # breathe(t)    — makes each point oscillate in/out over time.
            #                 pulse_spread staggers neighbours so they aren't
            #                 all in sync: spread=0 → whole circle pulses
            #                 together; spread~0.7 → independent bobbing feel.
            wave = 0.0
            for w, freq, phase in zip(wave_weights, wave_freqs, phase_offsets):
                shape   = math.sin(freq * theta + phase)
                breathe = math.sin(speed * t_s + theta * pulse_spread)
                wave += w * shape * breathe

            # Per-point noise.
            noise = _point_noise(i, t_s, speed)

            # Droop: shifts the bottom of the circle outward/downward.
            # (1 - cos θ) / 2 peaks at θ=π (bottom of circle).
            sag = droop * base_radius * (1.0 - math.cos(theta)) / 2.0

            r = base_radius + A_structured * wave + A_noise * noise + sag

            px = cx + r * math.cos(theta)
            py = cy + r * math.sin(theta)
            points.append((int(px), int(py)))

        return points


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_oscillator = EdgeOscillator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lerpf(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _ease_in_out(t: float) -> float:
    """Smooth-step (cubic ease in-out)."""
    return t * t * (3.0 - 2.0 * t)


def _get_stroke_width() -> int:
    return getattr(config, "PET_STROKE_WIDTH", 5)


# ---------------------------------------------------------------------------
# Public draw function  (call this from gui.py)
# ---------------------------------------------------------------------------

def draw_pet(
    screen: pygame.Surface,
    cx: float,
    cy: float,
    current_time_ms: int,
) -> None:
    """
    Draw the pet at (cx, cy) using state.pet_radius, state.pet_color.

    Replaces these two lines from gui.py:
        pygame.draw.circle(screen, config.BLACK,    (int(cx), int(cy)), state.current_radius)
        pygame.draw.circle(screen, state.pet_color, (int(cx), int(cy)), state.current_radius, 5)

    Both the fill and stroke follow the deformed perimeter polygon.
    """
    base_radius = state.pet_radius
    if base_radius <= 0:
        return

    points = _oscillator.get_points(cx, cy, base_radius, current_time_ms)

    if len(points) < 3:
        # Fallback: plain circle if something went wrong.
        pygame.draw.circle(screen, config.BLACK,    (int(cx), int(cy)), int(base_radius))
        pygame.draw.circle(screen, state.pet_color, (int(cx), int(cy)), int(base_radius), _get_stroke_width())
        return

    # Fill.
    pygame.draw.polygon(screen, config.BLACK, points)

    # Stroke (outline).
    dna = getattr(state, "pet_dna", None)
    stroke = dna.stroke_width if dna is not None else _get_stroke_width()
    pygame.draw.polygon(screen, state.pet_color, points, stroke)