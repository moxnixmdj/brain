"""Route-specific terminal executor for SA-CCR credit contract.

This module implements the exact frozen V2 route semantics:
- 2000 post-freeze cases;
- V2 seed rule bound to candidate commitment + unpredictable beacon + case id;
- Brain-owned candidate only;
- independent hidden oracle;
- zero replacement and zero replay.

Importantly, importing/testing this module does not consume terminal evidence.
Only execute_terminal() with the canonical execution authority may do so.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from canonical.runtime import saccr_credit_information_safe_candidate as candidate
from canonical.runtime import saccr_credit_information_safe_proof as proof

SCHEMA = "PROJECT_BRAIN_SACCR_ROUTE_SPECIFIC_TERMINAL_EXECUTOR_V1"
BEHAVIOR_ID = "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"
ROUTE_POPULATION_VERSION = "SA_CCR_TERMINAL_POPULATION_V1"
SAMPLE_COUNT = 2000
PREFIX = b"PROJECT_BRAIN_TERMINAL_V2\0"

POPULATION_BINDING = Path("canonical/governance/SA_CCR_TERMINAL_POPULATION_BINDING_V1.json")
WAVE_AUTHORITY = Path("canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json")


def derive_seed(commitment: str, beacon: str, case_id: str) -> int:
    if not all(isinstance(x, str) and x for x in (commitment, beacon, case_id)):
        raise ValueError("NONEMPTY_STRING_BINDINGS_REQUIRED")
    raw = PREFIX + commitment.encode() + b"\0" + beacon.encode() + b"\0" + case_id.encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big", signed=False)


def case_id(index: int) -> str:
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < SAMPLE_COUNT:
        raise ValueError("INDEX_OUT_OF_RANGE")
    return f"{BEHAVIOR_ID}::{ROUTE_POPULATION_VERSION}::slot::{index}"


def static_preflight(root: Path = Path(".")) -> dict[str, Any]:
    errors: list[str] = []
    try:
        binding = json.loads((root / POPULATION_BINDING).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema": SCHEMA, "pass": False, "errors": ["BINDING_READ:" + type(exc).__name__]}

    pop = binding.get("population")
    acceptance = binding.get("acceptance")
    if binding.get("behavior_id") != BEHAVIOR_ID:
        errors.append("BEHAVIOR_ID_MISMATCH")
    if binding.get("pre_beacon_frozen") is not True:
        errors.append("NOT_PRE_BEACON_FROZEN")
    if not isinstance(pop, dict):
        errors.append("POPULATION_INVALID")
        pop = {}
    if pop.get("sample_count") != SAMPLE_COUNT:
        errors.append("SAMPLE_COUNT_MISMATCH")
    if pop.get("route_population_version") != ROUTE_POPULATION_VERSION:
        errors.append("POPULATION_VERSION_MISMATCH")
    if pop.get("case_replacement") is not False:
        errors.append("CASE_REPLACEMENT_NOT_FALSE")
    if pop.get("adaptive_case_selection") is not False:
        errors.append("ADAPTIVE_SELECTION_NOT_FALSE")
    if pop.get("replay_for_tuning") is not False:
        errors.append("REPLAY_FOR_TUNING_NOT_FALSE")
    if pop.get("post_freeze_beacon") is not None:
        errors.append("BEACON_PREBOUND")
    if not isinstance(acceptance, dict):
        errors.append("ACCEPTANCE_INVALID")
        acceptance = {}
    if acceptance.get("allowed_failed_cases") != 0:
        errors.append("FAILED_CASE_ALLOWANCE_NONZERO")
    if acceptance.get("case_local_execution_failure_counts_as_failure") is not True:
        errors.append("CASE_LOCAL_FAILURE_RULE_MISSING")
    if binding.get("terminal_results_observed") != 0:
        errors.append("TERMINAL_RESULT_ALREADY_OBSERVED")
    if binding.get("fresh_terminal_evidence_consumed") != 0:
        errors.append("FRESH_EVIDENCE_ALREADY_CONSUMED")

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "errors": sorted(set(errors)),
        "sample_count": SAMPLE_COUNT,
        "behavior_id": BEHAVIOR_ID,
        "terminal_authority": False,
    }


def _evaluate_indices(commitment: str, beacon: str, indices: Iterable[int]) -> dict[str, Any]:
    rows = []
    for i in indices:
        cid = case_id(i)
        seed = derive_seed(commitment, beacon, cid)
        try:
            hidden = proof.generate_case(seed)
            public = proof.public_task(hidden)
            answer = candidate.solve(public)
            verdict = proof.score_case(hidden, answer)
            passed = verdict.get("pass") is True
            reason = verdict.get("reason")
        except Exception as exc:
            passed = False
            reason = "EXECUTION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)
        rows.append({
            "index": i,
            "case_id": cid,
            "seed": seed,
            "pass": passed,
            "reason": reason,
        })
    return {
        "schema": SCHEMA,
        "behavior_id": BEHAVIOR_ID,
        "case_count": len(rows),
        "pass_count": sum(int(x["pass"]) for x in rows),
        "all_pass": all(x["pass"] for x in rows),
        "failures": [x for x in rows if not x["pass"]],
        "rows": rows,
        "terminal_authority": False,
    }


def dev_self_check(commitment: str = "DEV_COMMITMENT", beacon: str = "DEV_NONTERMINAL_BEACON") -> dict[str, Any]:
    """Exercise a deterministic nonterminal prefix for verifier/runtime sanity only."""
    return _evaluate_indices(commitment, beacon, range(32))


def execute_terminal(
    *,
    candidate_package_commitment: str,
    post_freeze_beacon: str,
    root: Path = Path("."),
) -> dict[str, Any]:
    pre = static_preflight(root)
    if pre.get("pass") is not True:
        raise ValueError("STATIC_PREFLIGHT_FAILED:" + ",".join(pre.get("errors", [])))

    authority = json.loads((root / WAVE_AUTHORITY).read_text(encoding="utf-8"))
    if authority.get("execution_authority") is not True:
        raise ValueError("TERMINAL_WAVE_NOT_AUTHORIZED")
    if authority.get("terminal_results_observed") != 0 or authority.get("fresh_terminal_evidence_consumed") != 0:
        raise ValueError("TERMINAL_WAVE_ALREADY_CONSUMED_OR_STATE_DRIFTED")
    if "ROUTE_SPECIFIC_EXECUTOR_SET_MUST_EQUAL_ALL_12_FROZEN_BINDINGS" not in authority.get("conditions", []):
        raise ValueError("ROUTE_SPECIFIC_EXECUTOR_AUTHORITY_NOT_BOUND")

    out = _evaluate_indices(candidate_package_commitment, post_freeze_beacon, range(SAMPLE_COUNT))
    out.update({
        "status": "PASS" if out["all_pass"] and out["case_count"] == SAMPLE_COUNT else "FAIL",
        "terminal_authority": True,
        "fresh_terminal_evidence_consumed": SAMPLE_COUNT,
        "case_replacement": False,
        "tuning_replay": False,
        "acceptance_rule": "ALL_2000_CASES_PASS",
        "capability_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
    })
    return out
