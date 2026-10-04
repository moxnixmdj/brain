"""Fail-closed stronger-proof route compiler for frozen acceptance predicates.

This is a zero-credit scheduler. It never invents semantic equivalence. A route is
admissible only when its exact content-addressed receipt plus explicit independent
verification proves scope and semantic/metric entailment of the frozen target.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_STRONGER_PROOF_ROUTE_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_STRONGER_PROOF_ROUTE_VERDICT_V1"
HEX = set("0123456789abcdef")

ROUTE_ORDER = {
    "EXACT_EXISTING_CONTENT_ADDRESSED_RECEIPT": 0,
    "OBJECTIVE_CEILING_OR_FLOOR": 1,
    "FORMAL_DOMINANCE_OR_EQUIVALENCE": 2,
    "GENUINELY_EXHAUSTIVE_FINITE_UNIVERSE": 3,
    "VERIFIED_SCOPE_COMPLETE_SUPERSET": 4,
    "VERIFIED_METAMORPHIC_OR_INVARIANT_PROOF": 5,
    "MATCHED_EMPIRICAL_COMPARISON": 6,
    "ACCOUNT_FACT": 7,
    "OWNER_RESULT": 8,
    "NEW_CUSTOM_BENCHMARK": 9,
}


def _sha40(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and set(v.lower()) <= HEX


def _receipt(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v.get("path"))
        and _sha40(v.get("git_blob_sha"))
    )


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "selected": {},
        "open_targets": [],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
    }


def _admissible(route: Mapping[str, Any]) -> tuple[bool, str]:
    kind = route.get("kind")
    if kind not in ROUTE_ORDER:
        return False, "UNKNOWN_ROUTE_KIND"
    if route.get("verified") is not True or route.get("independent") is not True:
        return False, "NOT_INDEPENDENTLY_VERIFIED"
    if not _receipt(route.get("receipt")):
        return False, "RECEIPT_NOT_CONTENT_ADDRESSED"

    if kind in {"ACCOUNT_FACT", "OWNER_RESULT"}:
        return False, "EVIDENCE_INPUT_NOT_REPLACEMENT_PROOF"

    if route.get("scope_relation") not in {"EXACT", "SUPERSET"}:
        return False, "SCOPE_NOT_EXACT_OR_SUPERSET"
    if route.get("semantic_entailment_verified") is not True:
        return False, "SEMANTIC_ENTAILMENT_UNPROVED"
    if route.get("metric_entailment_verified") is not True:
        return False, "METRIC_ENTAILMENT_UNPROVED"

    if kind == "NEW_CUSTOM_BENCHMARK" and route.get("external_dominance_saturated") is not True:
        return False, "CUSTOM_BENCHMARK_PREMATURE"

    return True, "ADMISSIBLE"


def compile_routes(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")
    targets = doc.get("targets")
    if not isinstance(targets, list) or not targets:
        return _fail("TARGETS_REQUIRED")

    selected: dict[str, Any] = {}
    open_targets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for i, target in enumerate(targets):
        if not isinstance(target, Mapping):
            return _fail(f"TARGET_NOT_OBJECT:{i}")
        pid = target.get("predicate_id")
        routes = target.get("routes")
        if not isinstance(pid, str) or not pid:
            return _fail(f"PREDICATE_ID_INVALID:{i}")
        if pid in seen:
            return _fail(f"PREDICATE_DUPLICATE:{pid}")
        seen.add(pid)
        if not isinstance(routes, list):
            return _fail(f"ROUTES_INVALID:{pid}")

        ranked: list[tuple[int, str, Mapping[str, Any]]] = []
        rejected: list[dict[str, Any]] = []
        for j, route in enumerate(routes):
            if not isinstance(route, Mapping):
                return _fail(f"ROUTE_NOT_OBJECT:{pid}:{j}")
            kind = route.get("kind")
            ok, reason = _admissible(route)
            if ok:
                ranked.append((ROUTE_ORDER[str(kind)], str(route.get("route_id") or j), route))
            else:
                rejected.append({
                    "route_id": route.get("route_id"),
                    "kind": kind,
                    "reason": reason,
                })

        if ranked:
            ranked.sort(key=lambda x: (x[0], x[1]))
            _, _, winner = ranked[0]
            selected[pid] = {
                "route_id": winner.get("route_id"),
                "kind": winner.get("kind"),
                "receipt": winner.get("receipt"),
                "rule": "FIRST_ADMISSIBLE_STRONGEST_ROUTE_BY_FROZEN_PRECEDENCE",
            }
        else:
            open_targets.append({
                "predicate_id": pid,
                "rejected_routes": sorted(
                    rejected,
                    key=lambda x: (ROUTE_ORDER.get(str(x.get("kind")), 999), str(x.get("route_id"))),
                ),
                "rule": "NO_REPLACEMENT_CREDIT__PRESERVE_FROZEN_PREDICATE",
            })

    return {
        "schema": VERDICT_SCHEMA,
        "status": "ADMISSIBLE_STRONGER_PROOF_ROUTES_FOUND" if selected else "NO_ADMISSIBLE_STRONGER_PROOF_ROUTE",
        "errors": [],
        "selected": selected,
        "open_targets": open_targets,
        "route_order": [k for k, _ in sorted(ROUTE_ORDER.items(), key=lambda kv: kv[1])],
        "hard_rule": "NAMES_PROSE_DIFFICULTY_CLAIMS_AND_FINITE_SAMPLE_SUCCESS_NEVER_ESTABLISH_REPLACEMENT",
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
    }
