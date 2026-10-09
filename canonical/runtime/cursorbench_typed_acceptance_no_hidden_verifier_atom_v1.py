"""Proof one typed-acceptance membership atom from the frozen prewave boundary.

This module proves only SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1 for the exact
SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001 prewave binding. It does not
infer arbitrary task isolation and it does not prove any other membership atom.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.verify_specification_acceptance_prewave_v1 import (
    verify as verify_prewave,
)

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_NO_HIDDEN_VERIFIER_ATOM_PROOF_V1"
ATOM_ID = "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
ATOM_SEMANTICS = (
    "NO_HIDDEN_VERIFIER_OR_TASK_SPECIFIC_SOLUTION_INFORMATION_WAS_USED_BEFORE_"
    "TERMINAL_AUTHORIZATION"
)
BINDING_PATH = (
    "canonical/governance/"
    "SPECIFICATION_INDEPENDENT_ACCEPTANCE_PREWAVE_BINDING_V1.json"
)
BINDING_BLOB_SHA = "65c2ea78a548b4f4cd12ca6275cbad7ad2e08900"
PREWAVE_VERIFIER_PATH = (
    "canonical/runtime/verify_specification_acceptance_prewave_v1.py"
)
PREWAVE_VERIFIER_BLOB_SHA = "d9f113f6262c3b90c50169de4052a4a6021d7b75"
ROOT = Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED__NO_HIDDEN_VERIFIER_ATOM_UNPROVED",
        "reason": reason,
        "atom_id": ATOM_ID,
        "atom_truth_authorized": False,
        "proved_constraint": None,
        "membership_self_certified": False,
        "whole_policy_condition_proved": False,
        "whole_specification_behavior_adequate": False,
        "whole_cursorbench_adequate": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def verify(
    binding_ref: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(binding_ref, Mapping):
        return _fail("BINDING_REFERENCE_NOT_OBJECT")
    if binding_ref.get("path") != BINDING_PATH:
        return _fail("BINDING_PATH_NOT_EXACT_PREWAVE")
    if binding_ref.get("git_blob_sha") != BINDING_BLOB_SHA:
        return _fail("BINDING_REFERENCE_SHA_MISMATCH")

    try:
        root = (Path(repo_root) if repo_root is not None else ROOT).resolve(strict=True)
        binding = root / BINDING_PATH
        verifier = root / PREWAVE_VERIFIER_PATH
        for path in (binding, verifier):
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            if path.is_symlink():
                return _fail("BOUND_FILE_SYMLINK_FORBIDDEN", path=str(path))
            if not path.is_file():
                return _fail("BOUND_FILE_NOT_REGULAR", path=str(path))

        actual_binding_sha = _git_blob_sha(binding)
        if actual_binding_sha != BINDING_BLOB_SHA:
            return _fail(
                "BOUND_PREWAVE_BINDING_DRIFT",
                expected=BINDING_BLOB_SHA,
                actual=actual_binding_sha,
            )
        actual_verifier_sha = _git_blob_sha(verifier)
        if actual_verifier_sha != PREWAVE_VERIFIER_BLOB_SHA:
            return _fail(
                "BOUND_PREWAVE_VERIFIER_DRIFT",
                expected=PREWAVE_VERIFIER_BLOB_SHA,
                actual=actual_verifier_sha,
            )

        doc = json.loads(binding.read_text(encoding="utf-8"))
        if doc.get("schema") != "PROJECT_BRAIN_SPECIFICATION_INDEPENDENT_ACCEPTANCE_PREWAVE_BINDING_V1":
            return _fail("BOUND_PREWAVE_SCHEMA_INVALID")
        if doc.get("behavior_id") != "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001":
            return _fail("BOUND_PREWAVE_BEHAVIOR_MISMATCH")

        boundary = doc.get("information_boundary")
        if not isinstance(boundary, Mapping):
            return _fail("INFORMATION_BOUNDARY_NOT_OBJECT")
        if boundary.get("candidate_receives_hidden_oracle") is not False:
            return _fail("HIDDEN_ORACLE_VISIBLE")
        if boundary.get("candidate_receives_reference_solution") is not False:
            return _fail("REFERENCE_SOLUTION_VISIBLE")

        frozen = doc.get("post_freeze_selection_and_accounting")
        if not isinstance(frozen, Mapping):
            return _fail("POST_FREEZE_POLICY_NOT_OBJECT")
        for key in ("adaptive_case_selection", "case_replacement", "tuning_replay"):
            if frozen.get(key) is not False:
                return _fail("POST_FREEZE_LEAKAGE_CONTROL_UNPROVED", field=key)

        replay = verify_prewave(root)
        if replay.get("status") != "PASS" or replay.get("errors"):
            return _fail("EXACT_PREWAVE_REPLAY_FAILED", replay=replay)

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__NO_HIDDEN_VERIFIER_ATOM_PROVED_FROM_EXACT_PREWAVE_BOUNDARY",
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "atom_truth_authorized": True,
            "proof_basis": "EXACT_CONTENT_ADDRESSED_PREWAVE_INFORMATION_BOUNDARY_REPLAY",
            "binding_path": BINDING_PATH,
            "binding_git_blob_sha": actual_binding_sha,
            "prewave_verifier_path": PREWAVE_VERIFIER_PATH,
            "prewave_verifier_git_blob_sha": actual_verifier_sha,
            "prewave_replay": replay,
            "proved_constraint": {"op": "ATOM", "id": ATOM_ID},
            "other_condition_atoms_proved": [],
            "scope_boundary": (
                "EXACT_FROZEN_SPECIFICATION_ACCEPTANCE_PREWAVE_BINDING_ONLY__"
                "NO_CLAIM_FOR_ARBITRARY_CURSORBENCH_OR_HARBOR_CONTEXTS"
            ),
            "membership_self_certified": False,
            "whole_policy_condition_proved": False,
            "whole_specification_behavior_adequate": False,
            "whole_cursorbench_adequate": False,
            "terminal_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("PROOF_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))
