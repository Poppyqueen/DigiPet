# animation.py
#
# Architecture
# ------------
# Each animation is a self-contained BaseAnimation subclass that owns its
# phase state, transition logic, and offset/size calculation.  No animation
# touches another animation's data.
#
# The AnimationController maintains a priority-ordered list of animations
# and exposes the same two public functions the game loop has always called:
#
#   update_animation_state(current_time_ms) -> bool
#   calculate_circle_offset(current_time_ms) -> (float, float)
#
# Adding a new animation
# ----------------------
# 1. Subclass BaseAnimation and implement:
#      is_active()              — True while running
#      update(t)                — advance phase timers / handle transitions
#      get_offset(t) -> (x, y) — return positional offset
#      get_radius_scale() -> float  — optional size multiplier (default 1.0)
#      clear()                  — reset all owned state to idle
# 2. Register an instance in _REGISTRY (priority order, highest first).
# 3. Expose a module-level starter function that delegates to the instance.
#
# That's it.  No other file needs to change.

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import Tuple

import pygame

from pygame_int import config, state
from pygame_int.main_digipet import gui


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Offset = Tuple[float, float]


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseAnimation(ABC):
    """
    Contract that every animation must fulfil.

    Subclasses keep all their mutable data as instance attributes — they
    NEVER read or write state vars that belong to another animation.
    The only shared state they touch is ``state.pet_radius`` (write-only,
    via get_radius_scale()) and ``state.current_radius`` (read-only).
    """

    # Override in subclasses to give them a name used in log messages.
    name: str = "unnamed"

    @abstractmethod
    def is_active(self) -> bool:
        """Return True while this animation is running."""

    @abstractmethod
    def update(self, current_time_ms: int) -> None:
        """Advance internal phase timers; perform phase transitions."""

    @abstractmethod
    def get_offset(self, current_time_ms: int) -> Offset:
        """Return the (x, y) positional offset this animation contributes."""

    def get_radius_scale(self) -> float:
        """
        Multiplier applied to state.current_radius each frame.
        Override if the animation changes the pet's size.
        """
        return 1.0

    @abstractmethod
    def clear(self) -> None:
        """Reset all owned state so is_active() returns False."""

    # ------------------------------------------------------------------
    # Guard helpers (used by starter functions)
    # ------------------------------------------------------------------

    def _is_resting(self) -> bool:
        return pygame.time.get_ticks() < state.autonomous_action_paused_until_ms

    def _warn_resting(self) -> None:
        gui.gui_text_utils.add_message_to_history(
            f"System: Cannot trigger {self.name} while bot is resting.", "system"
        )


# ---------------------------------------------------------------------------
# Easing utilities
# ---------------------------------------------------------------------------

def _ease_out_quad(t: float) -> float:
    """Ease-out quadratic: smooth deceleration into the target position."""
    return -(t) * (t - 2)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# Individual animations
# ---------------------------------------------------------------------------

class SleepAnimation(BaseAnimation):
    """
    Three-phase sleep sequence:
      1 → Falling asleep  (drop + shrink)
      2 → Deep sleep loop (sway + random twitches)
      3 → Waking up       (rise + restore size)
    """

    name = "sleep"

    def __init__(self):
        self._phase: int = 0               # 0 = idle
        self._phase_start: int = 0
        self._original_radius: float | None = None
        self._twitch_active: bool = False
        self._twitch_start: int = 0
        self._next_twitch: int = 0

    # -- Public interface used by the controller --

    def is_active(self) -> bool:
        return self._phase != 0

    def start(self) -> None:
        if self._phase != 0:
            return
        t = pygame.time.get_ticks()
        self._phase = 1
        self._phase_start = t
        self._original_radius = state.pet_radius

    def wake_up(self) -> None:
        t = pygame.time.get_ticks()
        if self._phase in (1, 2):
            self._phase = 3
            self._phase_start = t

    # -- BaseAnimation contract --

    def update(self, t: int) -> None:
        elapsed = t - self._phase_start

        if self._phase == 1:                         # Falling asleep
            if elapsed >= config.SLEEP_DROP_DURATION_MS:
                self._phase = 2
                self._phase_start = t
                self._twitch_active = False
                self._next_twitch = t + random.randint(
                    config.SLEEP_TWITCH_MIN_INTERVAL_MS,
                    config.SLEEP_TWITCH_MAX_INTERVAL_MS,
                )

        elif self._phase == 2:                       # Deep sleep
            if self._twitch_active:
                if t - self._twitch_start >= config.SLEEP_TWITCH_DURATION_MS:
                    self._twitch_active = False
                    self._next_twitch = t + random.randint(
                        config.SLEEP_TWITCH_MIN_INTERVAL_MS,
                        config.SLEEP_TWITCH_MAX_INTERVAL_MS,
                    )
            elif t >= self._next_twitch:
                self._twitch_active = True
                self._twitch_start = t

        elif self._phase == 3:                       # Waking up
            if elapsed >= config.SLEEP_WAKE_DURATION_MS:
                self.clear()
                print("[animation] Sleep: fully awake.")

    def get_offset(self, t: int) -> Offset:
        if self._phase == 1:
            p = _ease_out_quad(min(1.0, (t - self._phase_start) / config.SLEEP_DROP_DURATION_MS))
            return 0.0, p * config.SLEEP_DROP_AMOUNT

        if self._phase == 2:
            elapsed_sleep = t - self._phase_start
            sway = (elapsed_sleep / 1000.0) * config.SLEEP_SWAY_FREQUENCY_HZ * 2 * math.pi
            ox = config.SLEEP_SWAY_AMPLITUDE_X * math.sin(sway)
            oy = config.SLEEP_DROP_AMOUNT + config.SLEEP_SWAY_AMPLITUDE_Y * math.sin(sway)
            if self._twitch_active:
                elapsed_twitch = t - self._twitch_start
                angle = (elapsed_twitch / 1000.0) * config.SLEEP_TWITCH_FREQUENCY_HZ * 2 * math.pi
                ox += config.SLEEP_TWITCH_INTENSITY * math.sin(angle)
                oy += config.SLEEP_TWITCH_INTENSITY * math.cos(angle)
            return ox, oy

        if self._phase == 3:
            p = _ease_out_quad(min(1.0, (t - self._phase_start) / config.SLEEP_WAKE_DURATION_MS))
            return 0.0, (1.0 - p) * config.SLEEP_DROP_AMOUNT

        return 0.0, 0.0

    def get_radius_scale(self) -> float:
        if self._original_radius is None or state.current_radius == 0:
            return 1.0

        orig = self._original_radius
        curr = state.current_radius

        if self._phase == 1:
            p = _ease_out_quad(min(1.0, (pygame.time.get_ticks() - self._phase_start) / config.SLEEP_DROP_DURATION_MS))
            return _lerp(orig, orig * 0.9, p) / curr

        if self._phase == 2:
            base = orig * 0.9
            if self._twitch_active:
                elapsed = pygame.time.get_ticks() - self._twitch_start
                angle = (elapsed / 1000.0) * config.SLEEP_TWITCH_FREQUENCY_HZ * 2 * math.pi
                pulse = math.sin(angle) * config.SLEEP_TWITCH_SIZE_CHANGE
                return (base * (1.0 + pulse)) / curr
            return base / curr

        if self._phase == 3:
            t = pygame.time.get_ticks()
            p = min(1.0, (t - self._phase_start) / config.SLEEP_WAKE_DURATION_MS)
            base = orig * 0.9
            return _lerp(base, orig, p) / curr

        return 1.0

    def clear(self) -> None:
        self._phase = 0
        self._phase_start = 0
        self._original_radius = None
        self._twitch_active = False
        self._twitch_start = 0
        self._next_twitch = 0


# ---------------------------------------------------------------------------

class _ThreePhaseEmoteAnimation(BaseAnimation):
    """
    Shared skeleton for Sad / Happy / Angry.

    All three follow the same pattern:
      Phase 1: Move to displaced position + change size
      Phase 2: Hold position + shake/orbit + maintain size
      Phase 3: Return to origin + restore size
    Subclasses override the configuration hooks.
    """

    def __init__(self):
        self._phase: int = 0
        self._phase_start: int = 0
        self._shake_start: int = 0
        self._original_radius: float | None = None
        self._target_radius: float | None = None

    # -- Configuration hooks (override in subclasses) --

    def _size_scale(self) -> float:
        """How much to scale the radius at peak. >1 = grow, <1 = shrink."""
        return 1.0

    def _phase1_duration(self) -> int: ...
    def _phase2_duration(self) -> int: ...
    def _phase3_duration(self) -> int: ...

    def _phase1_offset(self, progress: float) -> Offset:
        """Offset at the end of phase 1 (displacement)."""
        return 0.0, 0.0

    def _phase2_offset(self, t: int) -> Offset:
        """Offset during phase 2 (hold + shake/orbit)."""
        return 0.0, 0.0

    # -- BaseAnimation contract --

    def is_active(self) -> bool:
        return self._phase != 0

    def start(self) -> None:
        if self._phase != 0:
            return
        if self._is_resting():
            self._warn_resting()
            return
        t = pygame.time.get_ticks()
        self._phase = 1
        self._phase_start = t
        self._original_radius = state.pet_radius
        self._target_radius = state.pet_radius * self._size_scale()
        print(f"[animation] {self.name}: started.")

    def update(self, t: int) -> None:
        elapsed = t - self._phase_start

        if self._phase == 1:
            if elapsed >= self._phase1_duration():
                self._phase = 2
                self._phase_start = t
                self._shake_start = t

        elif self._phase == 2:
            if t - self._shake_start >= self._phase2_duration():
                self._phase = 3
                self._phase_start = t

        elif self._phase == 3:
            if elapsed >= self._phase3_duration():
                self.clear()

    def get_offset(self, t: int) -> Offset:
        if self._phase == 1:
            p = min(1.0, (t - self._phase_start) / self._phase1_duration())
            return self._phase1_offset(p)

        if self._phase == 2:
            return self._phase2_offset(t)

        if self._phase == 3:
            p = min(1.0, (t - self._phase_start) / self._phase3_duration())
            px1, py1 = self._phase1_offset(1.0)
            return _lerp(px1, 0.0, p), _lerp(py1, 0.0, p)

        return 0.0, 0.0

    def get_radius_scale(self) -> float:
        if self._original_radius is None or self._target_radius is None or state.current_radius == 0:
            return 1.0
        orig, target, curr = self._original_radius, self._target_radius, state.current_radius

        if self._phase == 1:
            p = min(1.0, (pygame.time.get_ticks() - self._phase_start) / self._phase1_duration())
            return _lerp(orig, target, p) / curr

        if self._phase == 2:
            return target / curr

        if self._phase == 3:
            p = min(1.0, (pygame.time.get_ticks() - self._phase_start) / self._phase3_duration())
            return _lerp(target, orig, p) / curr

        return 1.0

    def clear(self) -> None:
        self._phase = 0
        self._phase_start = 0
        self._shake_start = 0
        self._original_radius = None
        self._target_radius = None


# -----------

class SadAnimation(_ThreePhaseEmoteAnimation):
    name = "sad"

    def _size_scale(self)      -> float: return 1.0 + config.SAD_SIZE_CHANGE_PERCENTAGE
    def _phase1_duration(self) -> int:   return config.SAD_DROP_DURATION_MS
    def _phase2_duration(self) -> int:   return config.SAD_SHAKE_DURATION_MS
    def _phase3_duration(self) -> int:   return config.SAD_RISE_DURATION_MS

    def _phase1_offset(self, p: float) -> Offset:
        return 0.0, p * config.SAD_DROP_AMOUNT

    def _phase2_offset(self, t: int) -> Offset:
        elapsed = t - self._shake_start
        angle = elapsed / 1000.0 * config.SAD_SHAKE_FREQUENCY_HZ * 2 * math.pi
        ox = config.SAD_SHAKE_INTENSITY * math.sin(angle)
        oy = config.SAD_DROP_AMOUNT + config.SAD_SHAKE_INTENSITY * math.sin(angle + math.pi / 2)
        return ox, oy


class HappyAnimation(_ThreePhaseEmoteAnimation):
    name = "happy"

    def _size_scale(self)      -> float: return 1.0 + config.HAPPY_SIZE_CHANGE_PERCENTAGE
    def _phase1_duration(self) -> int:   return config.HAPPY_DIP_DURATION_MS
    def _phase2_duration(self) -> int:   return config.HAPPY_SHAKE_DURATION_MS
    def _phase3_duration(self) -> int:   return config.HAPPY_RISE_DURATION_MS

    def _phase1_offset(self, p: float) -> Offset:
        return 0.0, p * config.HAPPY_DIP_AMOUNT

    def _phase2_offset(self, t: int) -> Offset:
        elapsed_phase = t - self._phase_start
        phase_dur = config.HAPPY_SHAKE_DURATION_MS

        # Orbit with fade-in / fade-out
        fi = _ease_out_quad(min(1.0, elapsed_phase / config.HAPPY_ORBIT_FADE_IN_DURATION_MS))
        time_left = max(0.0, phase_dur - elapsed_phase)
        fo = _ease_out_quad(min(1.0, max(0.0,
            (config.HAPPY_ORBIT_FADE_OUT_DURATION_MS - time_left)
            / config.HAPPY_ORBIT_FADE_OUT_DURATION_MS
        )))
        radius = config.HAPPY_ORBIT_RADIUS * fi * (1.0 - fo)
        orbit_angle = elapsed_phase / 1000.0 * config.HAPPY_ORBIT_FREQUENCY_HZ * 2 * math.pi + config.HAPPY_ORBIT_START_ANGLE

        # Jiggle
        elapsed_jiggle = t - self._shake_start
        jx = config.HAPPY_SHAKE_INTENSITY * math.sin(elapsed_jiggle / 1000.0 * config.HAPPY_SHAKE_FREQUENCY_HZ * 2 * math.pi)
        jy = config.HAPPY_SHAKE_INTENSITY * math.sin(elapsed_jiggle / 1000.0 * config.HAPPY_SHAKE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2)

        ox = radius * math.cos(orbit_angle) + jx
        oy = config.HAPPY_DIP_AMOUNT + radius * math.sin(orbit_angle) + jy
        return ox, oy


class AngryAnimation(_ThreePhaseEmoteAnimation):
    name = "angry"

    def _size_scale(self)      -> float: return 1.0 + config.ANGRY_SIZE_INCREASE_PERCENTAGE
    def _phase1_duration(self) -> int:   return config.ANGRY_TENSE_DURATION_MS
    def _phase2_duration(self) -> int:   return config.ANGRY_VIBRATE_DURATION_MS
    def _phase3_duration(self) -> int:   return config.ANGRY_SETTLE_DURATION_MS

    def _phase1_offset(self, p: float) -> Offset:
        return 0.0, p * config.ANGRY_TENSE_AMOUNT

    def _phase2_offset(self, t: int) -> Offset:
        elapsed = t - self._shake_start
        angle = elapsed / 1000.0 * config.ANGRY_VIBRATE_FREQUENCY_HZ * 2 * math.pi
        ox = config.ANGRY_VIBRATE_INTENSITY * math.sin(angle)
        oy = config.ANGRY_TENSE_AMOUNT + config.ANGRY_VIBRATE_INTENSITY * math.sin(angle + math.pi / 2)
        return ox, oy


# -----------

class ExcitedAnimation(BaseAnimation):
    """
    Three-phase: bounce up → orbit + jiggle → settle back.
    Doesn't change pet size.
    """

    name = "excited"

    def __init__(self):
        self._phase: int = 0
        self._phase_start: int = 0
        self._shake_start: int = 0

    def is_active(self) -> bool:
        return self._phase != 0

    def start(self) -> None:
        if self._phase != 0:
            return
        if self._is_resting():
            self._warn_resting()
            return
        t = pygame.time.get_ticks()
        self._phase = 1
        self._phase_start = t
        print("[animation] excited: started.")

    def update(self, t: int) -> None:
        elapsed = t - self._phase_start

        if self._phase == 1:
            if elapsed >= config.EXCITED_BOUNCE_DURATION_MS:
                self._phase = 2
                self._phase_start = t
                self._shake_start = t

        elif self._phase == 2:
            if t - self._shake_start >= config.EXCITED_JIGGLE_DURATION_MS:
                self._phase = 3
                self._phase_start = t

        elif self._phase == 3:
            if elapsed >= config.EXCITED_SETTLE_DURATION_MS:
                self.clear()

    def get_offset(self, t: int) -> Offset:
        if self._phase == 1:
            p = _ease_out_quad(min(1.0, (t - self._phase_start) / config.EXCITED_BOUNCE_DURATION_MS))
            return 0.0, -config.EXCITED_BOUNCE_AMOUNT * p

        if self._phase == 2:
            return self._phase2_offset(t)

        if self._phase == 3:
            p = _ease_out_quad(min(1.0, (t - self._phase_start) / config.EXCITED_SETTLE_DURATION_MS))
            end_ox, end_oy = self._phase2_offset_at_end()
            return _lerp(end_ox, 0.0, p), _lerp(end_oy, 0.0, p)

        return 0.0, 0.0

    def _phase2_offset(self, t: int) -> Offset:
        elapsed = t - self._phase_start
        fi = _ease_out_quad(min(1.0, elapsed / config.EXCITED_ORBIT_FADE_IN_DURATION_MS))
        radius = config.EXCITED_ORBIT_RADIUS * fi
        orbit_angle = elapsed / 1000.0 * config.EXCITED_ORBIT_FREQUENCY_HZ * 2 * math.pi + config.EXCITED_ORBIT_START_ANGLE

        ji = _ease_out_quad(min(1.0, elapsed / config.EXCITED_JIGGLE_FADE_IN_DURATION_MS))
        intensity = config.EXCITED_JIGGLE_INTENSITY * ji
        elapsed_shake = t - self._shake_start
        jx = intensity * math.sin(elapsed_shake / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi)
        jy = intensity * math.sin(elapsed_shake / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2)

        ox = radius * math.cos(orbit_angle) + jx
        oy = -config.EXCITED_BOUNCE_AMOUNT + radius * math.sin(orbit_angle) + jy
        return ox, oy

    def _phase2_offset_at_end(self) -> Offset:
        """Snapshot the offset at the exact moment phase 2 ended (= phase 3 start)."""
        t_end = self._phase_start  # phase_start was just reset when entering phase 3
        t_fake = t_end  # reconstruct using phase duration
        dur = config.EXCITED_JIGGLE_DURATION_MS

        fi = _ease_out_quad(min(1.0, dur / config.EXCITED_ORBIT_FADE_IN_DURATION_MS))
        radius = config.EXCITED_ORBIT_RADIUS * fi
        orbit_angle = dur / 1000.0 * config.EXCITED_ORBIT_FREQUENCY_HZ * 2 * math.pi + config.EXCITED_ORBIT_START_ANGLE

        ji = _ease_out_quad(min(1.0, dur / config.EXCITED_JIGGLE_FADE_IN_DURATION_MS))
        intensity = config.EXCITED_JIGGLE_INTENSITY * ji
        jx = intensity * math.sin(dur / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi)
        jy = intensity * math.sin(dur / 1000.0 * config.EXCITED_JIGGLE_FREQUENCY_HZ * 2 * math.pi + math.pi / 2)

        return radius * math.cos(orbit_angle) + jx, -config.EXCITED_BOUNCE_AMOUNT + radius * math.sin(orbit_angle) + jy

    def clear(self) -> None:
        self._phase = 0
        self._phase_start = 0
        self._shake_start = 0


# -----------

class ThinkingAnimation(BaseAnimation):
    """U-shape path movement across configurable cycle count."""

    name = "thinking"

    _SEGMENT_PATH = [
        ((0, 0), (0, config.THINKING_POINT_P1_Y)),
        ((0, config.THINKING_POINT_P1_Y), (config.THINKING_POINT_P2_X, config.THINKING_POINT_P2_Y)),
        ((config.THINKING_POINT_P2_X, config.THINKING_POINT_P2_Y), (config.THINKING_POINT_P3_X, config.THINKING_POINT_P3_Y)),
        ((config.THINKING_POINT_P3_X, config.THINKING_POINT_P3_Y), (0, config.THINKING_POINT_P1_Y)),
        ((0, config.THINKING_POINT_P1_Y), (0, 0)),
        # Reverse pass
        ((0, 0), (0, config.THINKING_POINT_P1_Y)),
        ((0, config.THINKING_POINT_P1_Y), (config.THINKING_POINT_P3_X, config.THINKING_POINT_P3_Y)),
        ((config.THINKING_POINT_P3_X, config.THINKING_POINT_P3_Y), (config.THINKING_POINT_P2_X, config.THINKING_POINT_P2_Y)),
        ((config.THINKING_POINT_P2_X, config.THINKING_POINT_P2_Y), (0, config.THINKING_POINT_P1_Y)),
        ((0, config.THINKING_POINT_P1_Y), (0, 0)),
    ]

    def __init__(self):
        self._active: bool = False
        self._segment_idx: int = 0
        self._segment_start: int = 0
        self._total_segments: int = 0

    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        if self._is_resting():
            self._warn_resting()
            return
        t = pygame.time.get_ticks()
        self._active = True
        self._segment_idx = 0
        self._segment_start = t
        self._total_segments = config.THINKING_U_CYCLES * len(self._SEGMENT_PATH)
        print("[animation] thinking: started.")

    def update(self, t: int) -> None:
        if not self._active:
            return
        elapsed = t - self._segment_start
        if elapsed >= config.THINKING_SEGMENT_DURATION_MS:
            self._segment_idx += 1
            self._segment_start = t
            if self._segment_idx >= self._total_segments:
                self.clear()
                print("[animation] thinking: ended.")

    def get_offset(self, t: int) -> Offset:
        if not self._active:
            return 0.0, 0.0
        base_idx = self._segment_idx % len(self._SEGMENT_PATH)
        start, end = self._SEGMENT_PATH[base_idx]
        p = min(1.0, max(0.0, (t - self._segment_start) / config.THINKING_SEGMENT_DURATION_MS))
        return _lerp(start[0], end[0], p), _lerp(start[1], end[1], p)

    def clear(self) -> None:
        self._active = False
        self._segment_idx = 0
        self._segment_start = 0
        self._total_segments = 0


# -----------

class CuriousAnimation(BaseAnimation):
    """Horizontal sway + size pulse for a fixed duration."""

    name = "curious"

    def __init__(self):
        self._active: bool = False
        self._start: int = 0
        self._original_radius: float | None = None

    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        if self._is_resting():
            self._warn_resting()
            return
        t = pygame.time.get_ticks()
        self._active = True
        self._start = t
        self._original_radius = state.pet_radius
        print("[animation] curious: started.")

    def update(self, t: int) -> None:
        if self._active and t - self._start >= config.CURIOUS_DURATION_MS:
            self.clear()

    def get_offset(self, t: int) -> Offset:
        if not self._active:
            return 0.0, 0.0
        elapsed = (t - self._start) / 1000.0
        ox = config.CURIOUS_SWAY_AMPLITUDE_X * math.sin(elapsed * config.CURIOUS_SWAY_FREQUENCY_HZ * 2 * math.pi)
        oy = 0.0
        if config.CURIOUS_SWAY_AMPLITUDE_Y > 0:
            oy = config.CURIOUS_SWAY_AMPLITUDE_Y * math.sin(
                elapsed * config.CURIOUS_SWAY_FREQUENCY_HZ * 2 * math.pi + config.CURIOUS_SWAY_PHASE_SHIFT_Y
            )
        return ox, oy

    def get_radius_scale(self) -> float:
        if not self._active or self._original_radius is None or state.current_radius == 0:
            return 1.0
        elapsed = (pygame.time.get_ticks() - self._start) / 1000.0
        pulse = self._original_radius * config.CURIOUS_SIZE_CHANGE_PERCENTAGE * math.sin(
            elapsed * config.CURIOUS_SIZE_PULSE_FREQUENCY_HZ * 2 * math.pi
        )
        return (self._original_radius + pulse) / state.current_radius

    def clear(self) -> None:
        self._active = False
        self._start = 0
        self._original_radius = None


# -----------

class ConfusedAnimation(BaseAnimation):
    """
    Corner-to-centre wobble across 4 corners (8 half-phases) with size pulse.
    """

    name = "confused"

    _CORNERS = [
        (-1, -1), (1, -1), (-1, 1), (1, 1)
    ]

    def __init__(self):
        self._phase: int = 0
        self._phase_start: int = 0
        self._anim_start: int = 0
        self._original_radius: float | None = None

    def is_active(self) -> bool:
        return self._phase != 0

    def start(self) -> None:
        if self._phase != 0:
            return
        if self._is_resting():
            self._warn_resting()
            return
        t = pygame.time.get_ticks()
        self._phase = 1
        self._phase_start = t
        self._anim_start = t
        self._original_radius = state.pet_radius
        print("[animation] confused: started.")

    def update(self, t: int) -> None:
        if self._phase == 0:
            return
        if t - self._phase_start >= config.CONFUSED_PHASE_DURATION_MS:
            self._phase += 1
            self._phase_start = t
            if self._phase > 8:
                self.clear()

    def get_offset(self, t: int) -> Offset:
        if self._phase == 0:
            return 0.0, 0.0

        p = min(1.0, (t - self._phase_start) / config.CONFUSED_PHASE_DURATION_MS)
        corner_idx = (self._phase - 1) // 2
        cx = self._CORNERS[corner_idx][0] * config.CONFUSED_X_OFFSET_AMOUNT
        cy = self._CORNERS[corner_idx][1] * config.CONFUSED_Y_OFFSET_AMOUNT

        if self._phase % 2 != 0:          # Odd: centre → corner
            return _lerp(0.0, cx, p), _lerp(0.0, cy, p)
        else:                              # Even: corner → centre
            return _lerp(cx, 0.0, p), _lerp(cy, 0.0, p)

    def get_radius_scale(self) -> float:
        if self._original_radius is None or state.current_radius == 0:
            return 1.0
        elapsed = (pygame.time.get_ticks() - self._anim_start) / 1000.0
        amplitude = self._original_radius * config.CONFUSED_SIZE_PULSE_AMPLITUDE_PERCENTAGE
        radius = max(1.0, self._original_radius + amplitude * math.sin(
            elapsed * config.CONFUSED_SIZE_PULSE_FREQUENCY_HZ * 2 * math.pi
        ))
        return radius / state.current_radius

    def clear(self) -> None:
        self._phase = 0
        self._phase_start = 0
        self._anim_start = 0
        self._original_radius = None


# -----------

class ShakeAnimation(BaseAnimation):
    """General-purpose brief shake (lowest priority)."""

    name = "shake"

    def __init__(self):
        self._active: bool = False
        self._start: int = 0

    def is_active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._start = pygame.time.get_ticks()
        print("[animation] shake: started.")

    def update(self, t: int) -> None:
        if self._active and t - self._start >= config.SHAKE_DURATION_MS:
            self.clear()

    def get_offset(self, t: int) -> Offset:
        if not self._active:
            return 0.0, 0.0
        elapsed = t - self._start
        angle = elapsed / 1000.0 * config.SHAKE_FREQUENCY_HZ * 2 * math.pi
        return (
            config.SHAKE_INTENSITY * math.sin(angle),
            config.SHAKE_INTENSITY * math.sin(angle + math.pi / 2),
        )

    def clear(self) -> None:
        self._active = False
        self._start = 0


# ---------------------------------------------------------------------------
# Animation controller
# ---------------------------------------------------------------------------

class AnimationController:
    """
    Manages a priority-ordered list of animations.

    Priority is determined by list order — index 0 is highest priority.
    When an animation starts it clears all lower-priority animations so
    they don't fight for the same offset/radius output.

    The base movement is the implicit fallback when nothing is active.
    """

    def __init__(self, animations: list[BaseAnimation]) -> None:
        # Stored highest-priority-first.
        self._animations = animations

    # ------------------------------------------------------------------
    # Priority helpers
    # ------------------------------------------------------------------

    def _index_of(self, anim: BaseAnimation) -> int:
        return self._animations.index(anim)

    def _any_higher_active(self, anim: BaseAnimation) -> bool:
        my_idx = self._index_of(anim)
        return any(a.is_active() for a in self._animations[:my_idx])

    def _clear_lower(self, anim: BaseAnimation) -> None:
        my_idx = self._index_of(anim)
        for a in self._animations[my_idx + 1:]:
            if a.is_active():
                a.clear()

    # ------------------------------------------------------------------
    # Public start helpers (called by module-level starter functions)
    # ------------------------------------------------------------------

    def try_start(self, anim: BaseAnimation) -> bool:
        """
        Start *anim* if no higher-priority animation is currently active.
        Clears lower-priority animations on success.
        Returns True if the animation was started.
        """
        if self._any_higher_active(anim):
            return False
        if anim.is_active():
            return False
        anim.start()
        if anim.is_active():           # start() may refuse (e.g. resting guard)
            self._clear_lower(anim)
            return True
        return False

    # ------------------------------------------------------------------
    # Per-frame update (call once per frame before calculate_circle_offset)
    # ------------------------------------------------------------------

    def update(self, current_time_ms: int) -> bool:
        """
        Advance all active animations.
        Returns True if any specific animation is running (not base movement).
        """
        for anim in self._animations:
            if anim.is_active():
                anim.update(current_time_ms)

        return any(a.is_active() for a in self._animations)

    # ------------------------------------------------------------------
    # Per-frame offset + radius calculation
    # ------------------------------------------------------------------

    def calculate_offset_and_radius(self, current_time_ms: int) -> Offset:
        """
        Ask the highest-priority active animation for its offset and radius.
        Falls back to base bobbing/swaying when nothing is active.
        Also writes state.pet_radius.
        """
        for anim in self._animations:
            if anim.is_active():
                offset = anim.get_offset(current_time_ms)
                state.pet_radius = anim.get_radius_scale() * state.current_radius
                return offset

        # Base movement
        state.pet_radius = state.current_radius
        return self._base_offset(current_time_ms)

    @staticmethod
    def _base_offset(t: int) -> Offset:
        s = t / 1000.0
        oy = config.BASE_BOB_AMPLITUDE * math.sin(s * config.BASE_BOB_FREQUENCY * 2 * math.pi)
        ox = config.BASE_SWAY_AMPLITUDE * math.sin(s * config.BASE_SWAY_FREQUENCY * 2 * math.pi + config.BASE_PHASE_SHIFT)
        return ox, oy

    # ------------------------------------------------------------------
    # Clear all (used by start_neutral_animation)
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        for anim in self._animations:
            anim.clear()
        state.pet_radius = state.current_radius


# ---------------------------------------------------------------------------
# Singleton instances and controller
# ---------------------------------------------------------------------------

_sleep    = SleepAnimation()
_sad      = SadAnimation()
_happy    = HappyAnimation()
_angry    = AngryAnimation()
_excited  = ExcitedAnimation()
_thinking = ThinkingAnimation()
_curious  = CuriousAnimation()
_confused = ConfusedAnimation()
_shake    = ShakeAnimation()

# Priority order: index 0 = highest priority.
_controller = AnimationController([
    _sleep,
    _sad,
    _confused,
    _angry,
    _excited,
    _thinking,
    _curious,
    _happy,
    _shake,
])


# ---------------------------------------------------------------------------
# Public API  (identical signatures to the original module)
# ---------------------------------------------------------------------------

def update_animation_state(current_time_ms: int) -> bool:
    """Advance all animations. Returns True if any specific animation is active."""
    return _controller.update(current_time_ms)


def calculate_circle_offset(current_time_ms: int) -> Offset:
    """Return (offset_x, offset_y) for the pet circle this frame."""
    return _controller.calculate_offset_and_radius(current_time_ms)


# ---------------------------------------------------------------------------
# Starter functions  (identical signatures to the original module)
# ---------------------------------------------------------------------------

def start_sleep_animation() -> None:
    _sleep.start()
    _controller._clear_lower(_sleep)

def wake_up_pet() -> None:
    _sleep.wake_up()

def start_circle_shake() -> None:
    t = pygame.time.get_ticks()
    if t < state.autonomous_action_paused_until_ms:
        gui.gui_text_utils.add_message_to_history(
            "System: Cannot manually trigger shake while bot is resting.", "system"
        )
        return
    _controller.try_start(_shake)

def start_sad_animation()     -> None: _controller.try_start(_sad)
def start_happy_animation()   -> None: _controller.try_start(_happy)
def start_angry_animation()   -> None: _controller.try_start(_angry)
def start_excited_animation() -> None: _controller.try_start(_excited)
def start_thinking_animation()-> None: _controller.try_start(_thinking)
def start_curious_animation() -> None: _controller.try_start(_curious)
def start_confused_animation()-> None: _controller.try_start(_confused)

def start_neutral_animation() -> None:
    t = pygame.time.get_ticks()
    if t < state.autonomous_action_paused_until_ms:
        gui.gui_text_utils.add_message_to_history(
            "System: Cannot manually trigger neutral while bot is resting.", "system"
        )
        return
    _controller.clear_all()
    print("[animation] Returned to neutral state.")
    gui.gui_text_utils.add_message_to_history("System: Returned to neutral state.", "system")