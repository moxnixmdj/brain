"""Minimal donor-independent PC-Stable observational skeleton discovery.

Mechanism derived from py-why/causal-learn PC skeleton discovery, pinned donor
revision 0dacacf36390e3084704636bc3c36e82e35ee0cc (MIT).

Scope: continuous complete data, Fisher-Z conditional-independence test,
stable undirected skeleton only. No edge orientation, missing-data correction,
kernel/discrete CI tests, background knowledge, or causal-effect claims.
"""
from __future__ import annotations
from itertools import combinations
from math import erfc, log, sqrt
from typing import Iterable
import numpy as np

def fisher_z_pvalue(corr: np.ndarray, n: int, x: int, y: int, cond: Iterable[int]=()) -> float:
    s=tuple(sorted(set(int(i) for i in cond)))
    if x==y or x in s or y in s:
        raise ValueError("x, y and conditioning set must be disjoint")
    if n-len(s)-3 <= 0:
        raise ValueError("insufficient samples for conditioning set")
    var=(int(x),int(y),*s)
    sub=corr[np.ix_(var,var)]
    try:
        inv=np.linalg.inv(sub)
    except np.linalg.LinAlgError as exc:
        raise ValueError("singular correlation submatrix") from exc
    r=-inv[0,1]/sqrt(abs(inv[0,0]*inv[1,1]))
    if abs(r)>=1:
        r=(1.0-np.finfo(float).eps)*(1.0 if r>=0 else -1.0)
    z=0.5*log((1+r)/(1-r))
    statistic=sqrt(n-len(s)-3)*abs(z)
    return erfc(statistic/sqrt(2.0))

def pc_stable_skeleton(data: np.ndarray, alpha: float=0.05, max_k: int|None=None) -> np.ndarray:
    data=np.asarray(data,dtype=float)
    if data.ndim!=2 or data.shape[0]<4 or data.shape[1]<2:
        raise ValueError("data must be 2D with >=4 rows and >=2 columns")
    if np.isnan(data).any() or np.isinf(data).any():
        raise ValueError("complete finite data required")
    if not 0.0<alpha<1.0:
        raise ValueError("alpha must be in (0,1)")
    n,p=data.shape
    std=np.std(data,axis=0)
    if not np.isfinite(std).all() or np.any(std <= 0.0):
        raise ValueError("every variable must have positive finite variance")
    corr=np.corrcoef(data.T)
    if not np.isfinite(corr).all():
        raise ValueError("finite correlation matrix required")
    adj=np.ones((p,p),dtype=bool)
    np.fill_diagonal(adj,False)
    depth=0
    while True:
        degrees=adj.sum(axis=1)
        if int(degrees.max(initial=0))-1 < depth:
            break
        if max_k is not None and depth>max_k:
            break
        remove:set[tuple[int,int]]=set()
        for x in range(p):
            neigh_x=np.flatnonzero(adj[x])
            for y in neigh_x:
                y=int(y)
                if not adj[x,y]:
                    continue
                pools=[]
                px=tuple(int(i) for i in neigh_x if int(i)!=y)
                pools.append(px)
                py=tuple(int(i) for i in np.flatnonzero(adj[y]) if int(i)!=x)
                if py!=px:
                    pools.append(py)
                independent=False
                for pool in pools:
                    if len(pool)<depth:
                        continue
                    for s in combinations(pool,depth):
                        if fisher_z_pvalue(corr,n,x,y,s)>alpha:
                            remove.add((min(x,y),max(x,y)))
                            independent=True
                            break
                    if independent:
                        break
        for x,y in remove:
            adj[x,y]=adj[y,x]=False
        depth+=1
    return adj.astype(np.int8)
