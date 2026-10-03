from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FREEZE = ROOT / "canonical/governance/TOOLATHLON_VERIFIED_TOOL_DISCOVERY_ROUTE_FREEZE_V1.json"
INTERNAL = ROOT / "canonical/verification/TOOL_DISCOVERY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
PROTOCOLS = ROOT / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REDUCTION = ROOT / "canonical/governance/TOOL_DISCOVERY_MATCHED_ROUTE_PRECONDITION_REDUCTION_V1.json"

REQUIRED_INTERNAL = {
    "TRUE_TOOL_CAPABILITIES_HIDDEN_FROM_CANDIDATE",
    "SAFE_PROBES_RESTRICTED_TO_CURRENT_REQUIRED_CAPABILITIES",
    "LEAST_COST_EVIDENCE_SUPPORTED_SUFFICIENT_ROUTE_SELECTED",
    "VALID_PRIOR_CAPABILITY_EVIDENCE_REUSED_ON_LATER_TASK",
    "TARGETED_VERSION_CHANGE_INVALIDATES_STALE_EVIDENCE",
    "UNAVAILABLE_CHEAPER_ROUTE_EXCLUDED",
    "UNAUTHORIZED_CHEAPER_ROUTE_EXCLUDED",
    "NO_SUFFICIENT_ROUTE_ESCALATES_ONLY_AFTER_RELEVANT_NEGATIVE_EVIDENCE",
    "PREMATURE_ESCALATION_REJECTED",
}

CLOSED_PRECONDITIONS = {
    "FREEZE_CHECKER_AND_TASK_POPULATION_IDENTITY_WITHOUT_POST_FREEZE_TUNING",
    "DEFINE_HOW_INTERNAL_TRANSFER_VERSIONING_LEAST_COST_AND_ESCALATION_PROOFS_COMPOSE_WITH_TOOLATHLON_FIXED_BAR",
    "FREEZE_TERMINAL_ACCEPTANCE_ACCOUNTING_AND_SELECTOR",
}

REMAINING = {
    "MAP_TOOLATHLON_REPRESENTED_DIMENSIONS_TO_FROZEN_TOOL_DISCOVERY_CONTRACT_WITHOUT_SCOPE_WEAKENING",
    "PROVE_EXACT_ZERO_INCREMENTAL_SPEND_EXECUTION_CARRIER_OR_FAIL_CLOSED",
    "BIND_OPUS_5_5_77_8_PASS_AT_1_SOURCE_DURABLY_AND_INDEPENDENTLY",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_protocol(protocols: Any) -> dict[str, Any] | None:
    if isinstance(protocols, dict):
        if protocols.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING":
            return protocols
        for value in protocols.values():
            found = _tool_protocol(value)
            if found:
                return found
    elif isinstance(protocols, list):
        for value in protocols:
            found = _tool_protocol(value)
            if found:
                return found
    return None


def evaluate(
    freeze: dict[str, Any] | None = None,
    internal: dict[str, Any] | None = None,
    protocols: Any | None = None,
    reduction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    freeze = _load(FREEZE) if freeze is None else freeze
    internal = _load(INTERNAL) if internal is None else internal
    protocols = _load(PROTOCOLS) if protocols is None else protocols
    reduction = _load(REDUCTION) if reduction is None else reduction

    errors: list[str] = []

    unresolved = set(freeze.get("unresolved_before_public_fixed_bar_admission") or [])
    if not CLOSED_PRECONDITIONS.issubset(unresolved):
        errors.append("REDUCTION_DOES_NOT_TARGET_EXISTING_OPEN_PRECONDITIONS")

    benchmark = freeze.get("benchmark_identity") or {}
    presence = benchmark.get("task_file_presence") or {}
    contamination = freeze.get("contamination_state") or {}
    tree_freeze_proved = (
        freeze.get("freeze_order_position")
        == "BRAIN_CANDIDATE_FROZEN_BEFORE_ANY_TOOLATHLON_TASK_PROMPT_OR_GROUND_TRUTH_CONTENT_IS_READ"
        and bool(benchmark.get("frozen_head_commit"))
        and bool(benchmark.get("finalpool_tree_sha"))
        and benchmark.get("finalpool_task_directory_count") == 108
        and all(
            presence.get(path) == 108
            for path in ("docs/task.md", "evaluation/main.py", "task_config.json")
        )
        and contamination.get("task_prompt_content_read_by_this_route_audit_before_freeze") is False
        and contamination.get("ground_truth_content_read_by_this_route_audit_before_freeze") is False
    )
    if not tree_freeze_proved:
        errors.append("CONTENT_ADDRESSED_TASK_CHECKER_FREEZE_NOT_PROVED")

    verified_internal = set(internal.get("verified") or [])
    internal_composition_basis_proved = (
        internal.get("workflow_conclusion") == "success"
        and REQUIRED_INTERNAL.issubset(verified_internal)
    )
    if not internal_composition_basis_proved:
        errors.append("INDEPENDENT_INTERNAL_COMPOSITION_BASIS_NOT_PROVED")

    protocol = _tool_protocol(protocols) or {}
    acceptance = str(protocol.get("acceptance") or "")
    matched_protocol_bound = (
        "Opus matched bounds" in acceptance
        and "second-task transfer" in acceptance
        and "no unsupported capability-state promotion" in acceptance
    )
    if not matched_protocol_bound:
        errors.append("FROZEN_MATCHED_PROTOCOL_NOT_BOUND")

    reductions = {
        row.get("prior_open_precondition"): row
        for row in reduction.get("reductions") or []
        if isinstance(row, dict)
    }
    if set(reductions) != CLOSED_PRECONDITIONS:
        errors.append("REDUCTION_SET_NOT_EXACT")

    selector_row = reductions.get("FREEZE_TERMINAL_ACCEPTANCE_ACCOUNTING_AND_SELECTOR") or {}
    selector = selector_row.get("selector") or {}
    accounting = selector_row.get("accounting") or {}
    threshold = int(accounting.get("minimum_integer_brain_passes_to_meet_or_exceed_reported_bar", -1))
    bar = float(accounting.get("reported_opus55_pass_at_1_percent_from_existing_freeze", -1.0))
    denominator = int(selector.get("denominator", -1))
    selector_accounting_proved = (
        selector.get("task_population") == "ALL_108_FROZEN_TOOLATHLON_VERIFIED_TASK_DIRECTORIES"
        and selector.get("adaptive_task_selection") is False
        and selector.get("task_replacement") is False
        and selector.get("post_result_tuning") is False
        and selector.get("pass_at_1_attempts_per_task") == 1
        and denominator == 108
        and threshold == 85
        and (threshold / denominator * 100.0) >= bar
        and ((threshold - 1) / denominator * 100.0) < bar
    )
    if not selector_accounting_proved:
        errors.append("FULL_POPULATION_SELECTOR_OR_MINIMUM_THRESHOLD_NOT_PROVED")

    remaining = set(reduction.get("remaining_route_preconditions_after_this_candidate_if_independently_verified") or [])
    if remaining != REMAINING:
        errors.append("REMAINING_PRECONDITION_SET_NOT_EXACT")

    zero_credit = (
        reduction.get("new_reality_units_consumed") == 0
        and reduction.get("capability_credit_delta") == 0
        and reduction.get("family_credit_delta") == 0
        and reduction.get("execution_authority") is False
        and reduction.get("promotion_authority") is False
    )
    if not zero_credit:
        errors.append("ZERO_CREDIT_FIREWALL_VIOLATED")

    proved = not errors
    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_MATCHED_ROUTE_PRECONDITION_REDUCTION_VERDICT_V1",
        "precondition_reduction_proved": proved,
        "tree_checker_population_freeze_proved": tree_freeze_proved,
        "internal_composition_basis_proved": internal_composition_basis_proved,
        "fixed_full_population_selector_accounting_proved": selector_accounting_proved,
        "closed_precondition_count": 3 if proved else 0,
        "closed_preconditions": sorted(CLOSED_PRECONDITIONS) if proved else [],
        "remaining_precondition_count": 3 if proved else 6,
        "remaining_preconditions": sorted(REMAINING) if proved else sorted(unresolved),
        "toolathlon_result_observed": False,
        "tool_discovery_acceptance_granted": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": errors,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["precondition_reduction_proved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
