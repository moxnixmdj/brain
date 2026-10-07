from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_P2_ROUTE_IDENTITY_AUDIT_V1"

TOP_CELL = "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json"
P2_BINDING = "canonical/governance/P2_PROFESSIONAL_QUALITY_T1_MULTIPLEX_TERMINAL_BINDING_V1.json"
SUITE = "canonical/runtime/contract_native_proof_suites.py"
EXEC_CANDIDATE = "canonical/runtime/contract_native_brain_candidate.py"
CLAIMED_CANDIDATE = "canonical/runtime/p2_p3_information_safe_candidate_v2.py"
TERMINAL_RESULT = "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"

EXPECTED = {
    TOP_CELL: "28692768a21e95b51e847417cf5ba2343587e4aa",
    P2_BINDING: "8d5888a8299d1b8addd629be01fe9a6dc46b1a7d",
    SUITE: "0210790c7dd705ef328e1b55d529a30c5c6c3337",
    EXEC_CANDIDATE: "afc18af1d1da6f25166c6cc57dcbc0cd3070bb85",
    CLAIMED_CANDIDATE: "ea8057b0eadac210c4f4378298df93ed233c5824",
    TERMINAL_RESULT: "bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
}

EXECUTION_SNAPSHOT_COMMIT = "821712c059b139f3494723dca6e8d0fc82ee59a4"
SNAPSHOT_PARENT_BINDING_BLOB = "5212f5996dbc83e87a308b8c9d9d1d9ed3da5aab"
SNAPSHOT_P2_MODE = "CONTRACT_NATIVE"
SNAPSHOT_EXEC_SUITE_BLOB = "0210790c7dd705ef328e1b55d529a30c5c6c3337"
SNAPSHOT_EXEC_CANDIDATE_BLOB = "afc18af1d1da6f25166c6cc57dcbc0cd3070bb85"


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> dict:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _professional_case_public_fields() -> dict:
    namespace: dict = {}
    source = (ROOT / SUITE).read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_professional_plan_case"
    )
    # Static literal-field audit of the edit row generated into case["task"].
    edit_fields: set[str] = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Dict):
            continue
        keys = []
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.append(key.value)
        if {"id", "scores", "cost", "supported", "hard_violation"}.issubset(set(keys)):
            edit_fields.update(keys)
    # public_task removes only _oracle, so task fields remain candidate-visible.
    public_fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "public_task"
    )
    public_source = ast.get_source_segment(source, public_fn) or ""
    removes_only_oracle = 'k!="_oracle"' in public_source.replace(" ", "")
    return {
        "edit_fields": sorted(edit_fields),
        "public_task_removes_only_oracle": removes_only_oracle,
    }


def evaluate() -> dict:
    drift = {
        path: {"expected": expected, "actual": blob(path)}
        for path, expected in EXPECTED.items()
        if blob(path) != expected
    }
    if drift:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__BOUND_SOURCE_DRIFT",
            "pass": False,
            "drift": drift,
        }

    top = _load(TOP_CELL)
    p2 = _load(P2_BINDING)
    terminal = _load(TERMINAL_RESULT)
    public = _professional_case_public_fields()

    selected = top["selected_route"]["candidate"]
    declared_candidate_path = p2["evaluator"]["candidate"]
    hidden = set(p2["hidden_evaluator_information"])
    visible = set(p2["candidate_visible_information"])

    selected_route_identity_matches_snapshot = (
        selected.get("git_blob_sha") == SNAPSHOT_EXEC_CANDIDATE_BLOB
        and selected.get("path") == EXEC_CANDIDATE
    )
    p2_binding_candidate_matches_snapshot = (
        declared_candidate_path == EXEC_CANDIDATE
    )

    exposed = set(public["edit_fields"])
    gold_quality_effect_visible = "scores" in exposed
    grounding_truth_visible = "supported" in exposed
    hard_constraint_truth_visible = "hard_violation" in exposed

    terminal_snapshot_matches = (
        terminal.get("execution_snapshot_commit") == EXECUTION_SNAPSHOT_COMMIT
    )

    mismatch = (
        terminal_snapshot_matches
        and selected.get("path") == CLAIMED_CANDIDATE
        and selected.get("git_blob_sha") == EXPECTED[CLAIMED_CANDIDATE]
        and not selected_route_identity_matches_snapshot
        and declared_candidate_path == CLAIMED_CANDIDATE
        and not p2_binding_candidate_matches_snapshot
        and SNAPSHOT_P2_MODE == "CONTRACT_NATIVE"
        and public["public_task_removes_only_oracle"]
        and gold_quality_effect_visible
        and grounding_truth_visible
        and "PER_EDIT_RUBRIC_QUALITY_EFFECT" in hidden
        and "EVIDENCE_GROUNDING_TRUTH" in hidden
        and "EDIT_OPTIONS_WITHOUT_GOLD_QUALITY_EFFECTS" in visible
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PROFESSIONAL_TOP_CELL_WITNESS_ROUTE_IDENTITY_MISMATCH_LOCALIZED"
            if mismatch else
            "FAIL_CLOSED__EXPECTED_ROUTE_IDENTITY_MISMATCH_NOT_PROVED"
        ),
        "pass": mismatch,
        "execution_snapshot": {
            "commit": EXECUTION_SNAPSHOT_COMMIT,
            "parent_binding_git_blob_sha": SNAPSHOT_PARENT_BINDING_BLOB,
            "p2_mode": SNAPSHOT_P2_MODE,
            "suite_git_blob_sha": SNAPSHOT_EXEC_SUITE_BLOB,
            "candidate_git_blob_sha": SNAPSHOT_EXEC_CANDIDATE_BLOB,
        },
        "selected_top_cell_route": selected,
        "frozen_p2_binding_candidate": declared_candidate_path,
        "selected_route_identity_matches_execution_snapshot": selected_route_identity_matches_snapshot,
        "p2_binding_candidate_matches_execution_snapshot": p2_binding_candidate_matches_snapshot,
        "candidate_visible_contract_native_edit_fields": public["edit_fields"],
        "information_boundary_conflicts": {
            "gold_quality_effect_visible_as_scores": gold_quality_effect_visible,
            "grounding_truth_visible_as_supported": grounding_truth_visible,
            "hard_constraint_truth_visible": hard_constraint_truth_visible,
            "binding_hides_per_edit_quality_effect": "PER_EDIT_RUBRIC_QUALITY_EFFECT" in hidden,
            "binding_hides_grounding_truth": "EVIDENCE_GROUNDING_TRUTH" in hidden,
            "binding_requires_edit_options_without_gold_effects": "EDIT_OPTIONS_WITHOUT_GOLD_QUALITY_EFFECTS" in visible,
        },
        "counterfactual": {
            "world_a": "THE_CLAIMED_INFORMATION_SAFE_P2_CANDIDATE_EXECUTES_AND_PASSES_THE_BOOLEAN_GATE",
            "world_b": "A_DIFFERENT_CONTRACT_NATIVE_CANDIDATE_EXECUTES_WITH_GOLD_QUALITY_FIELDS_VISIBLE_AND_PASSES",
            "observed_terminal_aggregate_receipt_can_be_THE_SAME": True,
            "selected_route_credit_truth_can_DIFFER": True,
        },
        "localized_repair": (
            "PROVE_ROUTE_EQUIVALENCE_AND_INFORMATION_BOUNDARY_PRESERVATION_FROM_THE_EXECUTED_"
            "CONTRACT_NATIVE_ROUTE_TO_THE_CLAIMED_P2_ROUTE__OR_REVOKE_THE_SELECTED_PROPERTY_CELL_"
            "AND_REBUILD_IT_ONLY_FROM_EVIDENCE_EXECUTED_BY_THE_CLAIMED_ROUTE"
        ),
        "scope_boundary": (
            "THIS_AUDIT_ATTACKS_ONLY_THE_NEW_PROFESSIONAL_ARTIFACT_SELECTED_PROPERTY_CELL_AND_"
            "ANY_CLAIM_THAT_REUSES_THE_TERMINAL_P2_AGGREGATE_AS_IF_IT_CAME_FROM_THE_INFORMATION_SAFE_ROUTE"
        ),
        "hard_nonclaims": [
            "NO_CLAIM_THE_WHOLE_TERMINAL_WAVE_IS_INVALID",
            "NO_CLAIM_OTHER_BEHAVIOR_RECEIPTS_ARE_INVALID",
            "NO_CLAIM_THE_CONTRACT_NATIVE_ROUTE_FAILED_ITS_OWN_SCORER",
            "NO_CLAIM_THE_INFORMATION_SAFE_P2_CANDIDATE_FAILED",
            "NO_TERMINAL_CREDIT",
        ],
        "incremental_spend_usd": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
