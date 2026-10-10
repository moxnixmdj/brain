"""Minimal donor-independent robust anomaly candidate ranker.

Mechanism derived from BARO in phamquiluan/RCAEval revision
259ea4167160256a74ad30004aa3d96a998c846e (MIT / BARO MIT).

Scope: numeric non-constant variables split into normal reference and abnormal
incident samples. Per variable, center by normal median, scale by normal
interquartile range (Q75-Q25), score by the maximum standardized abnormal
value, and rank descending. This is candidate retrieval, not causal proof.
"""
from __future__ import annotations

from typing import Mapping, Sequence
import numpy as np


class RobustCandidateRanker:
    def __init__(self, variables: Sequence[str]):
        self.variables=tuple(variables)
        if not self.variables:
            raise ValueError("variables must be non-empty")
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("variables must be unique")
        self.center_: dict[str,float]={}
        self.scale_: dict[str,float]={}

    @staticmethod
    def _center_scale(v: np.ndarray) -> tuple[float,float]:
        x=np.asarray(v,dtype=float)
        if x.ndim!=1 or x.size==0 or not np.isfinite(x).all():
            raise ValueError("reference arrays must be non-empty finite 1D")
        center=float(np.median(x))
        q25,q75=np.percentile(x,[25.0,75.0])
        scale=float(q75-q25)
        # Match sklearn RobustScaler's zero-scale handling.
        if not np.isfinite(scale) or scale < 10*np.finfo(float).eps:
            scale=1.0
        return center,scale

    def fit(self, normal: Mapping[str,np.ndarray]) -> "RobustCandidateRanker":
        for name in self.variables:
            if name not in normal:
                raise ValueError(f"missing normal variable: {name}")
            center,scale=self._center_scale(np.asarray(normal[name],dtype=float))
            self.center_[name]=center
            self.scale_[name]=scale
        return self

    def score(self, abnormal: Mapping[str,np.ndarray]) -> dict[str,float]:
        if set(self.center_) != set(self.variables):
            raise RuntimeError("ranker must be fit before scoring")
        out={}
        for name in self.variables:
            if name not in abnormal:
                raise ValueError(f"missing abnormal variable: {name}")
            x=np.asarray(abnormal[name],dtype=float)
            if x.ndim!=1 or x.size==0 or not np.isfinite(x).all():
                raise ValueError("abnormal arrays must be non-empty finite 1D")
            z=(x-self.center_[name])/self.scale_[name]
            out[name]=float(np.max(z))
        return out

    def rank(self, abnormal: Mapping[str,np.ndarray]) -> list[tuple[str,float]]:
        scores=self.score(abnormal)
        order={name:i for i,name in enumerate(self.variables)}
        return sorted(scores.items(),key=lambda kv:(-kv[1],order[kv[0]]))

    def candidates(self, abnormal: Mapping[str,np.ndarray], k: int) -> list[str]:
        if not isinstance(k,int) or isinstance(k,bool) or k<1:
            raise ValueError("k must be a positive integer")
        return [name for name,_ in self.rank(abnormal)[:k]]
