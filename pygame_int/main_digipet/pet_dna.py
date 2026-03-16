# pet_dna.py
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from pygame_int.main_digipet.gui_pet import EmoteProfile


@dataclass
class PetDNA:
    """
    The immutable visual identity of a pet.

    wave_freq      -- number of scallops (1-14)
    amplitude      -- edge deformation (0.0-0.60)
    droop          -- posture bias (-0.25-0.25)
    blend_ms       -- emotion transition speed (900-15000)
    speed_base     -- base oscillation rate (0.45-2.5)
    noise_ceiling  -- max noise (0.0-0.9)
    stroke_width   -- outline thickness in pixels (2-8)
    """

    # ClassVar — not a dataclass field, never appears in __init__
    # Source of truth for all valid ranges: field_key -> (min, max, type)
    # Used by validate_field(), from_seed(), and the DNA selector GUI.
    RANGES: ClassVar[dict] = {
        "wave_freq":     (1,     14,    int),
        "amplitude":     (0.0,   0.60,  float),
        "droop":         (-0.25, 0.25,  float),
        "blend_ms":      (900,   15000, int),
        "speed_base":    (0.45,  2.5,   float),
        "noise_ceiling": (0.0,   0.9,   float),
        "stroke_width":  (2,     8,     int),
    }

    wave_freq:     int
    amplitude:     float
    droop:         float
    blend_ms:      int
    speed_base:    float
    noise_ceiling: float
    stroke_width:  int

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @classmethod
    def validate_field(cls, field_key: str, value) -> bool:
        """
        Returns True if value is within the valid range for field_key.
        Handles type coercion so strings from text inputs work too.
        """
        if field_key not in cls.RANGES:
            return False
        lo, hi, typ = cls.RANGES[field_key]
        try:
            v = typ(value)
            return lo <= v <= hi
        except (TypeError, ValueError):
            return False

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_seed(self) -> str:
        return (
            f"{self.wave_freq}"
            f":{self.amplitude:.2f}"
            f":{self.droop:.2f}"
            f":{self.blend_ms}"
            f":{self.speed_base:.2f}"
            f":{self.noise_ceiling:.2f}"
            f":{self.stroke_width}"
        )

    @classmethod
    def from_seed(cls, seed: str) -> "PetDNA":
        try:
            parts = seed.strip().split(":")
            if len(parts) != 7:
                raise ValueError(f"Expected 7 parts, got {len(parts)}")

            raw = {
                "wave_freq":     int(parts[0]),
                "amplitude":     float(parts[1]),
                "droop":         float(parts[2]),
                "blend_ms":      int(parts[3]),
                "speed_base":    float(parts[4]),
                "noise_ceiling": float(parts[5]),
                "stroke_width":  int(parts[6]),
            }

            # Validate each field against ranges
            invalid = [k for k, v in raw.items() if not cls.validate_field(k, v)]
            if invalid:
                raise ValueError(f"Fields out of range: {invalid}")

            return cls(**raw)
        except Exception as exc:
            raise ValueError(f"[pet_dna] Invalid seed {seed!r}: {exc}") from exc

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    @classmethod
    def generate_random(cls) -> "PetDNA":
        def _bimodal(lo_min, lo_max, hi_min, hi_max, decimals=2):
            if random.random() < 0.5:
                return round(random.uniform(lo_min, lo_max), decimals)
            else:
                return round(random.uniform(hi_min, hi_max), decimals)

        return cls(
            wave_freq     = random.randint(1, 14),
            amplitude     = round(random.uniform(0.0, 0.60), 2),
            droop         = round(random.uniform(-0.25, 0.25), 2),
            blend_ms      = random.randint(900, 15000),
            speed_base    = round(random.uniform(0.45, 2.5), 2),
            noise_ceiling = round(random.uniform(0.0, 0.9), 2),
            stroke_width  = random.randint(2, 8),
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"PetDNA(freq={self.wave_freq}, amp={self.amplitude}, "
            f"droop={self.droop}, blend={self.blend_ms}ms, "
            f"speed={self.speed_base}, noise_ceil={self.noise_ceiling}, "
            f"stroke={self.stroke_width})"
        )


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------

def build_profiles(dna: "PetDNA") -> dict:
    from pygame_int.main_digipet.gui_pet import EmoteProfile

    freq      = float(dna.wave_freq)
    amp       = dna.amplitude
    droop     = dna.droop
    speed     = dna.speed_base
    noise_cap = dna.noise_ceiling

    def _noise(raw: float) -> float:
        return min(raw, noise_cap)

    def _make(
        speed_mult:   float,
        noise:        float,
        pulse_spread: float,
        amp_mult:     float = 1.0,
        extra_droop:  float = 0.0,
    ) -> "EmoteProfile":
        return EmoteProfile(
            amplitude    = amp * amp_mult,
            wave_weights = [1.0],
            wave_freqs   = [freq],
            noise_weight = _noise(noise),
            speed        = speed * speed_mult,
            droop        = droop + extra_droop,
            pulse_spread = pulse_spread,
        )

    carousel = math.tau / freq
    ripples  = carousel * 2
    sadness  = math.e / freq

    return {
        "neutral":  _make(speed_mult=1.0,  noise=0.0,  pulse_spread=carousel),
        "happy":    _make(speed_mult=2.0,  noise=0.0,  pulse_spread=ripples,    amp_mult=1.5),
        "sad":      _make(speed_mult=0.4,  noise=0.05, pulse_spread=sadness,    amp_mult=0.85, extra_droop=0.25),
        "angry":    _make(speed_mult=2.5,  noise=0.85, pulse_spread=ripples*2,  amp_mult=2.5,  extra_droop=-0.45),
        "excited":  _make(speed_mult=2.5,  noise=0.0,  pulse_spread=2.0,        amp_mult=1.2),
        "thinking": _make(speed_mult=0.5,  noise=0.0,  pulse_spread=0.0,        amp_mult=1.0),
        "curious":  _make(speed_mult=1.2,  noise=0.0,  pulse_spread=0.2,        amp_mult=2.0,  extra_droop=0.5),
        "confused": _make(speed_mult=0.85, noise=0.35, pulse_spread=-carousel,  amp_mult=1.5,  extra_droop=0.25),
        "sleep":    _make(speed_mult=0.2,  noise=0.0,  pulse_spread=0.0,        amp_mult=0.4,  extra_droop=0.2),
    }