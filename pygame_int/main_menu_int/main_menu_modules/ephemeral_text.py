# ephemeral_text.py
#
# Two classes:
#
#   EphemeralTextManager  — owns the live particle pool, draws and updates it.
#   EphemeralTextEmitter  — sits on top of the manager, automates spawn timing.
#
# Typical usage:
#
#   manager = EphemeralTextManager(font)
#
#   emitter = EphemeralTextEmitter(
#       manager   = manager,
#       messages  = ["hello", "∿∿", "yes"],
#       origin    = (400, 0),
#       direction = "falling",
#       rate      = 1.5,          # particles per second
#       spread    = 200,          # spawn radius around origin (px)
#       angle_variance = 20,      # ± degrees off the base direction
#       speed     = (30, 60),     # px/s range
#       lifetime  = (1800, 3200), # ms range
#       color     = (180, 180, 200),
#   )
#
#   emitter.start()          # continuous emission
#   emitter.burst(6)         # one-shot burst of 6, ignores rate
#   emitter.stop()           # stop emitting (live particles finish naturally)
#
#   # each frame:
#   emitter.update(current_ms)
#   manager.update(current_ms)
#   manager.draw(screen)

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import pygame


# ---------------------------------------------------------------------------
# Internal: single particle
# ---------------------------------------------------------------------------

class _EphemeralMessage:
    """One floating text particle."""

    def __init__(
        self,
        text:        str,
        font:        pygame.font.Font,
        x:           float,
        y:           float,
        color:       tuple,
        vel_x:       float,   # px/s
        vel_y:       float,   # px/s
        lifetime_ms: int,
    ):
        self.surface    = font.render(text, True, color)
        # centre the text on the spawn point
        self.x          = x - self.surface.get_width() / 2
        self.y          = y - self.surface.get_height() / 2
        self.vel_x      = vel_x
        self.vel_y      = vel_y
        self.lifetime   = lifetime_ms
        self.born_ms    = pygame.time.get_ticks()
        self.alive      = True
        self._last_ms   = self.born_ms

    def update(self, current_ms: int) -> None:
        elapsed = current_ms - self.born_ms
        if elapsed >= self.lifetime:
            self.alive = False
            return

        dt_s = (current_ms - self._last_ms) / 1000.0
        self._last_ms = current_ms

        self.x += self.vel_x * dt_s
        self.y += self.vel_y * dt_s

        # Fade: solid for first 40%, then fade out over remaining 60%
        progress = elapsed / self.lifetime
        if progress < 0.4:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (progress - 0.4) / 0.6))
        self.surface.set_alpha(max(0, alpha))

    def draw(self, screen: pygame.Surface) -> None:
        if self.alive:
            screen.blit(self.surface, (int(self.x), int(self.y)))


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class EphemeralTextManager:
    """
    Owns the live particle pool.  Draw and update this every frame.

    You can spawn particles directly via .spawn(), or hand an
    EphemeralTextEmitter a reference to this manager and let it
    handle spawn timing automatically.
    """

    def __init__(self, font: pygame.font.Font):
        self._font:     pygame.font.Font          = font
        self._messages: List[_EphemeralMessage]   = []

    def spawn(
        self,
        text:        str,
        x:           float,
        y:           float,
        vel_x:       float = 0.0,
        vel_y:       float = 40.0,
        color:       tuple = (200, 200, 200),
        lifetime_ms: int   = 2200,
        font:        Optional[pygame.font.Font] = None,
    ) -> None:
        """Spawn a single particle at (x, y) with the given velocity."""
        f   = font or self._font
        msg = _EphemeralMessage(text, f, x, y, color, vel_x, vel_y, lifetime_ms)
        self._messages.append(msg)

    def update(self, current_time_ms: int) -> None:
        for msg in self._messages:
            msg.update(current_time_ms)
        self._messages = [m for m in self._messages if m.alive]

    def draw(self, screen: pygame.Surface) -> None:
        for msg in self._messages:
            msg.draw(screen)

    def clear(self) -> None:
        self._messages.clear()

    @property
    def active_count(self) -> int:
        return len(self._messages)


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------

# Base direction vectors (normalised)
_DIRECTION_VECTORS = {
    "falling": (0.0,  1.0),
    "rising":  (0.0, -1.0),
    "left":    (-1.0, 0.0),
    "right":   (1.0,  0.0),
}


class EphemeralTextEmitter:
    """
    Automates particle spawning on behalf of an EphemeralTextManager.

    Parameters
    ----------
    manager        : EphemeralTextManager to spawn into
    messages       : pool of strings; one is chosen at random per spawn
    origin         : (x, y) centre point of the emitter
    direction      : base travel direction — "falling", "rising", "left", "right"
    rate           : particles per second for continuous emission
    spread         : radius (px) within which spawn points are scattered
                     randomly around the origin.  0 = all from exact origin.
    angle_variance : ± degrees of random rotation applied to the base
                     direction vector per particle.  0 = perfectly straight.
                     30 = a ±30° cone, giving a natural fan effect.
    speed          : (min, max) px/s — each particle gets a random speed
                     in this range along its (possibly rotated) direction.
    lifetime       : (min_ms, max_ms) — each particle lives a random
                     duration in this range.
    color          : RGB tuple applied to all spawned particles
    font           : override the manager's default font (optional)
    """

    def __init__(
        self,
        manager:        EphemeralTextManager,
        messages:       List[str],
        origin:         Tuple[float, float],
        direction:      str   = "falling",
        rate:           float = 2.0,
        spread:         float = 0.0,
        angle_variance: float = 0.0,
        speed:          Tuple[float, float] = (30.0, 60.0),
        lifetime:       Tuple[int, int]     = (1800, 3000),
        color:          tuple = (200, 200, 200),
        font:           Optional[pygame.font.Font] = None,
    ):
        self._manager        = manager
        self._messages       = messages
        self._origin         = origin
        self._direction      = direction
        self._rate           = max(0.001, rate)
        self._spread         = spread
        self._angle_variance = angle_variance
        self._speed_range    = speed
        self._lifetime_range = lifetime
        self._color          = color
        self._font           = font

        self._active         = False
        self._last_spawn_ms  = 0
        self._interval_ms    = int(1000.0 / self._rate)

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin continuous emission."""
        self._active        = True
        self._last_spawn_ms = pygame.time.get_ticks()

    def stop(self) -> None:
        """Stop emitting. Live particles finish naturally."""
        self._active = False

    def burst(self, count: int) -> None:
        """
        Spawn `count` particles immediately, ignoring rate and active state.
        Does not affect continuous emission.
        """
        for _ in range(count):
            self._spawn_one()

    @property
    def is_active(self) -> bool:
        return self._active

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(self, current_ms: int) -> None:
        """
        Call once per frame.  Spawns particles as needed for continuous
        emission.  Does NOT update or draw the manager — call those
        separately.
        """
        if not self._active:
            return

        # Spawn as many particles as the elapsed time demands.
        # Using a while loop handles cases where the frame was slow
        # and we owe more than one particle.
        while current_ms - self._last_spawn_ms >= self._interval_ms:
            self._spawn_one()
            self._last_spawn_ms += self._interval_ms

    # ------------------------------------------------------------------
    # Spawn one particle
    # ------------------------------------------------------------------

    def _spawn_one(self) -> None:
        if not self._messages:
            return

        text = random.choice(self._messages)

        # --- Spawn position (random scatter within spread radius) ---
        if self._spread > 0:
            angle_rad = random.uniform(0, math.tau)
            radius    = random.uniform(0, self._spread)
            sx = self._origin[0] + math.cos(angle_rad) * radius
            sy = self._origin[1] + math.sin(angle_rad) * radius
        else:
            sx, sy = self._origin

        # --- Velocity (base direction + angle variance + random speed) ---
        base = _DIRECTION_VECTORS.get(self._direction, (0.0, 1.0))
        base_angle = math.atan2(base[1], base[0])

        if self._angle_variance > 0:
            deviation = math.radians(random.uniform(-self._angle_variance, self._angle_variance))
        else:
            deviation = 0.0

        final_angle = base_angle + deviation
        speed       = random.uniform(self._speed_range[0], self._speed_range[1])
        vel_x       = math.cos(final_angle) * speed
        vel_y       = math.sin(final_angle) * speed

        # --- Lifetime ---
        lifetime = random.randint(self._lifetime_range[0], self._lifetime_range[1])

        self._manager.spawn(
            text        = text,
            x           = sx,
            y           = sy,
            vel_x       = vel_x,
            vel_y       = vel_y,
            color       = self._color,
            lifetime_ms = lifetime,
            font        = self._font,
        )

    # ------------------------------------------------------------------
    # Convenience: update origin or color at runtime
    # ------------------------------------------------------------------

    def set_origin(self, x: float, y: float) -> None:
        self._origin = (x, y)

    def set_color(self, color: tuple) -> None:
        self._color = color