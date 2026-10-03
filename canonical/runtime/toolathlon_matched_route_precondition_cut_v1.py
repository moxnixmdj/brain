from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "canonical/governance/TOOLATHLON_VERIFIED_TOOL_DISCOVERY_ROUTE_FREEZE_V1.json"
BINDINGS = ROOT / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
CUT = ROOT / "canonical/governance/TOOLATHLON_MATCHED_ROUTE_PRECONDITION_CUT_V1.json"

EXPECTED_ORIGINAL = [
    "MAP_TOOLATHLON_REPRESENTED_DIMENSIONS_TO_FROZEN_TOOL_DISCOVERY_CONTRACT_WITHOUT_SCOPE_WEAKENING",
    "PROVE_EXACT_ZERO_INCREMENTAL_SPEND_EXECUTION_CARRIER_OR_FAIL_CLOSED",
    "FREEZE_CHECKER_AND_TASK_POPULATION_IDENTITY_WITHOUT_POST_FREEZE_TUNING",
    "BIND_OPUS_5_5_77_8_PASS_AT_1_SOURCE_DURABLY_AND_INDEPENDENTLY",
    "DEFINE_HOW_INTERNAL_TRANSFER_VERSIONING_LEAST_COST_AND_ESCALATION_PROOFS_COMPOSE_WITH_TOOLATHLON_FIXED_BAR",
    "FREEZE_TERMINAL_ACCEPTANCE_ACCOUNTING_AND_SELECTOR",
]

REMAINING = [
    "TOOLATHLON_MATCHED_SCOPE_COMPOSITION_CERTIFICATE",
    "TOOLATHLON_ZERO_INCREMENTAL_SPEND_EXECUTION_CARRIER",
    "OPUS55_TOOLATHLON_MATCHED_REFERENCE_BAR",
]


def _load(path: Path) -> dict[str, Any]:
    x = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return x


def _claim(bindings: dict[str, Any], predicate_id: str) -> dict[str, Any] | None:
    for row in bindings.get("claims", []):
        if isinstance(row, dict) and row.get("predicate_id") == predicate_id:
            return row
    return None


def evaluate(
    *,
    freeze: dict[str, Any] | None = None,
    bindings: dict[str, Any] | None = None,
    cut: dict[str, Any] | None = None,
    remaining_pass: dict[str, bool] | None = None,
) -> dict[str, Any]:
    freeze = _load(FREEZE) if freeze is None else freeze
    bindings = _load(BINDINGS) if bindings is None else bindings
    cut = _load(CUT) if cut is None else cut
    remaining_pass = {} if remaining_pass is None else dict(remaining_pass)

    errors: list[str] = []

    if freeze.get("status", "").startswith("PRE_TASK_CONTENT_FREEZE") is False:
        errors.append("PRE_TASK_FREEZE_NOT_ACTIVE")
    if freeze.get("unresolved_before_public_fixed_bar_admission") != EXPECTED_ORIGINAL:
        errors.append("ORIGINAL_SIX_PRECONDITION_SET_DRIFT")

    ident = freeze.get("benchmark_identity") or {}
    presence = ident.get("task_file_presence") or {}
    checker_population_frozen = (
        ident.get("frozen_head_commit") == "9be8d8fe07a497b18ee61e3f2ae694e9797f39eb"
        and ident.get("finalpool_tree_sha") == "0e6db218108c4666f3cdaa8d1ab976ab4807617c"
        and ident.get("finalpool_task_directory_count") == 108
        and all(presence.get(k) == 108 for k in (
            "docs/agent_system_prompt.md",
            "docs/task.md",
            "evaluation/main.py",
            "task_config.json",
        ))
        and (freeze.get("contamination_state") or {}).get("brain_candidate_frozen_before_task_prompt_content") is True
        and (freeze.get("contamination_state") or {}).get("ground_truth_content_read_by_this_route_audit_before_freeze") is False
    )
    if not checker_population_frozen:
        errors.append("CHECKER_OR_TASK_POPULATION_FREEZE_NOT_PROVED")

    transfer = _claim(bindings, "TOOL_LEARNING_SECOND_TASK_TRANSFER")
    promotion = _claim(bindings, "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION")
    proved_atomic_inputs = (
        transfer is not None
        and transfer.get("state") == "PROVED"
        and transfer.get("scope_complete") is True
        and promotion is not None
        and promotion.get("state") == "PROVED"
        and promotion.get("scope_complete") is True
    )
    if not proved_atomic_inputs:
        errors.append("REQUIRED_EXISTING_TOOL_ATOMS_NOT_PROVED")

    candidate_ref = freeze.get("opus55_reference_bar") or {}
    legacy_reference_not_matched = (
        candidate_ref.get("benchmark") == "Toolathlon-Verified"
        and float(candidate_ref.get("pass_at_1_percent", -1)) == 77.8
        and "DURABLE_LOCAL_EVIDENCE_BINDING_STILL_REQUIRED"
        in str(candidate_ref.get("source_status") or "")
    )
    if not legacy_reference_not_matched:
        errors.append("LEGACY_REFERENCE_CANDIDATE_STATE_DRIFT")

    selector = cut.get("terminal_selector") or {}
    required_selector = [x + "__INDEPENDENT_PASS" for x in REMAINING]
    selector_frozen = (
        selector.get("matched_route_execution_authorized_when") == required_selector
        and selector.get("otherwise") == "FAIL_CLOSED__NO_MATCHED_TARGET_EXECUTION"
        and "NO_SCOPE_THRESHOLD_HARNESS_TOOL_AUTHORITY_METRIC_SELECTOR_OR_REFERENCE_ADJUSTMENT_AFTER_ANY_TERMINAL_RESULT_IS_OBSERVED"
        == selector.get("post_result_rule")
    )
    if not selector_frozen:
        errors.append("TERMINAL_SELECTOR_NOT_FAIL_CLOSED_OR_NOT_FROZEN")

    all_remaining_pass = all(remaining_pass.get(x) is True for x in REMAINING)
    execution_authorized = not errors and all_remaining_pass

    return {
        "schema": "PROJECT_BRAIN_TOOLATHLON_MATCHED_ROUTE_PRECONDITION_CUT_VERDICT_V1",
        "status": (
            "PASS__SIX_TO_THREE_RESIDUAL_FACTORIZATION__REFERENCE_HARNESS_TRUTH_REPAIRED__ZERO_REALITY__ZERO_CREDIT"
            if not errors else "FAIL_CLOSED__PRECONDITION_CUT_INVALID"
        ),
        "errors": errors,
        "original_open_preconditions": 6,
        "checker_and_task_population_frozen": checker_population_frozen,
        "proved_existing_atomic_inputs": proved_atomic_inputs,
        "legacy_77_8_candidate_is_not_a_matched_reference": legacy_reference_not_matched,
        "terminal_selector_frozen": selector_frozen,
        "closed_zero_reality_count": 2 if not errors else 0,
        "absorbed_original_precondition_count": 2 if not errors else 0,
        "minimum_remaining_facts": REMAINING,
        "minimum_remaining_fact_count": 3 if not errors else None,
        "terminal_execution_authorized": execution_authorized,
        "terminal_goal_achieved": False,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "terminal_results_observed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": execution_authorized,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
