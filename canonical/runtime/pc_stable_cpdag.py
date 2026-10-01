"""Donor-independent PC-Stable CPDAG bridge.

Derived from benovamurat/causal-discovery-pc at revision
efc99e13dcc4a0f1e731ba46f5a0a20d75f4937b (MIT), combined with Brain's
already-owned Fisher-Z PC-Stable skeleton mechanism.

Scope: continuous complete data; Fisher-Z; PC-Stable skeleton with separating
sets; collider orientation; Meek R1-R4 propagation; unresolved Markov-equivalent
edges remain undirected as reciprocal adjacency. No hidden-confounder handling,
time-lag inference, nonlinear CI tests, or intervention claims.
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


def pc_stable_skeleton_with_sepsets(
    data: np.ndarray,
    alpha: float=0.05,
    max_k: int|None=None,
) -> tuple[np.ndarray, dict[tuple[int,int], tuple[int,...]]]:
    data=np.asarray(data,dtype=float)
    if data.ndim!=2 or data.shape[0]<4 or data.shape[1]<2:
        raise ValueError("data must be 2D with >=4 rows and >=2 columns")
    if np.isnan(data).any() or np.isinf(data).any():
        raise ValueError("complete finite data required")
    if not 0.0<alpha<1.0:
        raise ValueError("alpha must be in (0,1)")
    n,p=data.shape
    std=np.std(data,axis=0)
    if not np.isfinite(std).all() or np.any(std<=0.0):
        raise ValueError("every variable must have positive finite variance")
    corr=np.corrcoef(data.T)
    if not np.isfinite(corr).all():
        raise ValueError("finite correlation matrix required")
    adj=np.ones((p,p),dtype=bool)
    np.fill_diagonal(adj,False)
    sepsets: dict[tuple[int,int], tuple[int,...]]={}
    depth=0
    while True:
        degrees=adj.sum(axis=1)
        if int(degrees.max(initial=0))-1 < depth:
            break
        if max_k is not None and depth>max_k:
            break
        remove:set[tuple[int,int]]=set()
        found_sep:dict[tuple[int,int], tuple[int,...]]={}
        snapshot=adj.copy()
        for x in range(p):
            neigh_x=np.flatnonzero(snapshot[x])
            for y0 in neigh_x:
                y=int(y0)
                if not snapshot[x,y]:
                    continue
                key=(min(x,y),max(x,y))
                if key in remove:
                    continue
                pools=[]
                px=tuple(int(i) for i in neigh_x if int(i)!=y)
                pools.append(px)
                py=tuple(int(i) for i in np.flatnonzero(snapshot[y]) if int(i)!=x)
                if py!=px:
                    pools.append(py)
                independent=False
                for pool in pools:
                    if len(pool)<depth:
                        continue
                    for s in combinations(pool,depth):
                        if fisher_z_pvalue(corr,n,x,y,s)>alpha:
                            remove.add(key)
                            found_sep[key]=tuple(int(i) for i in s)
                            independent=True
                            break
                    if independent:
                        break
        for key in sorted(remove):
            x,y=key
            adj[x,y]=adj[y,x]=False
            sepsets.setdefault(key,found_sep[key])
        depth+=1
    return adj.astype(np.int8), sepsets


def _is_directed(g: np.ndarray, u: int, v: int) -> bool:
    return bool(g[u,v]) and not bool(g[v,u])


def _is_undirected(g: np.ndarray, u: int, v: int) -> bool:
    return bool(g[u,v]) and bool(g[v,u])


def _adjacent(g: np.ndarray, u: int, v: int) -> bool:
    return bool(g[u,v]) or bool(g[v,u])


def _orient(g: np.ndarray, u: int, v: int) -> bool:
    if _is_undirected(g,u,v):
        g[v,u]=0
        return True
    return False


def orient_v_structures(
    skeleton: np.ndarray,
    separating_sets: dict[tuple[int,int], tuple[int,...]],
) -> np.ndarray:
    sk=np.asarray(skeleton,dtype=np.int8)
    if sk.ndim!=2 or sk.shape[0]!=sk.shape[1]:
        raise ValueError("skeleton must be square")
    if np.any(np.diag(sk)!=0) or not np.array_equal(sk,sk.T):
        raise ValueError("skeleton must be symmetric with zero diagonal")
    g=sk.copy()
    p=g.shape[0]
    for y in range(p):
        neighbors=[int(i) for i in np.flatnonzero(sk[y])]
        for i in range(len(neighbors)):
            for j in range(i+1,len(neighbors)):
                x,z=neighbors[i],neighbors[j]
                if sk[x,z]:
                    continue
                sep=separating_sets.get((min(x,z),max(x,z)),())
                if y not in sep:
                    if g[y,x]:
                        g[y,x]=0
                    if g[y,z]:
                        g[y,z]=0
    return g


def meek_r1(g: np.ndarray) -> bool:
    changed=False
    p=g.shape[0]
    for y in range(p):
        parents=[x for x in range(p) if _is_directed(g,x,y)]
        und=[z for z in range(p) if _is_undirected(g,y,z)]
        for x in parents:
            for z in und:
                if z!=x and not _adjacent(g,x,z):
                    changed |= _orient(g,y,z)
    return changed


def meek_r2(g: np.ndarray) -> bool:
    changed=False
    p=g.shape[0]
    for x in range(p):
        for y in range(p):
            if x==y or not _is_undirected(g,x,y):
                continue
            for z in range(p):
                if z in (x,y):
                    continue
                if _is_directed(g,x,z) and _is_directed(g,z,y):
                    changed |= _orient(g,x,y)
                    break
    return changed


def meek_r3(g: np.ndarray) -> bool:
    changed=False
    p=g.shape[0]
    for x in range(p):
        und=[n for n in range(p) if _is_undirected(g,x,n)]
        for z in list(und):
            candidates=[n for n in und if n!=z]
            for i in range(len(candidates)):
                for j in range(i+1,len(candidates)):
                    y,w=candidates[i],candidates[j]
                    if _adjacent(g,y,w):
                        continue
                    if _is_directed(g,y,z) and _is_directed(g,w,z):
                        changed |= _orient(g,x,z)
    return changed


def meek_r4(g: np.ndarray) -> bool:
    changed=False
    p=g.shape[0]
    for x in range(p):
        und=[n for n in range(p) if _is_undirected(g,x,n)]
        for w in list(und):
            for y in und:
                if y==w or _adjacent(g,w,y):
                    continue
                for z in und:
                    if z in (y,w):
                        continue
                    if _is_directed(g,y,z) and _is_directed(g,z,w):
                        changed |= _orient(g,x,w)
                        break
    return changed


def apply_meek_rules(g: np.ndarray, max_iter: int=100) -> np.ndarray:
    g=np.asarray(g,dtype=np.int8).copy()
    if g.ndim!=2 or g.shape[0]!=g.shape[1]:
        raise ValueError("graph must be square")
    for _ in range(max_iter):
        changed=False
        changed |= meek_r1(g)
        changed |= meek_r2(g)
        changed |= meek_r3(g)
        changed |= meek_r4(g)
        if not changed:
            return g
    raise RuntimeError("Meek orientation did not converge within max_iter")


def cpdag_from_skeleton(
    skeleton: np.ndarray,
    separating_sets: dict[tuple[int,int], tuple[int,...]],
) -> np.ndarray:
    return apply_meek_rules(orient_v_structures(skeleton,separating_sets))


def pc_stable_cpdag(
    data: np.ndarray,
    alpha: float=0.05,
    max_k: int|None=None,
) -> tuple[np.ndarray, np.ndarray, dict[tuple[int,int], tuple[int,...]]]:
    skeleton,sepsets=pc_stable_skeleton_with_sepsets(data,alpha=alpha,max_k=max_k)
    return cpdag_from_skeleton(skeleton,sepsets),skeleton,sepsets
