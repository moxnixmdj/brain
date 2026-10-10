"""Independent verifier for residual semantic control invariance V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import residual_semantic_control_invariance_v1 as candidate_builder

SCHEMA = "PROJECT_BRAIN_RESIDUAL_SEMANTIC_CONTROL_INVARIANCE_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = "canonical/runtime/residual_semantic_control_invariance_v1.py"
ORIGIN_POLICY_PATH = "canonical/runtime/minimum_information_origin_policy_v1.py"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return "sha256:" + sha256(_canon(value)).hexdigest()


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def verify(
    candidate: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        if not isinstance(candidate, Mapping):
            raise ValueError("CANDIDATE_MAPPING_REQUIRED")
        if candidate.get("schema") != candidate_builder.SCHEMA:
            raise ValueError("CANDIDATE_SCHEMA_INVALID")
        if candidate.get("pass") is not True:
            raise ValueError("CANDIDATE_NOT_PASS")

        rebuilt = candidate_builder.build_candidate(
            environment_id=str(candidate.get("environment_id") or ""),
            goal_id=str(candidate.get("goal_id") or ""),
            semantic_state=str(candidate.get("semantic_state") or ""),
            decision_relevant=candidate.get("decision_relevant") is True,
            information_origin=deepcopy(candidate.get("information_origin")),
        )
        for field in (
            "environment_id",
            "goal_id",
            "semantic_state",
            "decision_relevant",
            "information_origin",
            "information_origin_sha256",
            "action",
            "control_scope",
            "candidate_sha256",
            "origin_policy_result",
            "semantic_identity_consulted",
        ):
            if candidate.get(field) != rebuilt.get(field):
                raise ValueError("CANDIDATE_RECOMPUTATION_MISMATCH:" + field)

        if candidate.get("control_scope") != candidate_builder.CONTROL_SCOPE:
            raise ValueError("CONTROL_SCOPE_INVALID")
        if candidate.get("semantic_identity_consulted") is not False:
            raise ValueError("SEMANTIC_IDENTITY_DEPENDENCE_FORBIDDEN")
        if candidate.get("open_world_semantics_closed") is not False:
            raise ValueError("SEMANTIC_CLOSURE_OVERCLAIM")
        if candidate.get("intended_sense_identified") is not False:
            raise ValueError("INTENDED_SENSE_OVERCLAIM")
        if candidate.get("semantic_truth_authority") is not False:
            raise ValueError("SEMANTIC_TRUTH_AUTHORITY_FORBIDDEN")
        if candidate.get("final_domain_action_authority") is not False:
            raise ValueError("FINAL_DOMAIN_ACTION_AUTHORITY_FORBIDDEN")

        builder_path = root / BUILDER_PATH
        origin_path = root / ORIGIN_POLICY_PATH
        if not builder_path.is_file() or not origin_path.is_file():
            raise ValueError("BOUND_RUNTIME_FILE_MISSING")
        builder_blob = _git_blob(builder_path)
        origin_blob = _git_blob(origin_path)

        receipt_material = {
            "environment_id": candidate["environment_id"],
            "goal_id": candidate["goal_id"],
            "action": candidate["action"],
            "candidate_sha256": candidate["candidate_sha256"],
            "builder_git_blob_sha": builder_blob,
            "origin_policy_git_blob_sha": origin_blob,
            "control_scope": candidate_builder.CONTROL_SCOPE,
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__RESIDUAL_SEMANTIC_CONTROL_INVARIANCE_VERIFIED",
            "pass": True,
            "conclusion": "success",
            "independent_verified": True,
            "exact_byte_bound": True,
            "environment_id": candidate["environment_id"],
            "goal_id": candidate["goal_id"],
            "action": candidate["action"],
            "control_scope": candidate_builder.CONTROL_SCOPE,
            "all_unmodeled_decision_relevant_alternatives_imply_control_action": True,
            "semantic_identity_consulted": False,
            "open_world_semantics_closed": False,
            "intended_sense_identified": False,
            "semantic_truth_authority": False,
            "final_domain_action_authority": False,
            "control_action_authority": True,
            "builder_path": BUILDER_PATH,
            "builder_git_blob_sha": builder_blob,
            "origin_policy_path": ORIGIN_POLICY_PATH,
            "origin_policy_git_blob_sha": origin_blob,
            "candidate_sha256": candidate["candidate_sha256"],
            "receipt_id": _sha(receipt_material),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "conclusion": "failure",
            "independent_verified": False,
            "exact_byte_bound": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_truth_authority": False,
            "final_domain_action_authority": False,
            "control_action_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
