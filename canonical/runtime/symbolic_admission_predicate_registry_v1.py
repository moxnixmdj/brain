from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_PREDICATE_REGISTRY_V2"
SCOPE_SCHEMA = "PROJECT_BRAIN_SYMBOLIC_SCOPE_PREDICATE_V1"
SCOPE_VERIFY_SCHEMA = "PROJECT_BRAIN_SYMBOLIC_SCOPE_PREDICATE_INDEPENDENT_VERIFICATION_V1"
PREDICATE_SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_PREDICATE_V1"
ADEQUACY_SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_SOUNDNESS_INDEPENDENT_VERIFICATION_V1"
_ALLOWED_OPS = {"ATOM", "AND", "OR", "NOT", "TRUE", "FALSE"}


def _canon(x: Any) -> str:
    return json.dumps(
        x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha256(x: Any) -> str:
    return "sha256:" + sha256(_canon(x).encode("utf-8")).hexdigest()


def _validate_ast(node: Any) -> bool:
    if not isinstance(node, Mapping):
        return False
    op = node.get("op")
    if op not in _ALLOWED_OPS:
        return False
    if op in {"TRUE", "FALSE"}:
        return set(node.keys()) == {"op"}
    if op == "ATOM":
        return (
            set(node.keys()) == {"op", "id"}
            and isinstance(node["id"], str)
            and bool(node["id"].strip())
        )
    if op == "NOT":
        return set(node.keys()) == {"op", "arg"} and _validate_ast(node["arg"])
    args = node.get("args")
    return (
        set(node.keys()) == {"op", "args"}
        and isinstance(args, Sequence)
        and not isinstance(args, (str, bytes))
        and len(args) > 0
        and all(_validate_ast(x) for x in args)
    )


def _norm(node: Mapping[str, Any]) -> dict[str, Any]:
    op = node["op"]
    if op in {"TRUE", "FALSE"}:
        return {"op": op}
    if op == "ATOM":
        return {"op": "ATOM", "id": node["id"].strip()}
    if op == "NOT":
        return {"op": "NOT", "arg": _norm(node["arg"])}
    args = [_norm(x) for x in node["args"]]
    args.sort(key=_canon)
    return {"op": op, "args": args}


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + "_INVALID")
    return value.strip()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "symbolic_successor_deployed": False,
        "selected_cover_complete": False,
        "u_empty": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _authenticate_scope(
    payload: Mapping[str, Any], *, scope_id: str, repo_root: str | Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    subject = resolve_receipt_bytes(
        payload.get("scope_predicate_reference"), repo_root=repo_root
    )
    verify = resolve_receipt_bytes(
        payload.get("scope_completeness_verification_reference"), repo_root=repo_root
    )
    sd = subject["document"]
    vd = verify["document"]

    if sd.get("schema") != SCOPE_SCHEMA:
        raise ValueError("SCOPE_PREDICATE_SCHEMA_INVALID")
    if sd.get("scope_id") != scope_id:
        raise ValueError("SCOPE_PREDICATE_SCOPE_MISMATCH")
    ast = sd.get("scope_predicate_ast")
    if not _validate_ast(ast):
        raise ValueError("SCOPE_PREDICATE_AST_INVALID")
    ast = _norm(ast)
    ast_digest = _sha256(ast)
    if sd.get("scope_predicate_ast_sha256") != ast_digest:
        raise ValueError("SCOPE_PREDICATE_AST_DIGEST_MISMATCH")

    if vd.get("schema") != SCOPE_VERIFY_SCHEMA:
        raise ValueError("SCOPE_VERIFY_SCHEMA_INVALID")
    if vd.get("subject_git_blob_sha") != subject["git_blob_sha"]:
        raise ValueError("SCOPE_VERIFY_SUBJECT_BLOB_MISMATCH")
    if vd.get("scope_id") != scope_id:
        raise ValueError("SCOPE_VERIFY_SCOPE_MISMATCH")
    if vd.get("scope_predicate_ast_sha256") != ast_digest:
        raise ValueError("SCOPE_VERIFY_AST_DIGEST_MISMATCH")
    if vd.get("scope_complete_for_s_trace") is not True:
        raise ValueError("SCOPE_COMPLETENESS_UNPROVED")
    if vd.get("independent_verified") is not True:
        raise ValueError("SCOPE_INDEPENDENT_VERIFICATION_REQUIRED")
    if vd.get("exact_byte_bound") is not True:
        raise ValueError("SCOPE_EXACT_BYTE_BINDING_REQUIRED")
    if vd.get("conclusion") != "success":
        raise ValueError("SCOPE_VERIFY_NOT_SUCCESS")
    _token(vd.get("verifier_id"), "SCOPE_VERIFIER_ID")
    return ast, subject, verify


def _authenticate_route(
    row: Mapping[str, Any], *, scope_id: str, repo_root: str | Path
) -> dict[str, Any]:
    rid = _token(row.get("route_id"), "ROUTE_ID")
    cid = _token(row.get("cell_id"), "CELL_ID")
    pid = _token(row.get("admission_predicate_id"), "ADMISSION_PREDICATE_ID")

    predicate = resolve_receipt_bytes(
        row.get("admission_predicate_reference"), repo_root=repo_root
    )
    adequacy = resolve_receipt_bytes(
        row.get("adequacy_certificate_reference"), repo_root=repo_root
    )
    verify = resolve_receipt_bytes(
        row.get("admission_soundness_verification_reference"), repo_root=repo_root
    )
    pd = predicate["document"]
    ad = adequacy["document"]
    vd = verify["document"]

    identity = {
        "scope_id": scope_id,
        "route_id": rid,
        "cell_id": cid,
        "admission_predicate_id": pid,
    }

    if pd.get("schema") != PREDICATE_SCHEMA:
        raise ValueError("ADMISSION_PREDICATE_SCHEMA_INVALID")
    for key, value in identity.items():
        if pd.get(key) != value:
            raise ValueError("ADMISSION_PREDICATE_IDENTITY_MISMATCH:" + key)
    ast = pd.get("admission_predicate_ast")
    if not _validate_ast(ast):
        raise ValueError("ADMISSION_PREDICATE_AST_INVALID")
    ast = _norm(ast)
    ast_digest = _sha256(ast)
    if pd.get("admission_predicate_ast_sha256") != ast_digest:
        raise ValueError("ADMISSION_PREDICATE_AST_DIGEST_MISMATCH")

    if ad.get("schema") != ADEQUACY_SCHEMA:
        raise ValueError("ADEQUACY_CERTIFICATE_SCHEMA_INVALID")
    for key, value in identity.items():
        if ad.get(key) != value:
            raise ValueError("ADEQUACY_CERTIFICATE_IDENTITY_MISMATCH:" + key)
    if ad.get("admission_predicate_git_blob_sha") != predicate["git_blob_sha"]:
        raise ValueError("ADEQUACY_PREDICATE_BLOB_MISMATCH")
    if ad.get("brain_owned") is not True:
        raise ValueError("ADEQUACY_BRAIN_OWNERSHIP_UNPROVED")
    if ad.get("deployed") is not True:
        raise ValueError("ADEQUACY_DEPLOYMENT_UNPROVED")
    if ad.get("resource_admissible") is not True:
        raise ValueError("ADEQUACY_RESOURCE_ADMISSIBILITY_UNPROVED")
    if ad.get("adequacy_proved") is not True or ad.get("conclusion") != "success":
        raise ValueError("ADEQUACY_UNPROVED")

    if vd.get("schema") != VERIFY_SCHEMA:
        raise ValueError("ADMISSION_VERIFY_SCHEMA_INVALID")
    for key, value in identity.items():
        if vd.get(key) != value:
            raise ValueError("ADMISSION_VERIFY_IDENTITY_MISMATCH:" + key)
    if vd.get("predicate_git_blob_sha") != predicate["git_blob_sha"]:
        raise ValueError("ADMISSION_VERIFY_PREDICATE_BLOB_MISMATCH")
    if vd.get("adequacy_certificate_git_blob_sha") != adequacy["git_blob_sha"]:
        raise ValueError("ADMISSION_VERIFY_ADEQUACY_BLOB_MISMATCH")
    if vd.get("admission_predicate_ast_sha256") != ast_digest:
        raise ValueError("ADMISSION_VERIFY_AST_DIGEST_MISMATCH")
    if vd.get("independent_verified") is not True:
        raise ValueError("ADMISSION_INDEPENDENT_VERIFICATION_REQUIRED")
    if vd.get("exact_byte_bound") is not True:
        raise ValueError("ADMISSION_EXACT_BYTE_BINDING_REQUIRED")
    if vd.get("admission_implies_route_adequacy") is not True:
        raise ValueError("ADMISSION_IMPLIES_ADEQUACY_UNPROVED")
    if vd.get("conclusion") != "success":
        raise ValueError("ADMISSION_VERIFY_NOT_SUCCESS")
    _token(vd.get("verifier_id"), "ADMISSION_VERIFIER_ID")

    return {
        **identity,
        "admission_predicate_ast": ast,
        "admission_predicate_ast_sha256": ast_digest,
        "admission_predicate_path": predicate["path"],
        "admission_predicate_blob_sha": predicate["git_blob_sha"],
        "adequacy_certificate_path": adequacy["path"],
        "adequacy_certificate_blob_sha": adequacy["git_blob_sha"],
        "admission_soundness_verification_path": verify["path"],
        "admission_soundness_verification_blob_sha": verify["git_blob_sha"],
    }


def evaluate(
    payload: Mapping[str, Any], *, repo_root: str | Path
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    scope_id = str(payload.get("scope_id") or "").strip()
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")

    try:
        scope_ast, scope_subject, scope_verify = _authenticate_scope(
            payload, scope_id=scope_id, repo_root=repo_root
        )
    except (ValueError, ReceiptResolutionError) as exc:
        return _fail(
            "SCOPE_AUTHENTICATION_FAILED",
            error=type(exc).__name__ + ":" + str(exc),
        )

    routes = payload.get("routes")
    if not isinstance(routes, Sequence) or isinstance(routes, (str, bytes)) or not routes:
        return _fail("ROUTES_REQUIRED")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(routes):
        if not isinstance(row, Mapping):
            return _fail("ROUTE_NOT_MAPPING", index=i)
        try:
            item = _authenticate_route(row, scope_id=scope_id, repo_root=repo_root)
        except (ValueError, ReceiptResolutionError) as exc:
            return _fail(
                "ROUTE_AUTHENTICATION_FAILED",
                index=i,
                error=type(exc).__name__ + ":" + str(exc),
            )
        pid = item["admission_predicate_id"]
        if pid in seen:
            return _fail("ADMISSION_PREDICATE_ID_DUPLICATE", index=i, predicate_id=pid)
        seen.add(pid)
        normalized.append(item)

    normalized.sort(
        key=lambda x: (
            x["admission_predicate_id"],
            x["route_id"],
            x["cell_id"],
        )
    )

    union = _norm(
        {"op": "OR", "args": [r["admission_predicate_ast"] for r in normalized]}
    )
    residual = _norm(
        {"op": "AND", "args": [scope_ast, {"op": "NOT", "arg": union}]}
    )

    registry_manifest = {
        "scope_id": scope_id,
        "scope_predicate_path": scope_subject["path"],
        "scope_predicate_blob_sha": scope_subject["git_blob_sha"],
        "scope_verification_path": scope_verify["path"],
        "scope_verification_blob_sha": scope_verify["git_blob_sha"],
        "scope_predicate_sha256": _sha256(scope_ast),
        "routes": [
            {
                "cell_id": r["cell_id"],
                "route_id": r["route_id"],
                "admission_predicate_id": r["admission_predicate_id"],
                "admission_predicate_path": r["admission_predicate_path"],
                "admission_predicate_blob_sha": r["admission_predicate_blob_sha"],
                "adequacy_certificate_path": r["adequacy_certificate_path"],
                "adequacy_certificate_blob_sha": r["adequacy_certificate_blob_sha"],
                "admission_soundness_verification_path": r[
                    "admission_soundness_verification_path"
                ],
                "admission_soundness_verification_blob_sha": r[
                    "admission_soundness_verification_blob_sha"
                ],
                "admission_predicate_ast_sha256": r[
                    "admission_predicate_ast_sha256"
                ],
            }
            for r in normalized
        ],
    }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CONTENT_AUTHENTICATED_SYMBOLIC_ADMISSION_REGISTRY",
        "scope_id": scope_id,
        "registry_manifest": registry_manifest,
        "registry_manifest_sha256": _sha256(registry_manifest),
        "sound_admission_union_ast": union,
        "sound_admission_union_ast_sha256": _sha256(union),
        "residual_definition": "S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE",
        "residual_ast": residual,
        "residual_ast_sha256": _sha256(residual),
        "symbolic_successor_deployed": True,
        "opaque_caller_soundness_claims_permitted": False,
        "selected_cover_complete": False,
        "u_empty": False,
        "terminal": False,
        "terminal_credit_delta": 0,
        "next": (
            "PROVE_THIS_EXACT_CONTENT_BOUND_RESIDUAL_UNSAT_WITH_AN_INDEPENDENT_"
            "VERIFIER_OR_EXTRACT_ONE_CONSTRUCTIVE_SAT_WITNESS_CLASS"
        ),
    }
