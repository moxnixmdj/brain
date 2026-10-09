"""Authority for the exact CCoB/CCyB/TLAC bounded-rival registry.

The registry is complete only by construction for the named task scope:
REGCAP_CCOB_CCYB_TLAC_BOUNDED_RIVAL_TASK_V1.

Concept semantics and every discriminator outcome are independently rebound to
the source-backed regulatory-capital contrastive matrix before an authority
receipt is emitted.  Nothing here claims open-world regulatory-capital
completeness.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
from canonical.runtime import regcap_contrastive_discriminator_matrix_v1 as matrix

SCHEMA = "PROJECT_BRAIN_REGCAP_BOUNDED_RIVAL_REGISTRY_AUTHORITY_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_REGCAP_BOUNDED_RIVAL_REGISTRY_AUTHORITY_REQUEST_V1"
REGISTRY_PATH = "canonical/evidence/REGCAP_BOUNDED_RIVAL_REGISTRY_V1.json"
REGISTRY_GIT_BLOB_SHA = "7deb684b4d827a811b9bdde62112593192bf2524"
REGISTRY_ID = "REGCAP_CCOB_CCYB_TLAC_BOUNDED_RIVAL_REGISTRY_V1"
SCOPE_ID = "REGCAP_CCOB_CCYB_TLAC_BOUNDED_RIVAL_TASK_V1"
ROOT = Path(__file__).resolve().parents[2]


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


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "scope_completeness_authenticated": False,
        "concept_semantics_authenticated": False,
        "open_world_ontology_complete": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def load_registry(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = (root / REGISTRY_PATH).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("REGISTRY_FILE_INVALID")
    raw = path.read_bytes()
    blob = _git_blob(raw)
    if blob != REGISTRY_GIT_BLOB_SHA:
        raise ValueError("REGISTRY_GIT_BLOB_DRIFT:" + blob)
    doc = json.loads(raw.decode("utf-8"))
    checked = universe.validate_registry(doc)
    normalized = checked["registry"]
    if normalized["registry_id"] != REGISTRY_ID:
        raise ValueError("REGISTRY_ID_MISMATCH")
    if normalized["scope_id"] != SCOPE_ID:
        raise ValueError("REGISTRY_SCOPE_MISMATCH")
    if set(checked["concept_ids"]) != set(matrix.DOMAIN):
        raise ValueError("REGISTRY_CONCEPT_DOMAIN_MISMATCH")
    return {
        "registry": dict(doc),
        "normalized_registry": normalized,
        "registry_sha256": checked["registry_sha256"],
        "registry_git_blob_sha": blob,
        "concept_ids": list(checked["concept_ids"]),
    }


def _matrix_bindings_match(
    normalized_registry: Mapping[str, Any],
    verified_matrix: Mapping[str, Any],
) -> tuple[bool, str | None]:
    rows = {
        str(row.get("observation_id") or ""): row
        for row in normalized_registry.get("observations", [])
        if isinstance(row, Mapping)
    }
    matrix_rows = {
        str(row.get("observation_id") or ""): row
        for row in verified_matrix.get("observations", [])
        if isinstance(row, Mapping)
    }
    if set(rows) != set(matrix_rows):
        return False, "OBSERVATION_ID_SET_MISMATCH"
    for oid, row in rows.items():
        if row.get("outcome_map_complete") is not True:
            return False, "REGISTRY_OUTCOME_MAP_NOT_COMPLETE:" + oid
        if dict(row.get("outcomes") or {}) != dict(
            matrix_rows[oid].get("outcomes") or {}
        ):
            return False, "OBSERVATION_OUTCOME_MISMATCH:" + oid
    return True, None


def verify_authority_request(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    projection_verifier=matrix.verify_projection_pack,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
            return _base("FAIL_CLOSED", reason="REQUEST_SCHEMA_INVALID")
        allowed = {"schema", "registry_id", "scope_id"}
        extra = set(request) - allowed
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_REQUEST_FIELDS:"
                + ",".join(sorted(str(x) for x in extra)),
            )
        if request.get("registry_id") != REGISTRY_ID:
            return _base("FAIL_CLOSED", reason="REGISTRY_ID_MISMATCH")
        if request.get("scope_id") != SCOPE_ID:
            return _base("FAIL_CLOSED", reason="SCOPE_ID_MISMATCH")

        checked = load_registry(repo_root=repo_root)
        matrix_result = matrix.verify_matrix(
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )
        if matrix_result.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="REGCAP_MATRIX_AUTHORITY_FAILED",
                matrix_result=matrix_result,
            )
        if set(matrix_result.get("candidate_domain") or []) != set(matrix.DOMAIN):
            return _base("FAIL_CLOSED", reason="MATRIX_CONCEPT_DOMAIN_MISMATCH")
        matches, reason = _matrix_bindings_match(
            checked["normalized_registry"],
            matrix_result,
        )
        if not matches:
            return _base("FAIL_CLOSED", reason=str(reason))

        receipt_core = {
            "pass": True,
            "schema": universe.AUTHORITY_SCHEMA,
            "registry_sha256": checked["registry_sha256"],
            "registry_id": REGISTRY_ID,
            "scope_id": SCOPE_ID,
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
        }
        receipt = dict(receipt_core)
        receipt["receipt_sha256"] = _sha(receipt_core)
        receipt.update({
            "bounded_scope_complete_for": list(matrix.DOMAIN),
            "open_world_ontology_complete": False,
            "matrix_sha256": matrix_result.get("matrix_sha256"),
            "registry_git_blob_sha": checked["registry_git_blob_sha"],
            "matrix_result": deepcopy(dict(matrix_result)),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        })
        return receipt
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def resolve_authenticated_registry(
    *,
    repo_root: str | Path | None = None,
    projection_verifier=matrix.verify_projection_pack,
) -> dict[str, Any]:
    try:
        checked = load_registry(repo_root=repo_root)
        request = {
            "schema": REQUEST_SCHEMA,
            "registry_id": REGISTRY_ID,
            "scope_id": SCOPE_ID,
        }

        def verifier(raw: Mapping[str, Any]) -> Mapping[str, Any] | None:
            return verify_authority_request(
                raw,
                repo_root=repo_root,
                projection_verifier=projection_verifier,
            )

        return universe.resolve(
            checked["registry"],
            {},
            ambiguity_owner="SYSTEM_MODEL",
            authority_receipt=request,
            authority_verifier=verifier,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
