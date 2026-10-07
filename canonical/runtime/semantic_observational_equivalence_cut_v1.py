from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from math import ceil, log2
import json
from typing import Any, Mapping, Sequence


class ObservationalEquivalenceCutError(ValueError):
    pass


def _obs_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalize(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    queries: Mapping[str, Mapping[str, Any]],
):
    ws=tuple(str(w) for w in worlds)
    ps=tuple(str(p) for p in policies)
    if not ws or len(set(ws))!=len(ws):
        raise ObservationalEquivalenceCutError("WORLD_DOMAIN_INVALID")
    if not ps or len(set(ps))!=len(ps):
        raise ObservationalEquivalenceCutError("POLICY_DOMAIN_INVALID")
    pset=set(ps)
    a={}
    for w in ws:
        if w not in adequate:
            raise ObservationalEquivalenceCutError("ADEQUATE_SET_MISSING:"+w)
        aset=frozenset(str(p) for p in adequate[w])
        if not aset:
            raise ObservationalEquivalenceCutError("NO_ADEQUATE_POLICY:"+w)
        if not aset <= pset:
            raise ObservationalEquivalenceCutError("UNKNOWN_POLICY:"+w)
        a[w]=aset
    q={}
    for qid, mapping in queries.items():
        qid=str(qid)
        if set(mapping)!=set(ws):
            raise ObservationalEquivalenceCutError("QUERY_WORLD_DOMAIN_MISMATCH:"+qid)
        q[qid]={w:_obs_key(mapping[w]) for w in ws}
    return ws,ps,a,q


def _minimum_cover(
    cell: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, frozenset[str]],
) -> tuple[str,...]:
    target=set(cell)
    covers={p:{w for w in cell if p in adequate[w]} for p in policies}
    for k in range(1,len(policies)+1):
        for combo in combinations(policies,k):
            if set().union(*(covers[p] for p in combo))==target:
                return combo
    raise ObservationalEquivalenceCutError("NO_POLICY_COVER")


def observational_equivalence_classes(
    worlds: Sequence[str],
    queries: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[str,...], ...]:
    ws=tuple(str(w) for w in worlds)
    qids=tuple(sorted(str(q) for q in queries))
    if not ws:
        raise ObservationalEquivalenceCutError("WORLD_DOMAIN_INVALID")
    if any(set(queries[q])!=set(ws) for q in qids):
        raise ObservationalEquivalenceCutError("QUERY_WORLD_DOMAIN_MISMATCH")
    groups={}
    for w in ws:
        sig=tuple(_obs_key(queries[q][w]) for q in qids)
        groups.setdefault(sig,[]).append(w)
    return tuple(sorted((tuple(sorted(v)) for v in groups.values()),key=lambda x:x))


def full_query_irreducible_states(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    queries: Mapping[str, Mapping[str, Any]],
) -> int:
    ws,ps,a,q=_normalize(worlds,policies,adequate,queries)
    classes=observational_equivalence_classes(ws,q)
    return max(len(_minimum_cover(cell,ps,a)) for cell in classes)


def full_query_irreducible_bits(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    queries: Mapping[str, Mapping[str, Any]],
) -> int:
    r=full_query_irreducible_states(worlds,policies,adequate,queries)
    return 0 if r==1 else ceil(log2(r))


def zero_residual_semantic_information(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    queries: Mapping[str, Mapping[str, Any]],
) -> bool:
    return full_query_irreducible_states(worlds,policies,adequate,queries)==1


def optimal_query_cut(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    queries: Mapping[str, Mapping[str, Any]],
    budget: int,
) -> dict[str,Any]:
    if not isinstance(budget,int) or isinstance(budget,bool) or budget<0:
        raise ObservationalEquivalenceCutError("BUDGET_INVALID")
    ws,ps,a,q=_normalize(worlds,policies,adequate,queries)
    qids=tuple(sorted(q))

    @lru_cache(maxsize=None)
    def solve(cell: tuple[str,...], remaining: tuple[str,...], b: int):
        no_query_cover=_minimum_cover(cell,ps,a)
        best=(len(no_query_cover),("STOP",),{"cover":no_query_cover})
        if b==0 or len(cell)<=1 or not remaining:
            return best

        for qid in remaining:
            buckets={}
            for w in cell:
                buckets.setdefault(q[qid][w],[]).append(w)
            parts=tuple(sorted((tuple(sorted(v)) for v in buckets.values()),key=lambda x:x))
            if len(parts)<=1:
                continue
            rem=tuple(x for x in remaining if x!=qid)
            child=[solve(part,rem,b-1) for part in parts]
            worst=max(x[0] for x in child)
            witness=("QUERY",qid,tuple((part,child[i][1]) for i,part in enumerate(parts)))
            detail={"query":qid,"parts":parts,"children":tuple(x[2] for x in child)}
            cand=(worst,witness,detail)
            if cand[0]<best[0] or (cand[0]==best[0] and repr(cand[1])<repr(best[1])):
                best=cand
        return best

    states,witness,detail=solve(tuple(sorted(ws)),qids,budget)
    bits=0 if states==1 else ceil(log2(states))
    return {
        "persistent_states":states,
        "persistent_bits":bits,
        "budget":budget,
        "decision_tree":witness,
        "detail":detail,
        "zero_residual_semantic_information":states==1,
    }


def exact_finite_theorem_summary(
    worlds: Sequence[str],
    policies: Sequence[str],
    adequate: Mapping[str, Sequence[str]],
    queries: Mapping[str, Mapping[str, Any]],
) -> dict[str,Any]:
    ws,ps,a,q=_normalize(worlds,policies,adequate,queries)
    classes=observational_equivalence_classes(ws,q)
    covers={cell:_minimum_cover(cell,ps,a) for cell in classes}
    states=max(len(c) for c in covers.values())
    return {
        "equivalence_classes":classes,
        "cell_minimum_policy_covers":covers,
        "irreducible_persistent_states":states,
        "irreducible_persistent_bits":0 if states==1 else ceil(log2(states)),
        "zero_residual_semantic_information":states==1,
        "theorem_boundary":"FINITE_DECLARED_WORLD_POLICY_AND_ADMISSIBLE_QUERY_UNIVERSE",
    }


def unsplittable_counterexample():
    worlds=("w0","w1")
    policies=("p0","p1")
    adequate={"w0":("p0",),"w1":("p1",)}
    queries={
        "q0":{"w0":"same","w1":"same"},
        "q1":{"w0":0,"w1":0},
    }
    return exact_finite_theorem_summary(worlds,policies,adequate,queries)


def two_query_zero_residual_example():
    worlds=("w00","w01","w10","w11")
    policies=("p00","p01","p10","p11")
    adequate={w:(f"p{w[1:]}",) for w in worlds}
    queries={
        "qA":{"w00":0,"w01":0,"w10":1,"w11":1},
        "qB":{"w00":0,"w01":1,"w10":0,"w11":1},
    }
    return {
        "b0":optimal_query_cut(worlds,policies,adequate,queries,0),
        "b1":optimal_query_cut(worlds,policies,adequate,queries,1),
        "b2":optimal_query_cut(worlds,policies,adequate,queries,2),
        "full":exact_finite_theorem_summary(worlds,policies,adequate,queries),
    }
