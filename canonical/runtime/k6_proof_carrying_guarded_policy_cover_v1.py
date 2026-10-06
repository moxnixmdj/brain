from __future__ import annotations
from typing import Mapping, Sequence, Any


class GuardedCoverError(ValueError):
    pass


def compile_guarded_cover(
    *,
    contexts: Sequence[str],
    policies: Sequence[str],
    certified_adequate: Mapping[str, Sequence[str]],
    guards: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    cs=tuple(str(c) for c in contexts)
    ps=tuple(str(p) for p in policies)
    if not cs or len(set(cs))!=len(cs): raise GuardedCoverError("CONTEXT_DOMAIN_INVALID")
    if not ps or len(set(ps))!=len(ps): raise GuardedCoverError("POLICY_DOMAIN_INVALID")
    pset=set(ps)
    adequacy={}
    for c in cs:
        if c not in certified_adequate: raise GuardedCoverError("ADEQUACY_MISSING:"+c)
        vals=set(str(p) for p in certified_adequate[c])
        if not vals<=pset: raise GuardedCoverError("UNKNOWN_POLICY_IN_ADEQUACY:"+c)
        adequacy[c]=vals

    normalized=[]
    seen=set()
    for raw in guards:
        gid=str(raw.get("id") or "")
        policy=str(raw.get("policy") or "")
        holds=raw.get("holds")
        if not gid or gid in seen: raise GuardedCoverError("GUARD_ID_INVALID_OR_DUPLICATE")
        seen.add(gid)
        if policy not in pset: raise GuardedCoverError("GUARD_POLICY_INVALID:"+gid)
        if not isinstance(holds,Mapping) or any(c not in holds for c in cs):
            raise GuardedCoverError("GUARD_TRUTH_INCOMPLETE:"+gid)
        truth={c:holds[c] for c in cs}
        if any(type(v) is not bool for v in truth.values()):
            raise GuardedCoverError("GUARD_TRUTH_NOT_BOOL:"+gid)
        false_positive=[c for c in cs if truth[c] and policy not in adequacy[c]]
        if false_positive:
            return {
              "status":"GUARD_SOUNDNESS_FALSIFIED",
              "guard":gid,"policy":policy,"counterexample_contexts":false_positive,
              "terminal_credit_delta":0
            }
        normalized.append({"id":gid,"policy":policy,"holds":truth})

    uncovered=[c for c in cs if not any(g["holds"][c] for g in normalized)]
    if uncovered:
        return {
          "status":"INCOMPLETE_GUARD_COVER",
          "uncovered_contexts":uncovered,
          "terminal_credit_delta":0
        }

    decisions={}
    for c in cs:
        fired=[g for g in normalized if g["holds"][c]]
        fired.sort(key=lambda g:g["id"])
        chosen=fired[0]
        decisions[c]={"guard":chosen["id"],"policy":chosen["policy"]}

    return {
      "status":"CERTIFIED_FINITE_GUARDED_POLICY_COVER",
      "context_count":len(cs),
      "guard_count":len(normalized),
      "decisions":decisions,
      "all_selected_policies_certified_adequate":all(
          decisions[c]["policy"] in adequacy[c] for c in cs
      ),
      "universal_beyond_declared_contexts_claimed":False,
      "terminal_credit_delta":0,
    }


def compile_falsifiers() -> dict[str, Any]:
    contexts=("c0","c1","c2")
    policies=("p0","p1")
    adequate={"c0":("p0",),"c1":("p0","p1"),"c2":("p1",)}
    good=compile_guarded_cover(
      contexts=contexts,policies=policies,certified_adequate=adequate,
      guards=[
        {"id":"g0","policy":"p0","holds":{"c0":True,"c1":True,"c2":False}},
        {"id":"g1","policy":"p1","holds":{"c0":False,"c1":True,"c2":True}},
      ])
    bad=compile_guarded_cover(
      contexts=contexts,policies=policies,certified_adequate=adequate,
      guards=[{"id":"bad","policy":"p0","holds":{"c0":True,"c1":True,"c2":True}}])
    missing=compile_guarded_cover(
      contexts=contexts,policies=policies,certified_adequate=adequate,
      guards=[{"id":"g0","policy":"p0","holds":{"c0":True,"c1":True,"c2":False}}])
    ok=(good["status"]=="CERTIFIED_FINITE_GUARDED_POLICY_COVER"
        and good["all_selected_policies_certified_adequate"] is True
        and bad["status"]=="GUARD_SOUNDNESS_FALSIFIED"
        and missing["status"]=="INCOMPLETE_GUARD_COVER")
    return {
      "status":"PASS__FINITE_GUARDED_POLICY_COVER_FALSIFIERS" if ok else "FAIL_CLOSED",
      "overlap_allowed":True,
      "false_positive_guard_detected":bad["status"]=="GUARD_SOUNDNESS_FALSIFIED",
      "uncovered_context_detected":missing["status"]=="INCOMPLETE_GUARD_COVER",
      "terminal_credit_delta":0,
    }
