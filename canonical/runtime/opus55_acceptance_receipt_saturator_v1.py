"""Zero-reality receipt saturation for the frozen Opus 5.5 acceptance residual.

This module does not infer broad family ownership. It performs two narrow jobs:
1. attest that the canonical immutable receipt roots were exhaustively scanned at a pinned source snapshot;
2. derive only acceptance predicates that are direct logical consequences of exact hash-bound terminal receipts.

No fresh benchmark cases are executed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_SNAPSHOT_SHA = "8687e93675abbba973bb263db5d4224ced94240f"
SOURCE_TREE_SHA = "43291b9a528877e8a4e72fe9208d845444ce06e6"
SCAN_ROOTS = (
    "canonical/verification",
    "canonical/governance",
    "canonical/capabilities/opus55",
)
EXPECTED_JSON_COUNT = 768

TERMINAL_RESULT_PATH = "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
TERMINAL_RESULT_BLOB = "bd86b4c53992b47a4a60b64a60ba03db9a442cfc"
P3_BINDING_PATH = "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
P3_BINDING_BLOB = "ad790afa864bd8f770c3d8a6e3ac901ed2843d26"
TOOL_BINDING_PATH = "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
TOOL_BINDING_BLOB = "6bcabc0a7d0525532ce7b80e132278f7c99caa43"

PROOF_BUNDLE_PATH = "canonical/governance/OPUS55_ACCEPTANCE_ZERO_REALITY_DERIVATIONS_V1.json"


def _load(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{rel} must contain a JSON object")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(payload).hexdigest()


def _assert_blob(root: Path, rel: str, expected: str) -> None:
    actual = _git_blob_sha(root / rel)
    if actual != expected:
        raise AssertionError(f"BLOB_MISMATCH:{rel}:{actual}:{expected}")


def _json_count(root: Path) -> int:
    seen: set[Path] = set()
    for rel in SCAN_ROOTS:
        base = root / rel
        for p in base.rglob("*.json"):
            if p.is_file():
                seen.add(p.resolve())
    return len(seen)


def _synthesis_receipts(terminal: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    receipts = terminal["reduction_input"]["wave"]["parent_portfolio_receipts"]
    for portfolio in ("T1", "T3"):
        rows = receipts.get(portfolio, [])
        hit = next(
            (
                row
                for row in rows
                if row.get("behavior_id") == "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
            ),
            None,
        )
        if hit is None:
            raise AssertionError(f"MISSING_SYNTHESIS_TERMINAL_RECEIPT:{portfolio}")
        out.append(hit)
    return out


def evaluate(root: Path) -> dict[str, Any]:
    if _json_count(root) != EXPECTED_JSON_COUNT:
        raise AssertionError(
            f"PINNED_RECEIPT_CORPUS_COUNT_MISMATCH:{_json_count(root)}:{EXPECTED_JSON_COUNT}"
        )

    _assert_blob(root, TERMINAL_RESULT_PATH, TERMINAL_RESULT_BLOB)
    _assert_blob(root, P3_BINDING_PATH, P3_BINDING_BLOB)
    _assert_blob(root, TOOL_BINDING_PATH, TOOL_BINDING_BLOB)

    terminal = _load(root, TERMINAL_RESULT_PATH)
    p3 = _load(root, P3_BINDING_PATH)
    tool = _load(root, TOOL_BINDING_PATH)

    if terminal.get("execution_snapshot_commit") != "821712c059b139f3494723dca6e8d0fc82ee59a4":
        raise AssertionError("UNEXPECTED_TERMINAL_EXECUTION_SNAPSHOT")
    if terminal.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        raise AssertionError("TERMINAL_WAVE_NOT_IMMUTABLE_PASS")
    guards = terminal.get("result_guards", {})
    if guards.get("no_case_replacement") is not True or guards.get("no_tuning_replay") is not True:
        raise AssertionError("TERMINAL_RESULT_CONTAMINATION_GUARD_FAILED")
    if guards.get("result_to_runtime_feedback_during_wave") is not False:
        raise AssertionError("TERMINAL_RESULT_FEEDBACK_PRESENT")

    synthesis_rows = _synthesis_receipts(terminal)
    for row in synthesis_rows:
        if row.get("binding_blob") != P3_BINDING_BLOB:
            raise AssertionError("SYNTHESIS_BINDING_BLOB_MISMATCH")
        for field in ("direct_instrumentation_pass", "load_bearing", "parent_terminal_acceptance_pass"):
            if row.get(field) is not True:
                raise AssertionError(f"SYNTHESIS_RECEIPT_NOT_PASS:{field}")
        if row.get("case_replaced") is not False or row.get("tuning_replay") is not False:
            raise AssertionError("SYNTHESIS_RECEIPT_CONTAMINATED")

    required_p3_checks = set(p3["evaluator"]["required_checks"])
    if "ZERO_UNSUPPORTED_MATERIAL_CLAIMS" not in required_p3_checks:
        raise AssertionError("P3_UNSUPPORTED_CLAIM_ORACLE_MISSING")
    if p3["terminal_acceptance"].get("any_load_bearing_p3_failure_blocks_behavior_proof") is not True:
        raise AssertionError("P3_FAILURE_NOT_LOAD_BEARING")

    tool_population = terminal["direct_terminal_population"]["routes"]["TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"]
    if tool_population != {"cases": 180, "passes": 180}:
        raise AssertionError("TOOL_TERMINAL_POPULATION_NOT_180_OF_180")
    if tool.get("status") != "FROZEN_PREWAVE_BINDING__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_TERMINAL_RESULTS":
        raise AssertionError("TOOL_BINDING_NOT_INDEPENDENT_PASS")
    if tool["source_pool"].get("terminal_sample_count") != 180:
        raise AssertionError("TOOL_BINDING_POPULATION_MISMATCH")
    if tool["acceptance"].get("every_selected_case_must_pass") is not True:
        raise AssertionError("TOOL_ACCEPTANCE_NOT_ALL_CASES")
    tool_checks = set(tool["acceptance"]["direct_checks"])
    if "CROSS_TASK_TRANSFER_WITHIN_VALID_EPOCH" not in tool_checks:
        raise AssertionError("TOOL_TRANSFER_CHECK_MISSING")
    if "NO_SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE" not in tool_checks:
        raise AssertionError("TOOL_POSITIVE_EVIDENCE_CHECK_MISSING")
    if "EVIDENCE_BACKED_CAPABILITY_UPDATE" not in set(tool["objective_dimensions"]):
        raise AssertionError("TOOL_EVIDENCE_BACKED_UPDATE_DIMENSION_MISSING")

    claims = [
        {
            "predicate_id": "SYNTHESIS_ZERO_UNSUPPORTED_MATERIAL_CLAIMS",
            "state": "PROVED",
            "proof_kind": "RECEIPT",
            "independent_or_objective": True,
            "scope_complete": True,
            "derivation": "T1_AND_T3_LOAD_BEARING_P3_DIRECT_INSTRUMENTATION_PASS__P3_REQUIRED_CHECK_ZERO_UNSUPPORTED_MATERIAL_CLAIMS",
        },
        {
            "predicate_id": "TOOL_LEARNING_SECOND_TASK_TRANSFER",
            "state": "PROVED",
            "proof_kind": "RECEIPT",
            "independent_or_objective": True,
            "scope_complete": True,
            "derivation": "180_OF_180_FROZEN_TOOL_TERMINAL_CASES_PASS__DIRECT_CHECK_CROSS_TASK_TRANSFER_WITHIN_VALID_EPOCH",
        },
        {
            "predicate_id": "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",
            "state": "PROVED",
            "proof_kind": "RECEIPT",
            "independent_or_objective": True,
            "scope_complete": True,
            "derivation": "180_OF_180_FROZEN_TOOL_TERMINAL_CASES_PASS__NO_SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE__EVIDENCE_BACKED_CAPABILITY_UPDATE",
        },
    ]

    return {
        "schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_RECEIPT_SATURATION_RESULT_V1",
        "status": "COMPLETE__ZERO_NEW_REALITY__3_ATOMIC_PREDICATES_PROVED",
        "source_snapshot_sha": SOURCE_SNAPSHOT_SHA,
        "source_tree_sha": SOURCE_TREE_SHA,
        "scan_roots": list(SCAN_ROOTS),
        "scanned_json_files": EXPECTED_JSON_COUNT,
        "fresh_acceptance_cases_consumed": 0,
        "terminal_replay": False,
        "claims": claims,
        "source_blobs": {
            TERMINAL_RESULT_PATH: TERMINAL_RESULT_BLOB,
            P3_BINDING_PATH: P3_BINDING_BLOB,
            TOOL_BINDING_PATH: TOOL_BINDING_BLOB,
        },
        "rule": "SATURATION_COMPLETION_IS_SEARCH_COMPLETION__ONLY_HASH_BOUND_SCOPE_COMPLETE_DERIVATIONS_RECEIVE_PROVED_CLAIMS",
    }
