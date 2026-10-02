"""Fail-closed proof-route dominance compiler.

Terminal requirements are behavioral obligations, not benchmark brand names.
A blocked/private benchmark route may be deleted from the required execution set
only when admissible executable zero-cost routes collectively cover every frozen
behavioral obligation attributed to it with equal-or-stronger oracle strength.

This compiler never invents equivalence.  Coverage and strength mappings must be
frozen inputs established independently before the verdict.
"""
from __future__ import annotations

from typing import Any, Mapping


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"schema":"BRAIN_PROOF_ROUTE_DOMINANCE_V1","status":"INVALID","errors":["INPUT_NOT_OBJECT"]}

    obligations = payload.get("obligations")
    routes = payload.get("routes")
    if not isinstance(obligations, list) or not isinstance(routes, list):
        return {"schema":"BRAIN_PROOF_ROUTE_DOMINANCE_V1","status":"INVALID","errors":["OBLIGATIONS_OR_ROUTES_NOT_LIST"]}

    errors: list[str] = []
    mins: dict[str, int] = {}
    for i, row in enumerate(obligations):
        if not isinstance(row, Mapping):
            errors.append(f"OBLIGATION_INVALID:{i}")
            continue
        oid=row.get("id"); strength=row.get("min_oracle_strength")
        if not isinstance(oid,str) or not oid or oid in mins:
            errors.append(f"OBLIGATION_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        if not isinstance(strength,int) or isinstance(strength,bool) or strength < 0:
            errors.append(f"OBLIGATION_STRENGTH_INVALID:{oid}")
            continue
        mins[oid]=strength

    normalized=[]
    ids=set()
    for i,row in enumerate(routes):
        if not isinstance(row, Mapping):
            errors.append(f"ROUTE_INVALID:{i}"); continue
        rid=row.get("id")
        covers=row.get("covers")
        strength=row.get("oracle_strength")
        if not isinstance(rid,str) or not rid or rid in ids:
            errors.append(f"ROUTE_ID_INVALID_OR_DUPLICATE:{i}"); continue
        ids.add(rid)
        if not isinstance(covers,list) or not covers or any(x not in mins for x in covers):
            errors.append(f"ROUTE_COVERAGE_INVALID:{rid}"); continue
        if not isinstance(strength,int) or isinstance(strength,bool) or strength < 0:
            errors.append(f"ROUTE_STRENGTH_INVALID:{rid}"); continue
        normalized.append({
            "id":rid,
            "covers":sorted(set(covers)),
            "oracle_strength":strength,
            "zero_cost":row.get("zero_cost") is True,
            "executable":row.get("executable") is True,
            "independent_oracle":row.get("independent_oracle") is True,
            "scope_mapping_frozen":row.get("scope_mapping_frozen") is True,
            "contamination_boundary_frozen":row.get("contamination_boundary_frozen") is True,
            "blocked":row.get("blocked") is True,
            "terminal_result_required":row.get("terminal_result_required") is True,
            "terminal_result_pass":row.get("terminal_result_pass") is True,
            "terminal_result_receipt":(
                row.get("terminal_result_receipt").strip()
                if isinstance(row.get("terminal_result_receipt"),str)
                and row.get("terminal_result_receipt").strip()
                else None
            ),
        })

    if errors:
        return {"schema":"BRAIN_PROOF_ROUTE_DOMINANCE_V1","status":"INVALID","errors":sorted(set(errors))}

    def admissible(r):
        return (
            r["zero_cost"] and r["executable"] and r["independent_oracle"]
            and r["scope_mapping_frozen"] and r["contamination_boundary_frozen"]
            and not r["blocked"]
            and (
                not r["terminal_result_required"]
                or (
                    r["terminal_result_pass"]
                    and r["terminal_result_receipt"] is not None
                )
            )
        )

    admissible_routes=[r for r in normalized if admissible(r)]
    obligation_support: dict[str,list[str]]={o:[] for o in mins}
    for oid,min_strength in mins.items():
        for r in admissible_routes:
            if oid in r["covers"] and r["oracle_strength"] >= min_strength:
                obligation_support[oid].append(r["id"])

    blocked_verdicts=[]
    for target in normalized:
        if not target["blocked"]:
            continue
        uncovered=[]
        supporters={}
        for oid in target["covers"]:
            support=sorted(obligation_support.get(oid,[]))
            if not support:
                uncovered.append(oid)
            else:
                supporters[oid]=support
        blocked_verdicts.append({
            "route_id":target["id"],
            "redundant":not uncovered,
            "uncovered_obligations":sorted(uncovered),
            "supporters":supporters,
            "rule":"DELETE_BLOCKED_ROUTE_ONLY_IF_ALL_ITS_FROZEN_BEHAVIORAL_OBLIGATIONS_HAVE_EQUAL_OR_STRONGER_ADMISSIBLE_SUPPORT",
        })

    global_uncovered=sorted(oid for oid,support in obligation_support.items() if not support)
    return {
        "schema":"BRAIN_PROOF_ROUTE_DOMINANCE_V1",
        "status":"COMPLETE" if not global_uncovered else "FAIL_CLOSED_UNCOVERED_OBLIGATIONS",
        "global_uncovered_obligations":global_uncovered,
        "obligation_support":{k:sorted(v) for k,v in sorted(obligation_support.items())},
        "blocked_route_verdicts":sorted(blocked_verdicts,key=lambda x:x["route_id"]),
        "admissible_routes":sorted(r["id"] for r in admissible_routes),
        "pending_terminal_result_routes":sorted(
            r["id"] for r in normalized
            if r["terminal_result_required"]
            and not (r["terminal_result_pass"] and r["terminal_result_receipt"] is not None)
        ),
        "principle":"BEHAVIORAL_OBLIGATIONS_ARE_TERMINAL_REQUIREMENTS__BENCHMARKS_ARE_REPLACEABLE_EVIDENCE_ROUTES_ONLY_WITH_EXPLICIT_NONWEAKENING_COVERAGE_PROOF",
    }
