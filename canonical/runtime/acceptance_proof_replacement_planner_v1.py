"""Fail-closed stronger-proof replacement planner for frozen acceptance predicates.

This planner does not invent benchmark equivalence, scope coverage, probabilities, or
acceptance credit. It composes existing independently-verified proof compilers to find
whether a candidate stronger witness already implies a frozen target, and otherwise
returns the smallest zero-reality attempt frontier in a fixed proof-precedence order.

It is planning-only. A passing candidate remains zero-credit until separately bound by
the canonical acceptance authority.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from canonical.runtime.proof_obligation_delta_compiler_v1 import compile_delta
from canonical.runtime.protocol_implication_scope_algebra_v2 import evaluate as evaluate_implication

INPUT_SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_PROOF_REPLACEMENT_PLANNER_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_PROOF_REPLACEMENT_PLANNER_OUTPUT_V1"

ROUTE_ORDER = (
    "FORMAL_IMPLICATION",
    "OBJECTIVE_CEILING",
    "EXHAUSTIVE_FINITE_UNIVERSE",
    "VERIFIED_SCOPE_SUPERSET",
    "METAMORPHIC_INVARIANT",
    "EXISTING_COMPARATOR_RECEIPT",
    "MATCHED_EMPIRICAL",
)
ROUTE_RANK = {name: i for i, name in enumerate(ROUTE_ORDER)}
HEX = set("0123456789abcdef")


def _sha40(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 40 and set(v.lower()) <= HEX


def _receipt(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v.get("path"))
        and _sha40(v.get("git_blob_sha"))
    )


def _seconds(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    if not isfinite(x) or x <= 0:
        return None
    return x


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "closure_candidates": [],
        "zero_reality_attempt_frontier": [],
        "blocked_fresh_reality_routes": [],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def _target_matches(target: Mapping[str, Any], mode: str, payload: Mapping[str, Any]) -> bool:
    ptarget = payload.get("target")
    if not isinstance(ptarget, Mapping):
        return False
    if mode == "DELTA":
        return ptarget.get("id") == target.get("id")
    if mode == "IMPLICATION":
        scope_ref = target.get("scope_ref")
        return isinstance(scope_ref, str) and bool(scope_ref) and ptarget.get("scope_ref") == scope_ref
    return False


def compile_replacement_frontier(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
        return _fail("SCHEMA_INVALID")

    target = doc.get("target")
    if not isinstance(target, Mapping):
        return _fail("TARGET_REQUIRED")
    target_id = target.get("id")
    if not isinstance(target_id, str) or not target_id:
        return _fail("TARGET_ID_REQUIRED")
    if not _receipt(target.get("receipt")):
        return _fail("TARGET_RECEIPT_NOT_CONTENT_ADDRESSED")

    allow_fresh = doc.get("allow_fresh_reality", False)
    if not isinstance(allow_fresh, bool):
        return _fail("ALLOW_FRESH_REALITY_INVALID")

    rows = doc.get("route_candidates")
    if not isinstance(rows, list):
        return _fail("ROUTE_CANDIDATES_INVALID")

    errors: list[str] = []
    seen: set[str] = set()
    closure_candidates: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    blocked_fresh: list[dict[str, Any]] = []

    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            errors.append(f"ROUTE_NOT_OBJECT:{i}")
            continue
        rid = raw.get("route_id")
        kind = raw.get("kind")
        mode = raw.get("mode", "UNPROVED")
        zero_reality = raw.get("zero_reality")
        seconds = _seconds(raw.get("critical_path_seconds"))

        if not isinstance(rid, str) or not rid:
            errors.append(f"ROUTE_ID_INVALID:{i}")
            continue
        if rid in seen:
            errors.append(f"ROUTE_ID_DUPLICATE:{rid}")
            continue
        seen.add(rid)

        if kind not in ROUTE_RANK:
            errors.append(f"ROUTE_KIND_INVALID:{rid}")
            continue
        if mode not in {"UNPROVED", "DELTA", "IMPLICATION"}:
            errors.append(f"ROUTE_MODE_INVALID:{rid}")
            continue
        if not isinstance(zero_reality, bool):
            errors.append(f"ROUTE_ZERO_REALITY_INVALID:{rid}")
            continue
        if seconds is None:
            errors.append(f"ROUTE_CRITICAL_PATH_SECONDS_INVALID:{rid}")
            continue

        base = {
            "route_id": rid,
            "kind": kind,
            "mode": mode,
            "zero_reality": zero_reality,
            "critical_path_seconds": seconds,
            "route_rank": ROUTE_RANK[kind],
        }

        if not zero_reality and not allow_fresh:
            blocked_fresh.append({**base, "status": "BLOCKED_FRESH_REALITY"})
            continue

        if mode == "UNPROVED":
            attempts.append({**base, "status": "ATTEMPT_REQUIRED"})
            continue

        payload = raw.get("payload")
        if not isinstance(payload, Mapping):
            errors.append(f"ROUTE_PAYLOAD_REQUIRED:{rid}")
            continue
        if not _target_matches(target, mode, payload):
            errors.append(f"ROUTE_TARGET_IDENTITY_MISMATCH:{rid}")
            continue

        if mode == "DELTA":
            verdict = compile_delta(payload)
            proved = verdict.get("pass") is True
            proof_status = verdict.get("status")
        else:
            verdict = evaluate_implication(payload)
            proved = verdict.get("implies_target") is True
            proof_status = verdict.get("status")

        if proved:
            closure_candidates.append({
                **base,
                "status": "PROVED_REPLACEMENT_CANDIDATE",
                "proof_status": proof_status,
                "proof_verdict": verdict,
            })
        else:
            attempts.append({
                **base,
                "status": "PROOF_ATTEMPT_RESIDUAL_OPEN",
                "proof_status": proof_status,
                "proof_verdict": verdict,
            })

    if errors:
        return _fail(*errors)

    closure_candidates.sort(
        key=lambda x: (x["route_rank"], x["critical_path_seconds"], x["route_id"])
    )
    attempts.sort(
        key=lambda x: (x["route_rank"], x["critical_path_seconds"], x["route_id"])
    )
    blocked_fresh.sort(
        key=lambda x: (x["route_rank"], x["critical_path_seconds"], x["route_id"])
    )

    if closure_candidates:
        status = "PROVED_REPLACEMENT_CANDIDATE_FOUND__ZERO_CREDIT"
    elif attempts:
        status = "ZERO_REALITY_PROOF_REPLACEMENT_FRONTIER_OPEN"
    else:
        status = "NO_ZERO_REALITY_REPLACEMENT_ROUTE_AVAILABLE"

    return {
        "schema": OUTPUT_SCHEMA,
        "status": status,
        "errors": [],
        "target_id": target_id,
        "target_receipt": dict(target["receipt"]),
        "closure_candidates": closure_candidates,
        "zero_reality_attempt_frontier": attempts,
        "blocked_fresh_reality_routes": blocked_fresh,
        "route_precedence": list(ROUTE_ORDER),
        "rule": (
            "NO_BENCHMARK_REPLACEMENT_BY_NAME_SIMILARITY_OR_PROSE__ONLY_EXISTING_FAIL_CLOSED_"
            "EXPLICIT_BINDINGS_OR_SCOPE_SAFE_IMPLICATION_MAY_PRODUCE_A_REPLACEMENT_CANDIDATE__"
            "PLANNER_OUTPUT_ITSELF_GRANTS_ZERO_ACCEPTANCE_CREDIT"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
