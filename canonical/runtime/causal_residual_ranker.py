"""Minimal donor-independent residual cause ranker.

Mechanism derived from salesforce/PyRCA HT at revision
411310d589fac5cb8e7bdce67d33eadb091a1083 (BSD-3-Clause).

Scope: explicit numeric causal DAG; normal reference samples; abnormal incident
samples; rank candidate nodes by maximum absolute standardized structural
residual. No causal edge discovery, intervenability inference, or general RCA.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class NodeModel:
    parents: tuple[str, ...]
    coef: np.ndarray | None
    intercept: float
    residual_mean: float
    residual_std: float


class ResidualCauseRanker:
    def __init__(self, nodes: Sequence[str], parents: Mapping[str, Sequence[str]]):
        self.nodes = tuple(nodes)
        self.parents = {n: tuple(parents.get(n, ())) for n in self.nodes}
        self.models: dict[str, NodeModel] = {}

    @staticmethod
    def _fit_linear(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
        ones = np.ones((x.shape[0], 1), dtype=float)
        design = np.concatenate([x.astype(float), ones], axis=1)
        beta, *_ = np.linalg.lstsq(design, y.astype(float), rcond=None)
        return beta[:-1], float(beta[-1])

    @staticmethod
    def _mean_std(v: np.ndarray) -> tuple[float, float]:
        mean = float(np.mean(v))
        std = float(np.std(v, ddof=0))
        if not np.isfinite(std) or std <= 0.0:
            raise ValueError("reference residual standard deviation must be positive")
        return mean, std

    def fit(self, normal: Mapping[str, np.ndarray]) -> "ResidualCauseRanker":
        lengths = {len(np.asarray(normal[n])) for n in self.nodes}
        if len(lengths) != 1:
            raise ValueError("all normal node arrays must have equal length")
        for node in self.nodes:
            y = np.asarray(normal[node], dtype=float)
            ps = self.parents[node]
            if ps:
                x = np.column_stack([np.asarray(normal[p], dtype=float) for p in ps])
                coef, intercept = self._fit_linear(x, y)
                residual = y - (x @ coef + intercept)
            else:
                coef, intercept = None, 0.0
                residual = y
            mean, std = self._mean_std(residual)
            self.models[node] = NodeModel(ps, coef, intercept, mean, std)
        return self

    def score(self, abnormal: Mapping[str, np.ndarray]) -> dict[str, float]:
        if set(self.models) != set(self.nodes):
            raise RuntimeError("ranker must be fit before scoring")
        scores: dict[str, float] = {}
        for node in self.nodes:
            model = self.models[node]
            y = np.asarray(abnormal[node], dtype=float)
            if model.parents:
                x = np.column_stack([np.asarray(abnormal[p], dtype=float) for p in model.parents])
                residual = y - (x @ model.coef + model.intercept)
            else:
                residual = y
            z = (residual - model.residual_mean) / model.residual_std
            scores[node] = float(np.max(np.abs(z)))
        return scores

    def rank(
        self,
        abnormal: Mapping[str, np.ndarray],
        candidates: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        scores = self.score(abnormal)
        chosen = self.nodes if candidates is None else tuple(candidates)
        missing = [n for n in chosen if n not in scores]
        if missing:
            raise ValueError("unknown candidate(s): " + ",".join(missing))
        return sorted(((n, scores[n]) for n in chosen), key=lambda x: x[1], reverse=True)
