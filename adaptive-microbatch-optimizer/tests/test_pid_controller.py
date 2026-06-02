"""Tests for the PID controller."""

from __future__ import annotations

import pytest

from microbatch.pid import PIDConfig, PIDController


def test_positive_error_shrinks_window() -> None:
    pid = PIDController()
    w1 = pid.apply(1.0, error=0.8)
    assert w1 < 1.0


def test_negative_error_grows_window() -> None:
    pid = PIDController()
    w1 = pid.apply(0.5, error=-0.8)
    assert w1 > 0.5


def test_output_clamped_to_min() -> None:
    cfg = PIDConfig(kp=10.0, ki=0.0, kd=0.0)
    pid = PIDController(cfg)
    w = 0.1
    for _ in range(50):
        w = pid.apply(w, error=1.0)
    assert w == pytest.approx(cfg.min_output, abs=1e-9)


def test_output_clamped_to_max() -> None:
    cfg = PIDConfig(kp=10.0, ki=0.0, kd=0.0)
    pid = PIDController(cfg)
    w = 4.0
    for _ in range(50):
        w = pid.apply(w, error=-1.0)
    assert w == pytest.approx(cfg.max_output, abs=1e-9)


def test_zero_error_is_stable() -> None:
    pid = PIDController()
    w = 1.0
    w_new = w
    for _ in range(20):
        w_new = pid.apply(w, error=0.0)
    assert abs(w_new - w) < 0.05


def test_anti_windup_limits_integral() -> None:
    cfg = PIDConfig(kp=0.0, ki=1.0, kd=0.0, integral_clamp=0.5)
    pid = PIDController(cfg)
    w = 2.0
    for _ in range(200):
        pid.apply(w, error=1.0)
    assert abs(pid.integral) <= cfg.integral_clamp + 1e-6


def test_reset_clears_state() -> None:
    pid = PIDController()
    pid.apply(1.0, error=0.9)
    pid.reset()
    assert pid.integral == 0.0
