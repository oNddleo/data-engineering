"""PID controller driving adaptive window-size decisions.

The controlled variable is *window_size* (seconds).
Positive error means latency/pressure is too high → shrink the window.
Negative error means headroom available → grow the window.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PIDConfig:
    kp: float = 0.4
    ki: float = 0.05
    kd: float = 0.15
    min_output: float = 0.05  # 50 ms floor
    max_output: float = 5.0  # 5 s ceiling
    integral_clamp: float = 2.0


@dataclass
class PIDState:
    """Mutable controller state (separated from config for clarity)."""

    integral: float = field(default=0.0)
    prev_error: float = field(default=0.0)
    last_output: float = field(default=0.5)


class PIDController:
    """Standard discrete-time PID with anti-windup and output clamping.

    dt is passed explicitly so the controller is deterministic and
    testable without wall-clock time.
    """

    def __init__(self, config: PIDConfig | None = None) -> None:
        self.cfg = config or PIDConfig()
        self._s = PIDState()

    # ── public ────────────────────────────────────────────────────────────────

    def step(self, error: float, dt: float = 0.1) -> float:
        """Return the signed delta to apply to the current window size."""
        dt = max(dt, 1e-9)
        self._s.integral += error * dt
        self._s.integral = max(
            -self.cfg.integral_clamp,
            min(self.cfg.integral_clamp, self._s.integral),
        )
        derivative = (error - self._s.prev_error) / dt
        raw = self.cfg.kp * error + self.cfg.ki * self._s.integral + self.cfg.kd * derivative
        self._s.prev_error = error
        return -raw  # positive error → negative delta (shrink)

    def apply(self, current_window: float, error: float, dt: float = 0.1) -> float:
        """Return the new clamped window size."""
        delta = self.step(error, dt)
        clamped = max(self.cfg.min_output, min(self.cfg.max_output, current_window + delta))
        self._s.last_output = clamped
        return clamped

    def reset(self) -> None:
        self._s = PIDState()

    @property
    def integral(self) -> float:
        return self._s.integral

    @property
    def last_output(self) -> float:
        return self._s.last_output
