from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_ROOT_DECISION_GATE_V1"
SCOPE_ID = "scope://opus55/observable-trace"
ALLOWED_PROOF_KINDS = {
    "FULL_SCOPE_DB_COVER",
    "TARGET_ESCAPE_NONOCCUPANCY",
    "GENERATOR_CLOSURE_SCOPE_COMPLETE",
    "SELECTED_COVER_COMPLEMENT_UNSAT",
}


def _content_binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and isinstance(value.get("git_blob_sha"), str)
        and len(value["git_blob_sha"]) == 40
        and all(ch in "0123456789abcdef" for ch in value["git_blob_sha"])
    )


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    digest = sha1()
    digest.update(f"blob {len(data)}".encode("ascii") + bytes([0]))
    digest.update(data)
    return digest.hexdigest()


def _load_bound_json(
    binding: Any,
    repo_root: Path | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not _content_binding(binding):
        return None, "BINDING_SHAPE_INVALID"
    if repo_root is None:
        return None, "REPOSITORY_ROOT_REQUIRED"

    relative = Path(binding["path"])
    if relative.is_absolute():
        return None, "ABSOLUTE_PATH_FORBIDDEN"

    root = repo_root.resolve()
    try:
        candidate = (root / relative).resolve(strict=True)
        candidate.relative_to(root)
    except FileNotFoundError:
        return None, "BOUND_FILE_MISSING"
    except (OSError, RuntimeError, ValueError):
        return None, "PATH_ESCAPES_OR_UNREADABLE"

    if not candidate.is_file():
        return None, "BOUND_FILE_MISSING"
    if _git_blob_sha(candidate) != binding["git_blob_sha"]:
        return None, "GIT_BLOB_SHA_MISMATCH"

    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "BOUND_JSON_UNREADABLE"
    if not isinstance(payload, dict):
        return None, "BOUND_JSON_NOT_OBJECT"
    return payload, None


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "x_decided": False,
        "x": None,
        "u_empty": False,
        "abc_closed": False,
        "d_finality_required": True,
        "terminal": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(
    payload: Mapping[str, Any],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    declaration = payload.get("closure_receipt")
    if not isinstance(declaration, Mapping):
        return _fail("CLOSURE_RECEIPT_REQUIRED")

    proof_binding = declaration.get("proof_artifact")
    verifier_binding = declaration.get("verifier_receipt_artifact")
    proof, proof_error = _load_bound_json(proof_binding, repo_root)
    verifier, verifier_error = _load_bound_json(verifier_binding, repo_root)
    if proof_error is not None or verifier_error is not None:
        return _fail(
            "CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED",
            proof_error=proof_error,
            verifier_error=verifier_error,
        )

    proof = proof or {}
    verifier = verifier or {}

    kind = proof.get("proof_kind")
    if kind not in ALLOWED_PROOF_KINDS:
        return _fail("PROOF_KIND_INVALID")
    if proof.get("conclusion") != "success":
        return _fail("SUCCESS_CONCLUSION_REQUIRED")

    scope_id = str(proof.get("scope_id") or "").strip()
    if scope_id != SCOPE_ID:
        return _fail("SCOPE_ID_REQUIRED", expected=SCOPE_ID, observed=scope_id or None)

    if verifier.get("independent_verified") is not True:
        return _fail("INDEPENDENT_VERIFICATION_REQUIRED")
    if verifier.get("exact_byte_bound") is not True:
        return _fail("EXACT_BYTE_BINDING_REQUIRED")
    if verifier.get("conclusion") != "success":
        return _fail("VERIFIER_SUCCESS_CONCLUSION_REQUIRED")
    if verifier.get("proof_artifact") != proof_binding:
        return _fail("VERIFIER_PROOF_BINDING_MISMATCH")

    for field in ("proof_kind", "scope_id", "conclusion"):
        if field in declaration and declaration.get(field) != proof.get(field):
            return _fail("DECLARATION_PROOF_MISMATCH", field=field)

    if kind == "FULL_SCOPE_DB_COVER":
        if proof.get("s_trace_subset_db") is not True:
            return _fail("FULL_SCOPE_DB_COVER_UNPROVED")
        rule = "S_TRACE_SUBSET_DB_IMPLIES_U_SUBSET_DB_IMPLIES_U_INTERSECTION_E_EMPTY"
    elif kind == "TARGET_ESCAPE_NONOCCUPANCY":
        if proof.get("u_intersection_escape_empty") is not True:
            return _fail("TARGET_ESCAPE_NONOCCUPANCY_UNPROVED")
        rule = "DIRECT_TARGET_ESCAPE_NONOCCUPANCY"
    elif kind == "GENERATOR_CLOSURE_SCOPE_COMPLETE":
        required = (
            "generator_basis_complete",
            "all_generators_covered",
            "all_transforms_abc_preserving",
            "all_useful_contexts_reachable",
        )
        missing = [field for field in required if proof.get(field) is not True]
        if missing:
            return _fail("GENERATOR_CLOSURE_PREMISES_UNPROVED", missing=missing)
        rule = "SCOPE_COMPLETE_GENERATOR_INDUCTION_COVERS_ALL_USEFUL_CONTEXTS"
    else:
        required = ("every_admission_sound", "residual_complement_unsat")
        missing = [field for field in required if proof.get(field) is not True]
        if missing:
            return _fail("SELECTED_COVER_COMPLEMENT_PREMISES_UNPROVED", missing=missing)
        rule = "SOUND_ADMISSION_UNION_PLUS_UNSAT_COMPLEMENT_COVERS_SCOPE"

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__TERMINAL_ROOT_NOT_X_PROVED",
        "proof_kind": kind,
        "scope_id": scope_id,
        "proof_rule": rule,
        "x_decided": True,
        "x": False,
        "u_empty": True,
        "abc_closed": True,
        "d_finality_required": True,
        "terminal": False,
        "terminal_credit_delta": 0,
        "next": "FREEZE_EXACT_CREDITED_ROUTES__RECOMPUTE_D__DELETE_DONORS__RUN_INDEPENDENT_CLEAN_ROOM_REPLAY",
    }
