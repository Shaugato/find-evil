"""Per-agent calibration — Platt, isotonic, temperature scaling.

Blueprint Part 7.3:
  * |validation| <= 1000 -> Platt (logistic regression over raw score)
  * otherwise -> isotonic regression
  * models emitting logits -> temperature scaling σ(z/T)
Calibrators live at /opt/findevil/data/calibrators/{agent_id}.joblib and are loaded
once at boot by the CalibratorRegistry.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Optional

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from findevil.config.settings import settings


def fit_platt(scores: Iterable[float], labels: Iterable[int], out: Path) -> None:
    clf = LogisticRegression().fit(np.asarray(list(scores)).reshape(-1, 1), list(labels))
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out)


def fit_isotonic(scores: Iterable[float], labels: Iterable[int], out: Path) -> None:
    iso = IsotonicRegression(out_of_bounds="clip").fit(list(scores), list(labels))
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(iso, out)


def fit_temperature(logits: Iterable[float], labels: Iterable[int]) -> float:
    """Closed-form temperature using NLL minimization on a 1-D search."""
    logits_arr = np.asarray(list(logits))
    labels_arr = np.asarray(list(labels))
    best_T, best_nll = 1.0, float("inf")
    for T in np.linspace(0.1, 5.0, 50):
        p = 1.0 / (1.0 + np.exp(-logits_arr / T))
        eps = 1e-9
        nll = float(-np.mean(labels_arr * np.log(p + eps) + (1 - labels_arr) * np.log(1 - p + eps)))
        if nll < best_nll:
            best_nll, best_T = nll, float(T)
    return best_T


class _IdentityCal:
    """Probability-preserving fallback used when no calibrator exists.

    Parser confidence values are already normalized probabilities. Applying a
    sigmoid here compresses low scores toward 0.5, which erases benign
    counter-evidence and prevents the Yager conflict path from firing.
    """

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        p = np.clip(x.reshape(-1), 0.0, 1.0)
        return np.column_stack([1 - p, p])


class CalibratorRegistry:
    """Load & cache per-agent calibrators. Thread-safe by virtue of joblib objects."""

    def __init__(self, dir_: Optional[Path] = None):
        self.dir = Path(dir_ or "/opt/findevil/data/calibrators")
        self._cache: dict[str, object] = {}

    def load(self, agent_id: str):
        if agent_id in self._cache:
            return self._cache[agent_id]
        path = self.dir / f"{agent_id}.joblib"
        if path.exists():
            cal = joblib.load(path)
        else:
            cal = _IdentityCal()
        self._cache[agent_id] = cal
        return cal

    def calibrate(self, agent_id: str, raw_score: float) -> float:
        cal = self.load(agent_id)
        x = np.asarray([[raw_score]])
        if isinstance(cal, IsotonicRegression):
            return float(cal.predict([raw_score])[0])
        if hasattr(cal, "predict_proba"):
            return float(cal.predict_proba(x.reshape(-1, 1))[0, 1])
        return float(1.0 / (1.0 + math.exp(-raw_score)))


_registry: Optional[CalibratorRegistry] = None


def registry() -> CalibratorRegistry:
    global _registry
    if _registry is None:
        _registry = CalibratorRegistry()
    return _registry
