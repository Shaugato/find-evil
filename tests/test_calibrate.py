"""Calibrator registry smoke tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from findevil.swarm.calibrate import (
    CalibratorRegistry,
    fit_isotonic,
    fit_platt,
)


def test_platt_fit_and_predict_monotone():
    rng = np.random.default_rng(0)
    scores = rng.uniform(0, 1, 500)
    labels = (scores > 0.5).astype(int)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "agent_x.joblib"
        fit_platt(scores, labels, out)
        reg = CalibratorRegistry(dir_=Path(td))
        p_low = reg.calibrate("agent_x", 0.1)
        p_hi = reg.calibrate("agent_x", 0.9)
        assert 0.0 <= p_low <= 1.0
        assert p_hi > p_low


def test_isotonic_extrapolates_clipped():
    rng = np.random.default_rng(1)
    scores = rng.uniform(0, 1, 500)
    labels = (scores > 0.3).astype(int)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "agent_y.joblib"
        fit_isotonic(scores, labels, out)
        reg = CalibratorRegistry(dir_=Path(td))
        # out-of-range should be clipped, not crash
        p = reg.calibrate("agent_y", 1.5)
        assert 0.0 <= p <= 1.0


def test_missing_calibrator_preserves_probability_score():
    reg = CalibratorRegistry(dir_=Path("/nonexistent"))
    assert reg.calibrate("missing-agent", 0.0) == 0.0
    assert reg.calibrate("missing-agent", 0.01) == 0.01
    assert reg.calibrate("missing-agent", 0.99) == 0.99
    assert reg.calibrate("missing-agent", 2.0) == 1.0
