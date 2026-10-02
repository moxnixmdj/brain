"""Deterministic reducer for the exact four-portfolio terminal prequalification.

The reducer never grants capability credit. It only decides whether the frozen
terminal wave may begin, from explicit pre-wave facts already present in the
canonical prequalification manifest. Unknown, missing, or contradictory state
fails closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PREQUAL = "canonical/governance/EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json"

_REQUIRED_TRUE_PROGRESS = (
    "exact_cut_current_and_verified",
    "zero_open_specification_holes",
    "zero_preproof_implementation_residuals",
    "shared_one_shot_contamination_oracle_mutation_protocol_frozen",
    "public_evaluation_route_matrix_frozen",
)

_REQUIRED_CLOSED_PROGRESS = (
    "brain_route_and_dependency_manifest_frozen",
    "no_known_opaque_target_capability_provider_in_operative_brain_route",
    "no_known_unresolved_composition_defect_before_wave",
)

_EXPECTED_PORTFOLIOS = (
    "T0_CODING_SEMANTIC_GEOMETRY_PORTFOLIO",
    "T1_PROFESSIONAL_FINANCE_ARTIFACT_SYNTHESIS_VISION_PORTFOLIO",
    "T2_INTERACTIVE_AGENCY_RECOVERY_SCOPE_DELEGATION_COMPOSITION_PORTFOLIO",
    "T3_RESEARCH_UNKNOWN_DOMAIN_PORTFOLIO",
)


def _load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("PREQUALIFICATION_NOT_OBJECT")
    return value


def _closed_marker(value: Any) -> bool:
    if value is True:
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    upper = value.upper()
    if any(token in upper for token in ("PENDING", "REQUIRED", "OPEN", "UNKNOWN", "FAIL_CLOSED")):
        return False
    return any(token in upper for token in ("PASS", "FROZEN", "BOUND", "VERIFIED", "CLOSED", "CANONICAL/"))


def evaluate(root: Path) -> dict[str, Any]:
    p = _load(root, PREQUAL)
    failures: list[str] = []

    if p.get("schema") != "PROJECT_BRAIN_EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1":
        failures.append("SCHEMA")

    core = p.get("core_deduction") or {}
    if core.get("preproof_implementation_residual_count") != 0:
        failures.append("PREPROOF_IMPLEMENTATION_RESIDUALS")
    if core.get("consequence") != "NO_NEW_GENERIC_MECHANISM_WORK_BEFORE_TERMINAL_WAVE":
        failures.append("PREPROOF_SCHEDULING_AUTHORITY")

    progress = p.get("prequalification_progress") or {}
    for key in _REQUIRED_TRUE_PROGRESS:
        if progress.get(key) is not True:
            failures.append("PROGRESS:" + key)
    for key in _REQUIRED_CLOSED_PROGRESS:
        if not _closed_marker(progress.get(key)):
            failures.append("PROGRESS:" + key)

    portfolios = p.get("portfolio_status")
    if not isinstance(portfolios, dict):
        failures.append("PORTFOLIO_STATUS")
        portfolios = {}

    unknown = sorted(set(portfolios) - set(_EXPECTED_PORTFOLIOS))
    missing = sorted(set(_EXPECTED_PORTFOLIOS) - set(portfolios))
    if unknown:
        failures.append("UNKNOWN_PORTFOLIOS:" + ",".join(unknown))
    if missing:
        failures.append("MISSING_PORTFOLIOS:" + ",".join(missing))

    blocker_map: dict[str, list[str]] = {}
    for pid in _EXPECTED_PORTFOLIOS:
        row = portfolios.get(pid)
        if not isinstance(row, dict):
            continue
        blockers = row.get("blockers")
        if blockers is None:
            blockers = []
        if not isinstance(blockers, list) or any(not isinstance(x, str) or not x.strip() for x in blockers):
            failures.append("INVALID_BLOCKERS:" + pid)
            continue
        blocker_map[pid] = blockers
        if blockers:
            failures.append("PORTFOLIO_BLOCKED:" + pid)

    remaining = p.get("remaining_irreducible_prequalification_blockers")
    if remaining is None:
        remaining = []
    if not isinstance(remaining, list):
        failures.append("REMAINING_BLOCKERS_INVALID")
    elif remaining:
        failures.append("REMAINING_BLOCKERS_NONZERO")

    # These become true only when every public/scope-equivalent route and every
    # oracle/harness/stop/dependency binding has actually been frozen.
    for key in (
        "every_surface_zero_cost_route_frozen",
        "every_surface_oracle_and_verifier_binding_frozen",
        "every_portfolio_task_case_harness_metric_stop_rule_and_mutation_set_frozen",
    ):
        if progress.get(key) is not True:
            failures.append("PROGRESS:" + key)

    independence = progress.get("four_portfolios_pairwise_execution_independent")
    if not _closed_marker(independence):
        failures.append("PROGRESS:four_portfolios_pairwise_execution_independent")

    failures = sorted(set(failures))
    passed = not failures
    return {
        "schema": "PROJECT_BRAIN_EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_VERDICT_V1",
        "pass": passed,
        "execution_authority": passed,
        "authorization": "T0_T1_T2_T3_PARALLEL_TERMINAL_WAVE" if passed else "NONE",
        "failed_predicates": failures,
        "portfolio_blockers": blocker_map,
        "rule": "UNKNOWN_MISSING_OR_CONTRADICTORY_PREWAVE_STATE_FAILS_CLOSED__ZERO_CAPABILITY_CREDIT",
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", type=Path)
    args = ap.parse_args()
    out = evaluate(args.repo_root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
