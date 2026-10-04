"""Typed proof-route compiler and exact minimum verified certificate basis.

Scheduling/proof compression only. No acceptance or execution authority.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_TYPED_CERTIFICATE_BASIS_V1"

RELATIVE_ELO={
 "PROWORK_GDPVAL_GE_1846",
 "PROWORK_AA_BRIEFCASE_GE_1822",
 "ARTIFACT_AA_BRIEFCASE_GE_1822",
}

ROUTES={
 "PUBLIC_FIXED_BAR":(
   "FORMAL_THRESHOLD_ENTAILMENT",
   "OBJECTIVE_THRESHOLD_CEILING_OR_FLOOR",
   "EXHAUSTIVE_THRESHOLD_UNIVERSE",
   "SCOPE_SAFE_THRESHOLD_DOMINANCE",
   "EXISTING_COMPARATOR_EVIDENCE",
   "MATCHED_EMPIRICAL_SCORE",
 ),
 "RELATIVE_ELO_FIXED_BAR":(
   "RELATIVE_SCORE_BRIDGE",
   "EXISTING_RELATIVE_COMPARATOR_EVIDENCE",
   "OWNER_RELATIVE_RESULT",
   "MATCHED_RELATIVE_EMPIRICAL_COMPARISON",
 ),
 "MATCHED_NONINFERIORITY":(
   "FORMAL_MATCHED_DOMINANCE",
   "EXHAUSTIVE_MATCHED_UNIVERSE",
   "SCOPE_SAFE_MATCHED_STRONGER_PROOF",
   "EXISTING_MATCHED_COMPARATOR_EVIDENCE",
   "MATCHED_EMPIRICAL_COMPARISON",
 ),
 "MATCHED_SCOPE_AUDIT":(
   "UNIVERSAL_FORMAL_SCOPE_PROOF",
   "EXHAUSTIVE_FINITE_SCOPE_UNIVERSE",
   "SCOPE_SAFE_STRONGER_PROOF",
   "MATCHED_SCOPE_EVIDENCE",
 ),
 "DIRECT_SCOPE_AUDIT":(
   "UNIVERSAL_FORMAL_SCOPE_PROOF",
   "EXHAUSTIVE_FINITE_SCOPE_UNIVERSE",
   "SCOPE_SAFE_STRONGER_PROOF",
   "DIRECT_SCOPE_EVIDENCE",
 ),
 "INVARIANT":(
   "FORMAL_INVARIANT_PROOF",
   "EXHAUSTIVE_INVARIANT_UNIVERSE",
   "DIRECT_INVARIANT_EVIDENCE",
 ),
 "ABSOLUTE_CEILING":(
   "OBJECTIVE_CEILING_PROOF",
   "EXHAUSTIVE_CEILING_UNIVERSE",
 ),
 "DEPENDENCY_PROOF":(
   "UPSTREAM_SCOPE_RECEIPT_CLOSURE",
 ),
}
ALLOWED_SCOPE={"EXACT","SUPERSET"}

def typed_kind(predicate_id: str, kind: str) -> str:
    if predicate_id in RELATIVE_ELO:
        if kind != "PUBLIC_FIXED_BAR":
            raise ValueError("RELATIVE_ELO_KIND_MISMATCH")
        return "RELATIVE_ELO_FIXED_BAR"
    if kind not in ROUTES:
        raise ValueError(f"UNSUPPORTED_PREDICATE_KIND:{kind}")
    return kind

def compile_typed_routes(predicates: Sequence[Mapping[str,Any]]) -> dict[str,Any]:
    rows=[]; seen=set()
    for raw in predicates:
        pid=str(raw.get("id","")).strip()
        kind=str(raw.get("kind","")).strip()
        if not pid or pid in seen:
            raise ValueError("MISSING_OR_DUPLICATE_PREDICATE_ID")
        seen.add(pid)
        tk=typed_kind(pid,kind)
        rows.append({
          "predicate_id":pid,
          "registry_kind":kind,
          "typed_kind":tk,
          "routes":list(ROUTES[tk]),
          "route_count":len(ROUTES[tk]),
        })
    return {
      "schema":SCHEMA,
      "predicate_count":len(rows),
      "typed_route_count":sum(r["route_count"] for r in rows),
      "predicates":rows,
      "acceptance_credit_authorized":False,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }

def admit_verified_certificate(
    certificate: Mapping[str,Any],
    universe: set[str],
) -> dict[str,Any]:
    reasons=[]
    cid=str(certificate.get("certificate_id","")).strip()
    if not cid:
        reasons.append("MISSING_CERTIFICATE_ID")
    if certificate.get("source_content_addressed") is not True:
        reasons.append("SOURCE_NOT_CONTENT_ADDRESSED")
    implications=certificate.get("target_implications")
    if not isinstance(implications,Mapping) or not implications:
        reasons.append("TARGET_IMPLICATIONS_MISSING")
        implications={}

    covers=set()
    for pid,imp in implications.items():
        if pid not in universe:
            reasons.append(f"TARGET_OUTSIDE_UNIVERSE:{pid}")
            continue
        if not isinstance(imp,Mapping):
            reasons.append(f"INVALID_IMPLICATION:{pid}")
            continue
        scope=str(imp.get("scope_relation","")).upper()
        if scope not in ALLOWED_SCOPE:
            reasons.append(f"SCOPE_NOT_EXACT_OR_SUPERSET:{pid}")
        if imp.get("acceptance_implication_proved") is not True:
            reasons.append(f"ACCEPTANCE_IMPLICATION_NOT_PROVED:{pid}")
        if imp.get("independent_verification_pass") is not True:
            reasons.append(f"INDEPENDENT_VERIFICATION_NOT_BOUND:{pid}")
        if pid in RELATIVE_ELO and imp.get("relative_score_semantics_bound") is not True:
            reasons.append(f"RELATIVE_SCORE_SEMANTICS_NOT_BOUND:{pid}")
        if (
          scope in ALLOWED_SCOPE
          and imp.get("acceptance_implication_proved") is True
          and imp.get("independent_verification_pass") is True
          and (pid not in RELATIVE_ELO or imp.get("relative_score_semantics_bound") is True)
        ):
            covers.add(pid)

    admitted=not reasons
    return {
      "schema":SCHEMA,
      "certificate_id":cid,
      "admitted":admitted,
      "covers":sorted(covers) if admitted else [],
      "reasons":sorted(reasons),
      "critical_path_seconds":certificate.get("critical_path_seconds"),
      "acceptance_credit_authorized":False,
      "requires_separate_predicate_activation":True,
    }

def minimum_verified_basis(
    universe_ids: Sequence[str],
    certificates: Sequence[Mapping[str,Any]],
    *,
    max_solutions: int=32,
) -> dict[str,Any]:
    universe=set(universe_ids)
    if len(universe)!=len(list(universe_ids)) or not universe:
        raise ValueError("UNIVERSE_EMPTY_OR_DUPLICATE")
    admitted=[]
    for c in certificates:
        a=admit_verified_certificate(c,universe)
        if a["admitted"] and a["covers"]:
            admitted.append(a)

    union=set().union(*(set(a["covers"]) for a in admitted)) if admitted else set()
    residual=sorted(universe-union)
    if residual:
        return {
          "schema":SCHEMA,
          "complete_basis_exists":False,
          "minimum_action_count":None,
          "solutions":[],
          "uncovered_predicates":residual,
          "admitted_certificate_count":len(admitted),
          "acceptance_credit_authorized":False,
        }

    by_pid={p:[] for p in universe}
    for i,a in enumerate(admitted):
        for p in a["covers"]:
            by_pid[p].append(i)

    best_count=[10**9]
    solutions: list[tuple[int,...]]=[]
    def search(covered:set[str], chosen:tuple[int,...], start_guard:set[int]):
        if len(chosen)>best_count[0]:
            return
        if covered==universe:
            if len(chosen)<best_count[0]:
                best_count[0]=len(chosen); solutions.clear()
            if len(chosen)==best_count[0] and len(solutions)<max_solutions:
                solutions.append(chosen)
            return
        remaining=universe-covered
        pivot=min(remaining,key=lambda p:sum(1 for i in by_pid[p] if i not in start_guard))
        options=[i for i in by_pid[pivot] if i not in start_guard]
        # deterministic high-fanout-first ordering speeds branch-and-bound.
        options.sort(key=lambda i:(-len(set(admitted[i]["covers"])-covered),admitted[i]["certificate_id"]))
        for i in options:
            search(
              covered|set(admitted[i]["covers"]),
              chosen+(i,),
              start_guard|{j for j in options if j<i},
            )

    # Simpler exact recursion without unsafe heuristic pruning.
    solutions=[]; best_count[0]=10**9
    def exact(covered:set[str],chosen:tuple[int,...],available:frozenset[int]):
        if len(chosen)>best_count[0]:
            return
        if covered==universe:
            if len(chosen)<best_count[0]:
                best_count[0]=len(chosen); solutions.clear()
            if len(chosen)==best_count[0] and len(solutions)<max_solutions:
                solutions.append(chosen)
            return
        remaining=universe-covered
        pivot=min(remaining,key=lambda p:sum(1 for i in by_pid[p] if i in available))
        opts=[i for i in by_pid[pivot] if i in available]
        opts.sort(key=lambda i:(-len(set(admitted[i]["covers"])-covered),admitted[i]["certificate_id"]))
        for pos,i in enumerate(opts):
            next_available=frozenset(j for j in available if j!=i)
            exact(covered|set(admitted[i]["covers"]),chosen+(i,),next_available)
    exact(set(),tuple(),frozenset(range(len(admitted))))

    rendered=[]
    seen_keys=set()
    for sol in solutions:
        ids=tuple(sorted(admitted[i]["certificate_id"] for i in sol))
        if ids in seen_keys: continue
        seen_keys.add(ids)
        times=[admitted[i].get("critical_path_seconds") for i in sol]
        known=all(isinstance(t,(int,float)) and not isinstance(t,bool) and t>=0 for t in times)
        rendered.append({
          "certificate_ids":list(ids),
          "action_count":len(ids),
          "known_total_critical_path_seconds":sum(times) if known else None,
          "unknown_cost_preserved":not known,
        })
    rendered.sort(key=lambda x:(x["action_count"],x["known_total_critical_path_seconds"] is None,x["known_total_critical_path_seconds"] or 0,x["certificate_ids"]))
    return {
      "schema":SCHEMA,
      "complete_basis_exists":True,
      "minimum_action_count":best_count[0],
      "solutions":rendered[:max_solutions],
      "uncovered_predicates":[],
      "admitted_certificate_count":len(admitted),
      "cost_rule":"UNKNOWN_COST_IS_NEVER_GUESSED__SECONDARY_TIME_ORDER_USED_ONLY_WHEN_ALL_SELECTED_COSTS_ARE_KNOWN",
      "acceptance_credit_authorized":False,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }
