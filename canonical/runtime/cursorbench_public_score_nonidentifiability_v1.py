"""CursorBench 4.0 public-score inference non-identifiability.

Narrow theorem only: the currently accessible public/owner-bound evidence cannot
determine the Brain's private CursorBench 4.0 score. This does NOT prove the
acceptance predicate external, because a stronger scope-complete positive
adequacy theorem remains an internal route.

The construction keeps every accessible observation fixed and changes only the
unobserved Brain outcome on the private held-out benchmark. One world crosses
57.8%; the other does not. Therefore a public-data-only score inference is not
sound.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CURSORBENCH_PUBLIC_SCORE_NONIDENTIFIABILITY_V1"

EXPECTED = {
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json":
        "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json":
        "d58c41a8e93fc95df6667e955e291b3f36c8942f",
    "canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json":
        "7401589da3b30954104145dc4959e534ab8cd641",
    "canonical/governance/CODING_PRIVATE_BENCHMARK_PROOF_CARRYING_SCOPE_COVER_RECONCILIATION_20261009_V3.json":
        "6c73b429108efe16e6be94afa846dea6c818db59",
    "canonical/capabilities/frontier/ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_SUPERPOWERS_V1.json":
        "e7d4fbceb8f69bbe21a28a525b9c04ebf97628c9",
    "canonical/capabilities/internalized/software_engineering/mini_swe_superpowers_v1/EVALUATION_PROTOCOL_V2.json":
        "508199f53727cd0a7b7fa19a81caca1329fde1a2",
}

def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def _load(path: str) -> dict[str, Any]:
    obj = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return obj

def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")

def _sha256(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()

def construct_world_pair(
    *,
    threshold_percent: float,
    accessible_observation: Mapping[str, Any],
    public_brain_score_percent: float | None = None,
) -> dict[str, Any]:
    if isinstance(threshold_percent, bool) or not isinstance(threshold_percent, (int, float)):
        raise ValueError("THRESHOLD_INVALID")
    if not 0.0 <= float(threshold_percent) <= 100.0:
        raise ValueError("THRESHOLD_OUT_OF_RANGE")
    if not isinstance(accessible_observation, Mapping) or not accessible_observation:
        raise ValueError("ACCESSIBLE_OBSERVATION_REQUIRED")

    obs = _sha256(dict(accessible_observation))

    if public_brain_score_percent is not None:
        score = float(public_brain_score_percent)
        action = "ACCEPT" if score >= float(threshold_percent) else "REJECT"
        return {
            "schema": SCHEMA + "_WORLD_PAIR",
            "nonidentifiable": False,
            "reason": "BRAIN_SCORE_IS_ALREADY_ACCESSIBLE",
            "accessible_observation_sha256": obs,
            "known_score_percent": score,
            "required_action": action,
        }

    hi = float(threshold_percent)
    lo = 0.0 if hi > 0 else 100.0
    if hi == 0.0:
        # For a zero threshold every valid percentage passes, so no action
        # separation can be constructed.
        return {
            "schema": SCHEMA + "_WORLD_PAIR",
            "nonidentifiable": False,
            "reason": "THRESHOLD_ZERO_HAS_NO_PASS_FAIL_SEPARATION",
            "accessible_observation_sha256": obs,
        }

    world_pass = {
        "world_id": "W_PASS",
        "accessible_observation_sha256": obs,
        "hidden_brain_cursorbench_score_percent": hi,
        "required_action": "ACCEPT",
    }
    world_fail = {
        "world_id": "W_FAIL",
        "accessible_observation_sha256": obs,
        "hidden_brain_cursorbench_score_percent": lo,
        "required_action": "REJECT",
    }
    return {
        "schema": SCHEMA + "_WORLD_PAIR",
        "nonidentifiable": True,
        "reason": "SAME_ACCESSIBLE_EVIDENCE__DIFFERENT_PRIVATE_BRAIN_OUTCOME__DIFFERENT_ACCEPTANCE_ACTION",
        "accessible_observation_sha256": obs,
        "world_pass": world_pass,
        "world_fail": world_fail,
        "actions_differ": world_pass["required_action"] != world_fail["required_action"],
        "observations_equal": (
            world_pass["accessible_observation_sha256"]
            == world_fail["accessible_observation_sha256"]
        ),
    }

def verify_current() -> dict[str, Any]:
    errors: list[str] = []
    for path, expected in EXPECTED.items():
        full = ROOT / path
        if not full.is_file():
            errors.append("SOURCE_MISSING:" + path)
            continue
        if _git_blob(full) != expected:
            errors.append("SOURCE_DRIFT:" + path)

    registry = _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
    owner = _load("canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json")
    scope = _load("canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json")
    reconciliation = _load(
        "canonical/governance/CODING_PRIVATE_BENCHMARK_PROOF_CARRYING_SCOPE_COVER_RECONCILIATION_20261009_V3.json"
    )
    frontier = _load(
        "canonical/capabilities/frontier/ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_SUPERPOWERS_V1.json"
    )
    protocol = _load(
        "canonical/capabilities/internalized/software_engineering/mini_swe_superpowers_v1/EVALUATION_PROTOCOL_V2.json"
    )

    rows = {
        row.get("id"): row
        for row in registry.get("predicates", [])
        if isinstance(row, Mapping)
    }
    pred = rows.get("CODING_CURSORBENCH_GE_57_8")
    if not isinstance(pred, Mapping):
        errors.append("CURSORBENCH_PREDICATE_MISSING")
        threshold = 57.8
    else:
        if pred.get("acceptance") != "CursorBench 4.0 >= 57.8%":
            errors.append("CURSORBENCH_FROZEN_ACCEPTANCE_DRIFT")
        threshold = 57.8

    facts = set(owner.get("owner_facts") or [])
    for fact in (
        "CURSORBENCH_IS_INTERNAL_EVALUATION_SUITE",
        "NO_OWNER_RUN_EVALUATION_OF_EXTERNAL_SYSTEMS_ON_CURSORBENCH_4_0",
        "NO_PUBLIC_SUBMISSION_INTERFACE_API_CONTAINER_CLI_OR_SIMILAR_FOR_THIRD_PARTY_SYSTEMS",
        "PRIVATE_AND_HELDOUT_TASKS_STAY_PRIVATE",
    ):
        if fact not in facts:
            errors.append("OWNER_FACT_MISSING:" + fact)

    if scope.get("scope_complete") is not True:
        errors.append("SCOPE_COMPLETENESS_NOT_CLOSED")
    if scope.get("positive_adequacy_cover_closed") is not False:
        errors.append("ADEQUACY_STATE_DRIFT")
    if scope.get("acceptance_state") != "OPEN":
        errors.append("SCOPE_RECEIPT_ACCEPTANCE_MUST_REMAIN_OPEN")

    cursor = reconciliation.get("cursorbench_4_0") or {}
    if cursor.get("scope_gap_deleted") is not True:
        errors.append("CURSORBENCH_SCOPE_GAP_NOT_DELETED")
    if cursor.get("positive_adequacy_cover_closed") is not False:
        errors.append("CURSORBENCH_ADEQUACY_MUST_REMAIN_OPEN")
    if cursor.get("cursorbench_score_proved") is not False:
        errors.append("CURSORBENCH_SCORE_MUST_REMAIN_UNPROVED")

    if frontier.get("current_opus_5_5_credit", 0) != 0:
        errors.append("CODING_FRONTIER_CREDIT_UNEXPECTED")
    if "BENCHMARK_SCORE_PENDING" not in str(frontier.get("status", "")).upper():
        errors.append("FRONTIER_SCORE_PENDING_STATUS_MISSING")

    stage3 = None
    for row in protocol.get("stage_order", []):
        if isinstance(row, Mapping) and row.get("stage") == 3:
            stage3 = row
    if not isinstance(stage3, Mapping) or float(stage3.get("target_percent", -1)) != threshold:
        errors.append("EVALUATION_PROTOCOL_CURSORBENCH_TARGET_DRIFT")
    if (protocol.get("stage_1_progress") or {}).get("benchmark_comparable_score_established") is not False:
        errors.append("CODING_COMPARABLE_SCORE_UNEXPECTEDLY_ESTABLISHED")

    accessible = {
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "threshold_percent": threshold,
        "owner_route": {
            "external_submission": False,
            "private_tasks": True,
        },
        "scope_complete": scope.get("scope_complete"),
        "positive_adequacy_cover_closed": scope.get("positive_adequacy_cover_closed"),
        "brain_cursorbench_score_public": None,
        "coding_stage1_comparable_score_established": (
            protocol.get("stage_1_progress") or {}
        ).get("benchmark_comparable_score_established"),
    }
    pair = construct_world_pair(
        threshold_percent=threshold,
        accessible_observation=accessible,
        public_brain_score_percent=None,
    )
    if pair.get("nonidentifiable") is not True:
        errors.append("WORLD_PAIR_NOT_CONSTRUCTED")
    if pair.get("observations_equal") is not True:
        errors.append("WORLD_PAIR_OBSERVATIONS_DIFFER")
    if pair.get("actions_differ") is not True:
        errors.append("WORLD_PAIR_ACTIONS_NOT_SEPARATED")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PUBLIC_DATA_ONLY_CURSORBENCH_SCORE_INFERENCE_NONIDENTIFIABLE__"
            "STRONGER_POLICY_ADEQUACY_ROUTE_REMAINS_INTERNAL_UNSOLVED__ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": errors,
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "threshold_percent": threshold,
        "world_pair": pair,
        "public_data_exact_score_route": (
            "PROVED_NONIDENTIFIABLE" if passed else "UNRESOLVED"
        ),
        "scope_complete": scope.get("scope_complete"),
        "stronger_scope_complete_policy_adequacy_route": "INTERNAL_UNSOLVED",
        "stronger_route_missing_object":
            "SCOPE_COMPLETE_AUTHENTICATED_BRAIN_OWNED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        "whole_acceptance_predicate_external": False,
        "information_theoretic_externality_claimed_for_whole_predicate": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "rule": (
            "DELETE_ONLY_PUBLIC_DATA_SCORE_INFERENCE__DO_NOT_CLASSIFY_THE_WHOLE_"
            "CURSORBENCH_PREDICATE_EXTERNAL_WHILE_A_STRONGER_INTERNAL_SCOPE_COMPLETE_"
            "POLICY_ADEQUACY_PROOF_ROUTE_REMAINS_LOGICALLY_OPEN"
        ),
    }

if __name__ == "__main__":
    print(json.dumps(verify_current(), indent=2, sort_keys=True))
