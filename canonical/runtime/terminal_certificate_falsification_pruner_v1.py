"""Fail-closed pruning of independently falsified terminal certificate routes.

A falsified certificate route is not a falsified target predicate. This layer removes
only the impossible certificate from executable scheduling, leaves every target open,
and recomputes the exact certificate cut. It grants no acceptance or capability credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.terminal_certificate_cut_v1 import evaluate as evaluate_cut
from canonical.runtime.canonical_proof_atom_basis_v2 import compile_basis

SCHEMA = "PROJECT_BRAIN_TERMINAL_CERTIFICATE_FALSIFICATION_PRUNER_V1"
ROOT = Path(__file__).resolve().parents[2]


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "pruned_certificate_ids": [],
        "uncovered_predicates_after_pruning": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _valid_sha(v: Any) -> bool:
    return (
        isinstance(v, str)
        and len(v) == 40
        and all(ch in "0123456789abcdef" for ch in v.lower())
    )


def apply_falsification_overlay(
    global_frontier: Mapping[str, Any],
    overlay: Mapping[str, Any],
    *,
    refinement_overlay: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(global_frontier, Mapping):
        return _fail("GLOBAL_FRONTIER_NOT_OBJECT")
    unresolved = global_frontier.get("unresolved_predicates")
    certs = global_frontier.get("certificates")
    if not isinstance(unresolved, list) or not unresolved or len(unresolved) != len(set(unresolved)):
        return _fail("GLOBAL_UNRESOLVED_INVALID")
    if not isinstance(certs, list) or not certs:
        return _fail("GLOBAL_CERTIFICATES_INVALID")

    routes = overlay.get("falsified_certificate_routes") if isinstance(overlay, Mapping) else None
    if not isinstance(routes, list) or not routes:
        return _fail("FALSIFICATION_ROUTES_REQUIRED")

    by_id: dict[str, Mapping[str, Any]] = {}
    for cert in certs:
        if not isinstance(cert, Mapping) or not isinstance(cert.get("id"), str):
            return _fail("GLOBAL_CERTIFICATE_INVALID")
        cid = cert["id"]
        if cid in by_id:
            return _fail("GLOBAL_CERTIFICATE_ID_DUPLICATE")
        by_id[cid] = cert

    pruned: list[dict[str, Any]] = []
    pruned_ids: set[str] = set()
    for i, route in enumerate(routes):
        if not isinstance(route, Mapping):
            return _fail(f"FALSIFICATION_ROUTE_{i}_INVALID")
        cid = route.get("certificate_id")
        req = route.get("falsified_requirement")
        targets = route.get("target_predicates")
        receipt = route.get("independent_verification_receipt")
        receipt_sha = route.get("independent_verification_receipt_git_blob_sha")

        if route.get("independent_verified") is not True:
            return _fail(f"INDEPENDENT_VERIFICATION_REQUIRED:{cid}")
        if route.get("target_predicate_falsified") is not False:
            return _fail(f"TARGET_FALSIFICATION_MUST_BE_FALSE:{cid}")
        if route.get("adjudication") != "ROUTE_FALSIFIED_TARGET_REMAINS_OPEN":
            return _fail(f"ADJUDICATION_INVALID:{cid}")
        if not isinstance(cid, str) or cid not in by_id or cid in pruned_ids:
            return _fail("FALSIFIED_CERTIFICATE_ID_INVALID_OR_DUPLICATE")
        if not isinstance(req, str) or not req:
            return _fail(f"FALSIFIED_REQUIREMENT_INVALID:{cid}")
        if not isinstance(targets, list) or not targets or len(targets) != len(set(targets)):
            return _fail(f"FALSIFIED_TARGETS_INVALID:{cid}")
        if not isinstance(receipt, str) or not receipt or not _valid_sha(receipt_sha):
            return _fail(f"VERIFICATION_RECEIPT_BINDING_INVALID:{cid}")

        cert = by_id[cid]
        cert_targets = cert.get("target_predicates")
        cert_requires = cert.get("requires")
        if targets != cert_targets:
            return _fail(f"FALSIFICATION_TARGETS_DO_NOT_EXACTLY_MATCH_CERTIFICATE:{cid}")
        if not isinstance(cert_requires, list) or req not in cert_requires:
            return _fail(f"FALSIFIED_REQUIREMENT_NOT_IN_CERTIFICATE:{cid}")

        pruned_ids.add(cid)
        pruned.append({
            "certificate_id": cid,
            "falsified_requirement": req,
            "target_predicates": list(targets),
            "independent_verification_receipt": receipt,
            "independent_verification_receipt_git_blob_sha": receipt_sha,
            "target_predicate_falsified": False,
        })

    filtered = dict(global_frontier)
    filtered["certificates"] = [c for c in certs if c["id"] not in pruned_ids]
    filtered["status"] = "DERIVED__INDEPENDENTLY_FALSIFIED_CERTIFICATE_ROUTES_PRUNED__TARGETS_REMAIN_OPEN__ZERO_CREDIT"

    cut = evaluate_cut(filtered)
    if cut.get("status") != "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED":
        return _fail("FILTERED_TERMINAL_CUT_NOT_COMPUTABLE")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS__INDEPENDENTLY_FALSIFIED_ROUTES_PRUNED__TARGETS_REMAIN_OPEN__ZERO_CREDIT",
        "errors": [],
        "input_unresolved_predicate_count": len(unresolved),
        "input_certificate_count": len(certs),
        "active_certificate_count": len(filtered["certificates"]),
        "pruned_certificate_count": len(pruned),
        "pruned_certificate_ids": sorted(pruned_ids),
        "pruned_routes": sorted(pruned, key=lambda x: x["certificate_id"]),
        "covered_predicate_count_after_pruning": cut["covered_predicate_count"],
        "uncovered_predicates_after_pruning": cut["uncovered_predicates"],
        "selected_certificate_ids_after_pruning": cut["selected_certificates"],
        "filtered_frontier": filtered,
        "rule": (
            "FALSIFIED_CERTIFICATE_ROUTE_IS_REMOVED_FROM_EXECUTABLE_CUT__"
            "TARGET_PREDICATE_REMAINS_OPEN__"
            "NO_ROUTE_FALSIFICATION_MAY_BE_PROMOTED_TO_TARGET_FALSIFICATION__"
            "ONLY_EXACT_CERTIFICATE_TARGET_AND_REQUIREMENT_BINDINGS_ARE_CONSUMED"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

    if refinement_overlay is not None:
        basis = compile_basis(filtered, refinement_overlay)
        if not str(basis.get("status", "")).startswith("PASS"):
            return _fail("FILTERED_PROOF_ATOM_BASIS_NOT_PASS")
        out["executable_leaf_atom_count_after_pruning"] = basis["leaf_atom_count"]
        out["executable_leaf_requirement_occurrence_count_after_pruning"] = basis[
            "leaf_requirement_occurrence_count"
        ]
        out["executable_atom_ids_after_pruning"] = [x["atom_id"] for x in basis["atoms"]]

    return out


def main() -> int:
    frontier = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text(
            encoding="utf-8"
        )
    )
    overlay = json.loads(
        (ROOT / "canonical/governance/TERMINAL_CERTIFICATE_FALSIFICATION_OVERLAY_V1.json").read_text(
            encoding="utf-8"
        )
    )
    refinement = json.loads(
        (ROOT / "canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json").read_text(
            encoding="utf-8"
        )
    )
    out = apply_falsification_overlay(frontier, overlay, refinement_overlay=refinement)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
