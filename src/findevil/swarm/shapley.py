"""Shapley post-hoc attribution.

Per blueprint Part 7.5: exact enumeration for n <= 6 (2^n * n <= 384 fusions),
KernelSHAP-style linear surrogate for n > 6. Runs async *after* ledger append;
never gates mitigation.
"""

from __future__ import annotations

from itertools import chain, combinations
from math import comb

import numpy as np

from .ds_fusion import AgentReport, fuse


def powerset(xs):
    s = list(xs)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def shapley_attribution_exact(reports: list[AgentReport]) -> dict[str, float]:
    n = len(reports)
    if n == 0:
        return {}
    attr = {r.agent_id: 0.0 for r in reports}

    for i, ri in enumerate(reports):
        others = [r for j, r in enumerate(reports) if j != i]
        for S in powerset(others):
            with_i = list(S) + [ri]
            v_wi = fuse(with_i)["belief_evil"]
            v_wo = fuse(list(S))["belief_evil"] if S else 0.0
            k = len(S)
            weight = 1.0 / (n * comb(n - 1, k))
            attr[ri.agent_id] += weight * (v_wi - v_wo)
    return attr


def shapley_attribution_kernel(reports: list[AgentReport], n_samples: int = 256) -> dict[str, float]:
    """KernelSHAP-style sampling for n > 6."""
    rng = np.random.default_rng(0xFE)
    n = len(reports)
    attr = {r.agent_id: 0.0 for r in reports}
    ids = [r.agent_id for r in reports]

    for _ in range(n_samples):
        perm = rng.permutation(n)
        running: list[AgentReport] = []
        prev_bel = 0.0
        for idx in perm:
            running.append(reports[idx])
            bel = fuse(running)["belief_evil"]
            attr[ids[idx]] += bel - prev_bel
            prev_bel = bel

    return {k: v / n_samples for k, v in attr.items()}


def shapley_attribution(reports: list[AgentReport]) -> dict[str, float]:
    """Choose exact enumeration or KernelSHAP based on n."""
    if len(reports) <= 6:
        return shapley_attribution_exact(reports)
    return shapley_attribution_kernel(reports)
