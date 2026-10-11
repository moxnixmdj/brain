"""Fail-closed final clean-room terminal gate.

This is deliberately the *last* gate, not a shortcut around unresolved work.
It cannot run to a terminal pass while CURRENT_TERMINAL_AUTHORITY still says the
global terminal predicate is false. Once a real terminal candidate exists, it
requires five exact independently verified conjuncts plus a donor-denied
clean-room replay bound to the same candidate bytes.

No conjunct can be inferred from another, no stale receipt is accepted, and no
caller assertion is treated as verification authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import current_one_shot_projection_v1 as projection
from canonical.runtime.runtime_cognition_credit_guard_v1 import assert_credit_path_cognition_governance

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_FINAL_TERMINAL_CLEANROOM_GATE_V1"

TERMINAL_PATH = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REQUIRED_CONJUNCTS = (
    "coverage",
    "adequacy",
    "ownership",
    "reliability",
    "resource_constraints",
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return value


def _resolve_receipt(
    root: Path,
    binding: Mapping[str, Any] | None,
    *,
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not isinstance(binding, Mapping):
        return None, [label + ":BINDING_MISSING"]
    rel = str(binding.get("path") or "").strip()
    expected = str(binding.get("git_blob_sha") or "").strip()
    if not rel:
        return None, [label + ":PATH_MISSING"]
    if not expected:
        return None, [label + ":GIT_BLOB_SHA_MISSING"]
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None, [label + ":PATH_ESCAPES_REPOSITORY"]
    if not path.is_file():
        return None, [label + ":FILE_MISSING:" + rel]
    actual = _git_blob(path)
    if actual != expected:
        errors.append(label + ":BLOB_MISMATCH:" + actual + ":" + expected)
    try:
        receipt = _load(path)
    except Exception as exc:
        errors.append(label + ":RECEIPT_LOAD_FAILED:" + type(exc).__name__)
        return None, errors
    return receipt, errors


def _current_open_truth(terminal: Mapping[str, Any]) -> dict[str, Any]:
    live = terminal.get("live_truth")
    live = live if isinstance(live, Mapping) else {}
    return {
        "terminal": live.get("terminal") is True,
        "current_U_empty_proved": live.get("current_U_empty_proved") is True,
        "complete_selected_context_ABC_closed": (
            live.get("complete_selected_context_ABC_closed") is True
        ),
        "D_finality_closed": live.get("D_finality_closed") is True,
        "frozen_terminal_family_pass_count": live.get(
            "frozen_terminal_family_pass_count"
        ),
        "frozen_terminal_family_open_count": live.get(
            "frozen_terminal_family_open_count"
        ),
        "frozen_atomic_predicates_proved": live.get(
            "frozen_atomic_predicates_proved"
        ),
        "frozen_atomic_predicates_unresolved": live.get(
            "frozen_atomic_predicates_unresolved"
        ),
        "r2_primary_internal_unsolved_count": live.get(
            "r2_primary_internal_unsolved_count"
        ),
        "r2_primary_internal_unsolved_cell": live.get(
            "r2_primary_internal_unsolved_cell"
        ),
    }


def evaluate(
    proof_manifest: Mapping[str, Any] | None = None,
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    assert_credit_path_cognition_governance(root)
    dynamic = projection.evaluate(root)
    if dynamic.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__CURRENT_AUTHORITY_PROJECTION_INVALID",
            "pass": False,
            "terminal_authority": False,
            "internal_unsolved": True,
            "projection": deepcopy(dynamic),
        }

    terminal_path = (root / TERMINAL_PATH).resolve(strict=True)
    terminal_path.relative_to(root)
    terminal = _load(terminal_path)
    open_truth = _current_open_truth(terminal)

    if not open_truth["terminal"]:
        return {
            "schema": SCHEMA,
            "status": "OPEN__INTERNAL_UNSOLVED__TERMINAL_PRECONDITIONS_NOT_CLOSED",
            "pass": False,
            "terminal_authority": False,
            "internal_unsolved": True,
            "final_cleanroom_executed": False,
            "current_terminal_authority_git_blob_sha": _git_blob(terminal_path),
            "current_terminal_pointer_revision": terminal.get("pointer_revision"),
            "open_truth": open_truth,
            "rule": (
                "FINAL_CLEANROOM_MAY_NOT_CREATE_A_TERMINAL_CANDIDATE__"
                "CURRENT_TERMINAL_PREDICATE_MUST_ALREADY_BE_TRUE"
            ),
        }

    if not isinstance(proof_manifest, Mapping):
        return {
            "schema": SCHEMA,
            "status": "OPEN__INTERNAL_UNSOLVED__FINAL_CLEANROOM_PROOF_MANIFEST_REQUIRED",
            "pass": False,
            "terminal_authority": False,
            "internal_unsolved": True,
            "final_cleanroom_executed": False,
            "open_truth": open_truth,
        }

    manifest = deepcopy(dict(proof_manifest))
    candidate_sha256 = str(manifest.get("candidate_sha256") or "").lower()
    errors: list[str] = []
    if not _valid_sha256(candidate_sha256):
        errors.append("CANDIDATE_SHA256_INVALID")

    conjunct_bindings = manifest.get("conjuncts")
    if not isinstance(conjunct_bindings, Mapping):
        conjunct_bindings = {}
        errors.append("CONJUNCT_BINDINGS_MISSING")

    conjunct_results: dict[str, Any] = {}
    for name in REQUIRED_CONJUNCTS:
        receipt, receipt_errors = _resolve_receipt(
            root,
            conjunct_bindings.get(name),
            label="CONJUNCT_" + name.upper(),
        )
        errors.extend(receipt_errors)
        if receipt is None:
            continue
        conjunct_results[name] = {
            "path": conjunct_bindings[name].get("path"),
            "git_blob_sha": conjunct_bindings[name].get("git_blob_sha"),
            "status": receipt.get("status"),
        }
        if receipt.get("pass") is not True:
            errors.append("CONJUNCT_" + name.upper() + ":PASS_NOT_TRUE")
        if receipt.get("independent_verifier_passed") is not True:
            errors.append(
                "CONJUNCT_" + name.upper() + ":INDEPENDENT_VERIFIER_NOT_PASSED"
            )
        if receipt.get("predicate") != name:
            errors.append("CONJUNCT_" + name.upper() + ":PREDICATE_MISMATCH")
        if receipt.get("value") != 1:
            errors.append("CONJUNCT_" + name.upper() + ":VALUE_NOT_ONE")
        if str(receipt.get("candidate_sha256") or "").lower() != candidate_sha256:
            errors.append("CONJUNCT_" + name.upper() + ":CANDIDATE_MISMATCH")

    cleanroom_binding = manifest.get("cleanroom")
    cleanroom, cleanroom_errors = _resolve_receipt(
        root,
        cleanroom_binding if isinstance(cleanroom_binding, Mapping) else None,
        label="CLEANROOM",
    )
    errors.extend(cleanroom_errors)
    cleanroom_result: dict[str, Any] | None = None
    if cleanroom is not None:
        cleanroom_result = {
            "path": cleanroom_binding.get("path"),
            "git_blob_sha": cleanroom_binding.get("git_blob_sha"),
            "status": cleanroom.get("status"),
        }
        required_true = (
            "pass",
            "independent_verifier_passed",
            "cleanroom_rebuilt_from_canonical_state",
            "donor_removed_or_unreachable",
            "network_denied",
            "behavior_preserved",
            "resource_constraints_satisfied",
        )
        for key in required_true:
            if cleanroom.get(key) is not True:
                errors.append("CLEANROOM:" + key.upper() + "_NOT_TRUE")
        if cleanroom.get("external_contribution_census_complete") is not True:
            errors.append("CLEANROOM:EXTERNAL_CONTRIBUTION_CENSUS_INCOMPLETE")
        if cleanroom.get("full_runtime_dependency_inventory_complete") is not True:
            errors.append("CLEANROOM:RUNTIME_DEPENDENCY_INVENTORY_INCOMPLETE")
        if cleanroom.get("runtime_cognition_dependency_class") != "MODEL_INDEPENDENT":
            errors.append("CLEANROOM:RUNTIME_COGNITION_NOT_MODEL_INDEPENDENT")
        for key in ("model_dependency_count","external_model_runtime_dependency_count","online_teacher_call_count","teacher_fallback_path_count"):
            if cleanroom.get(key) != 0:
                errors.append("CLEANROOM:" + key.upper() + "_NOT_ZERO")
        if cleanroom.get("copied_or_rehosted_teacher_present") is not False:
            errors.append("CLEANROOM:COPIED_OR_REHOSTED_TEACHER_NOT_EXPLICITLY_FALSE")
        if cleanroom.get("brain_owned_operative_artifact") is not True:
            errors.append("CLEANROOM:BRAIN_OWNED_OPERATIVE_ARTIFACT_NOT_TRUE")
        if cleanroom.get("operative_solver_role") not in {"BRAIN_OWNED_NATIVE_MECHANISM","BRAIN_OWNED_DERIVED_MECHANISM"}:
            errors.append("CLEANROOM:OPERATIVE_SOLVER_ROLE_NOT_BRAIN_OWNED")
        if cleanroom.get("undeclared_dependency_count") != 0:
            errors.append("CLEANROOM:UNDECLARED_DEPENDENCY_COUNT_NOT_ZERO")
        if str(cleanroom.get("candidate_sha256") or "").lower() != candidate_sha256:
            errors.append("CLEANROOM:CANDIDATE_MISMATCH")

    resource = conjunct_results.get("resource_constraints")
    all_pass = not errors and len(conjunct_results) == len(REQUIRED_CONJUNCTS)
    proof_basis = {
        "candidate_sha256": candidate_sha256,
        "conjuncts": conjunct_results,
        "cleanroom": cleanroom_result,
        "dynamic_projection": {
            "current_r2": dynamic.get("current_r2"),
            "current_terminal_authority": dynamic.get(
                "current_terminal_authority"
            ),
        },
    }
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FINAL_CLEANROOM_ALL_CONJUNCTS_AND_DONOR_INDEPENDENCE"
            if all_pass
            else "FAIL_CLOSED__FINAL_CLEANROOM_PROOF_INCOMPLETE_OR_INVALID"
        ),
        "pass": all_pass,
        "terminal_authority": all_pass,
        "internal_unsolved": not all_pass,
        "candidate_sha256": candidate_sha256 or None,
        "conjunct_count_required": len(REQUIRED_CONJUNCTS),
        "conjunct_count_verified": len(conjunct_results),
        "coverage": 1 if all_pass else 0,
        "adequacy": 1 if all_pass else 0,
        "ownership": 1 if all_pass else 0,
        "reliability": 1 if all_pass else 0,
        "resource_constraints_satisfied": 1 if all_pass else 0,
        "donor_independence_cleanroom": 1 if all_pass else 0,
        "errors": sorted(set(errors)),
        "proof_basis": proof_basis,
        "proof_basis_sha256": _sha(proof_basis),
        "verification_authority_mutation_allowed": False,
        "terminal_credit_delta": 1 if all_pass else 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
