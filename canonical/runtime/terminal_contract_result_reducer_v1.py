"""Normalize one completed terminal wave into exactly 12 behavioral contract verdicts.

This reducer does not grant capability or family credit. It revalidates the
load-bearing parent instrumentation, checks direct-route evidence, deduplicates
the CAD overlap, and emits a stable contract-verdict set for downstream family
adjudication. A valid negative terminal outcome is preserved as FAIL; malformed
or incomplete evidence fails closed.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import cad_t0_route_specific_terminal_executor_v1 as cad
from canonical.runtime import direct_route_terminal_executors_v1 as direct
from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex
from canonical.runtime import terminal_parent_portfolio_launcher_v1 as launcher

SCHEMA = "PROJECT_BRAIN_TERMINAL_CONTRACT_RESULT_REDUCER_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_TERMINAL_CONTRACT_VERDICT_SET_V1"

DIRECT_IDS = frozenset(set(direct.bound_behavior_ids()) | {cad.BEHAVIOR_ID})
MULTIPLEX_IDS = frozenset(multiplex.bound_behavior_ids())
ACTIVE_IDS = frozenset(DIRECT_IDS | MULTIPLEX_IDS)
OVERLAP_IDS = frozenset(DIRECT_IDS & MULTIPLEX_IDS)

if len(ACTIVE_IDS) != 12 or OVERLAP_IDS != {cad.BEHAVIOR_ID}:
    raise RuntimeError("TERMINAL_ROUTE_ALGEBRA_DRIFT")


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED_INVALID_TERMINAL_EVIDENCE",
        "valid": False,
        "all_contracts_pass": False,
        "contract_verdicts": {},
        "errors": sorted(set(errors)),
        "contract_count": 0,
        "terminal_result": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def reduce_wave(
    wave: Mapping[str, Any],
    *,
    commitment: str,
    beacon: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(wave, Mapping):
        return _fail(["WAVE_NOT_MAPPING"])
    if not isinstance(commitment, str) or not commitment:
        return _fail(["COMMITMENT_REQUIRED"])
    if not isinstance(beacon, str) or not beacon:
        return _fail(["BEACON_REQUIRED"])

    if wave.get("terminal_result") is not True:
        errors.append("WAVE_NOT_TERMINAL_RESULT")
    if wave.get("no_case_replacement") is not True:
        errors.append("CASE_REPLACEMENT_GUARD_MISSING")
    if wave.get("no_tuning_replay") is not True:
        errors.append("TUNING_REPLAY_GUARD_MISSING")
    if wave.get("result_to_runtime_feedback_during_wave") is not False:
        errors.append("RUNTIME_FEEDBACK_GUARD_MISSING")
    if wave.get("shared_direct_route_duplicate_execution_count") != 0:
        errors.append("DUPLICATE_DIRECT_ROUTE_EXECUTION")

    direct_results = wave.get("direct_results")
    if not isinstance(direct_results, Mapping):
        errors.append("DIRECT_RESULTS_NOT_MAPPING")
        direct_results = {}
    if set(direct_results) != set(DIRECT_IDS):
        errors.append(
            "DIRECT_RESULT_SET_MISMATCH:missing="
            + ",".join(sorted(set(DIRECT_IDS) - set(direct_results)))
            + ";extra="
            + ",".join(sorted(set(direct_results) - set(DIRECT_IDS)))
        )

    executed_once = wave.get("direct_routes_executed_once")
    if not isinstance(executed_once, list) or set(executed_once) != set(DIRECT_IDS):
        errors.append("DIRECT_EXECUTED_ONCE_SET_MISMATCH")

    parent_receipts = wave.get("parent_portfolio_receipts")
    if not isinstance(parent_receipts, Mapping):
        errors.append("PARENT_RECEIPTS_NOT_MAPPING")
        parent_receipts = {}
        parent_rederived = None
    else:
        parent_rederived = launcher.validate_parent_receipts(
            parent_receipts, commitment=commitment, beacon=beacon
        )
        # A valid terminal wave may contain a legitimate behavioral failure.
        # validate_parent_receipts reports FAIL_CLOSED for such a negative
        # outcome, so only structural receipt errors make the set invalid here.
        structural = [
            e for e in parent_rederived.get("errors", [])
            if not str(e).startswith("MULTIPLEX_REDUCTION_FAIL:")
        ]
        if structural:
            errors.extend("PARENT_REVALIDATION:" + str(e) for e in structural)

    verdicts: dict[str, dict[str, Any]] = {}

    for behavior_id in sorted(ACTIVE_IDS):
        sources: list[str] = []
        source_passes: list[bool] = []
        source_terminal: list[bool] = []

        if behavior_id in DIRECT_IDS:
            row = direct_results.get(behavior_id)
            if not isinstance(row, Mapping):
                errors.append("DIRECT_RESULT_INVALID:" + behavior_id)
            else:
                if row.get("behavior_id") != behavior_id:
                    errors.append("DIRECT_BEHAVIOR_ID_MISMATCH:" + behavior_id)
                p = row.get("pass")
                t = row.get("terminal_result")
                if p not in (True, False):
                    errors.append("DIRECT_PASS_VERDICT_MISSING:" + behavior_id)
                if t is not True:
                    errors.append("DIRECT_TERMINAL_RESULT_MISSING:" + behavior_id)
                if p in (True, False):
                    sources.append("DIRECT")
                    source_passes.append(bool(p))
                    source_terminal.append(t is True)

        if behavior_id in MULTIPLEX_IDS:
            red = (
                parent_rederived.get("reductions", {}).get(behavior_id)
                if isinstance(parent_rederived, Mapping)
                else None
            )
            if not isinstance(red, Mapping):
                errors.append("MULTIPLEX_REDUCTION_MISSING:" + behavior_id)
            else:
                if red.get("behavior_id") != behavior_id:
                    errors.append("MULTIPLEX_BEHAVIOR_ID_MISMATCH:" + behavior_id)
                receipt_count = red.get("receipt_count")
                load_count = red.get("load_bearing_receipt_count")
                invalid_count = red.get("invalid_receipt_count")
                if not isinstance(receipt_count, int) or receipt_count <= 0:
                    errors.append("MULTIPLEX_RECEIPTS_MISSING:" + behavior_id)
                if not isinstance(load_count, int) or load_count <= 0:
                    errors.append("MULTIPLEX_LOAD_BEARING_RECEIPTS_MISSING:" + behavior_id)
                if invalid_count != 0:
                    errors.append("MULTIPLEX_INVALID_RECEIPTS:" + behavior_id)
                sources.append("PARENT_MULTIPLEX")
                source_passes.append(red.get("status") == "PASS_COMPONENT")
                source_terminal.append(
                    isinstance(receipt_count, int)
                    and receipt_count > 0
                    and isinstance(load_count, int)
                    and load_count > 0
                    and invalid_count == 0
                )

        if behavior_id in OVERLAP_IDS and len(sources) != 2:
            errors.append("OVERLAP_EVIDENCE_INCOMPLETE:" + behavior_id)
        if not sources:
            errors.append("NO_EVIDENCE_SOURCE:" + behavior_id)
            continue

        terminal = all(source_terminal)
        passed = terminal and all(source_passes)
        verdicts[behavior_id] = {
            "behavior_id": behavior_id,
            "status": "PASS" if passed else "FAIL",
            "pass": passed,
            "terminal_result": terminal,
            "evidence_sources": sources,
            "source_passes": source_passes,
        }

    if set(verdicts) != set(ACTIVE_IDS):
        errors.append("CONTRACT_VERDICT_SET_INCOMPLETE")
    if errors:
        return _fail(errors)

    all_pass = all(row["pass"] is True for row in verdicts.values())
    return {
        "schema": VERDICT_SCHEMA,
        "status": "VALID_TERMINAL_VERDICT_SET",
        "valid": True,
        "all_contracts_pass": all_pass,
        "contract_verdicts": verdicts,
        "errors": [],
        "contract_count": len(verdicts),
        "candidate_package_commitment": commitment,
        "post_freeze_beacon": beacon,
        "terminal_result": True,
        "rule": (
            "NORMALIZE_ONE_SHOT_WAVE_TO_EXACT_12_CONTRACT_VERDICTS__"
            "CAD_REQUIRES_DIRECT_AND_MULTIPLEX_CONSISTENCY__"
            "VALID_NEGATIVE_OUTCOMES_ARE_PRESERVED__NO_FAMILY_CREDIT"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
