"""Fail-closed zero-reality recompile after verified Tool Discovery acceptance.

This module recomputes the current atomic acceptance IR and exact minimum action
cut from the content-addressed 5-of-19 / 12-of-38 state. It creates no evidence,
spends no fresh reality, and grants no acceptance, family, ownership, execution,
or promotion credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.acceptance_ir_compiler_v1 import compile_ir
from canonical.runtime.minimum_terminal_cut_solver_v1 import evaluate as solve_cut

ROOT = Path(__file__).resolve().parents[2]

INPUTS = {
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":
        "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
        "e5888b0f03ddd3a7fbfdfd74d11b4680abc9f0dd",
    "canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json":
        "38b53147597b5457859e3b0d031168842560e3e2",
    "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":
        "2fe5d35d62f264de0661860afb8f2192fc87801b",
}

EXPECTED_SELECTED_ACTIONS = [
    "BIND_CHARTOGRAPHY_PUBLIC_BAR_ROUTE",
    "BIND_FINANCE_ACCOUNTING_INDEX_PUBLIC_ROUTE",
    "BIND_GDPVAL_PUBLIC_ROUTE",
    "BIND_OSWORLD_COMPARABLE_PUBLIC_ROUTE",
    "BIND_SHARED_PUBLIC_BENCHMARK_EXECUTION_ABI",
    "BUILD_AA_BRIEFCASE_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
    "BUILD_CODING_DELETED_PRIVATE_BAR_STRONGER_PROOFS",
    "BUILD_FINANCE_AGENT_V2_DELETED_PRIVATE_BAR_STRONGER_PROOF",
    "BUILD_MYSTERYMECHANISM_DELETED_PRIVATE_BAR_STRONGER_PROOF",
    "INTERNALIZE_FINANCE_JUDGMENT_ROUTE",
    "INTERNALIZE_UNKNOWN_DOMAIN_JUDGMENT_ROUTE",
    "RAISE_TB4_ATTAINABILITY_UPPER_BOUND_WITHOUT_CASE_EXPOSURE",
    "RESOLVE_HLE_PUBLIC_BAR_ROUTE_OR_SCOPE_COMPLETE_REPLACEMENT",
    "RUN_COMPOSITION_COMPONENT_PROOF_SLICER",
    "SEARCH_SCOPE_COMPLETE_STRONGER_PROOFS_FOR_MATCHED_RESIDUAL",
]


def _blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def evaluate() -> dict[str, Any]:
    drift = {
        rel: {"expected": expected, "actual": _blob_sha(rel)}
        for rel, expected in INPUTS.items()
        if _blob_sha(rel) != expected
    }
    if drift:
        return {
            "schema": "PROJECT_BRAIN_POST_TOOL_DISCOVERY_ZERO_REALITY_RECOMPILE_V1",
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT__ZERO_CREDIT",
            "source_blob_drift": drift,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    root_state = _load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
    current = root_state.get("current_acceptance") or {}
    root_ok = (
        current.get("accepted_families") == 5
        and current.get("open_families") == 14
        and current.get("proved_atomic") == 12
        and current.get("unresolved_atomic") == 26
        and current.get("total_atomic") == 38
        and current.get("terminal") is False
    )
    if not root_ok:
        return {
            "schema": "PROJECT_BRAIN_POST_TOOL_DISCOVERY_ZERO_REALITY_RECOMPILE_V1",
            "status": "FAIL_CLOSED__ROOT_STATE_MISMATCH__ZERO_CREDIT",
            "source_blob_drift": {},
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    ir = compile_ir(
        _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        _load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
    )
    cut = solve_cut(ir)

    selected = cut.get("selected_actions", [])
    exact = (
        ir.get("predicate_count") == 38
        and ir.get("proved_predicate_count") == 12
        and ir.get("unresolved_predicate_count") == 26
        and cut.get("unresolved_predicate_count") == 26
        and cut.get("available_action_count") == 17
        and cut.get("covered_predicate_count") == 26
        and cut.get("uncovered_predicates") == []
        and cut.get("selected_new_reality_units") == 0
        and selected == EXPECTED_SELECTED_ACTIONS
        and "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" not in selected
    )

    return {
        "schema": "PROJECT_BRAIN_POST_TOOL_DISCOVERY_ZERO_REALITY_RECOMPILE_V1",
        "status": (
            "PASS__5_OF_19__12_OF_38__26_UNRESOLVED__ALL_COVERED__"
            "15_ACTION_ZERO_REALITY_CUT__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
            if exact else
            "FAIL_CLOSED__CURRENT_RECOMPILE_MISMATCH__ZERO_CREDIT"
        ),
        "source_blob_drift": {},
        "current_acceptance": {
            "accepted_families": 5,
            "open_families": 14,
            "proved_atomic": ir.get("proved_predicate_count"),
            "unresolved_atomic": ir.get("unresolved_predicate_count"),
        },
        "cut": {
            "available_action_count": cut.get("available_action_count"),
            "selected_action_count": cut.get("selected_action_count"),
            "selected_actions": selected,
            "covered_predicate_count": cut.get("covered_predicate_count"),
            "uncovered_predicates": cut.get("uncovered_predicates"),
            "blocked_preconditions": cut.get("blocked_preconditions"),
            "selected_new_reality_units": cut.get("selected_new_reality_units"),
        },
        "tool_discovery_replay_removed": (
            "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" not in selected
        ),
        "next_rule": (
            "EXECUTE_ONLY_NONDOMINATED_ZERO_REALITY_RESIDUALS_FROM_THIS_CURRENT_CUT__"
            "RECOMPUTE_AFTER_EACH_VERIFIED_DELTA__NO_FRESH_REALITY_WHILE_ZERO_REALITY_ADVANCES_EXIST"
        ),
        "hard_nonclaims": [
            "NO_NEW_ACCEPTANCE_PROOF_CREATED",
            "NO_FAMILY_OR_OWNERSHIP_CREDIT",
            "NO_BENCHMARK_EXECUTION_AUTHORITY",
            "NO_FRESH_REALITY_AUTHORITY",
            "NO_STALE_V13_SCHEDULER_REUSE",
        ],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
