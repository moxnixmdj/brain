from __future__ import annotations
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_PREDICATE_REGISTRY_V1"
_ALLOWED_OPS = {"ATOM", "AND", "OR", "NOT", "TRUE", "FALSE"}

def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _sha256(x: Any) -> str:
    return "sha256:" + sha256(_canon(x).encode("utf-8")).hexdigest()

def _hex40(x: Any) -> bool:
    return isinstance(x, str) and len(x) == 40 and all(c in "0123456789abcdef" for c in x)

def _validate_ast(node: Any) -> bool:
    if not isinstance(node, Mapping):
        return False
    op = node.get("op")
    if op not in _ALLOWED_OPS:
        return False
    if op in {"TRUE", "FALSE"}:
        return set(node.keys()) == {"op"}
    if op == "ATOM":
        return set(node.keys()) == {"op", "id"} and isinstance(node["id"], str) and bool(node["id"].strip())
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

def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    scope_id = str(payload.get("scope_id") or "").strip()
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")

    scope_ast = payload.get("scope_predicate")
    if not _validate_ast(scope_ast):
        return _fail("SCOPE_PREDICATE_AST_INVALID")
    scope_ast = _norm(scope_ast)

    routes = payload.get("routes")
    if not isinstance(routes, Sequence) or isinstance(routes, (str, bytes)) or not routes:
        return _fail("ROUTES_REQUIRED")

    normalized = []
    seen = set()
    for i, row in enumerate(routes):
        if not isinstance(row, Mapping):
            return _fail("ROUTE_NOT_MAPPING", index=i)
        rid = str(row.get("route_id") or "").strip()
        cid = str(row.get("cell_id") or "").strip()
        pid = str(row.get("admission_predicate_id") or "").strip()
        if not rid or not cid or not pid or pid in seen:
            return _fail("ROUTE_IDENTITY_INVALID", index=i)
        seen.add(pid)

        for field in (
            "admission_predicate_blob_sha",
            "adequacy_certificate_blob_sha",
            "admission_soundness_receipt_blob_sha",
        ):
            if not _hex40(row.get(field)):
                return _fail("INVALID_GIT_BLOB_SHA", index=i, field=field)

        ast = row.get("admission_predicate_ast")
        if not _validate_ast(ast):
            return _fail("ADMISSION_PREDICATE_AST_INVALID", route_id=rid)
        ast = _norm(ast)
        ast_digest = _sha256(ast)
        if row.get("admission_predicate_ast_sha256") != ast_digest:
            return _fail("ADMISSION_PREDICATE_AST_DIGEST_MISMATCH", route_id=rid)

        sr = row.get("admission_soundness_receipt")
        if (
            not isinstance(sr, Mapping)
            or sr.get("independent_verified") is not True
            or sr.get("exact_byte_bound") is not True
            or sr.get("conclusion") != "success"
            or sr.get("admission_implies_route_adequacy") is not True
        ):
            return _fail("ADMISSION_SOUNDNESS_UNPROVED", route_id=rid)

        normalized.append({
            "cell_id": cid,
            "route_id": rid,
            "admission_predicate_id": pid,
            "admission_predicate_blob_sha": row["admission_predicate_blob_sha"],
            "adequacy_certificate_blob_sha": row["adequacy_certificate_blob_sha"],
            "admission_soundness_receipt_blob_sha": row["admission_soundness_receipt_blob_sha"],
            "admission_predicate_ast": ast,
            "admission_predicate_ast_sha256": ast_digest,
        })

    normalized.sort(key=lambda x: (x["admission_predicate_id"], x["route_id"], x["cell_id"]))

    union = _norm({"op": "OR", "args": [r["admission_predicate_ast"] for r in normalized]})
    residual = _norm({"op": "AND", "args": [scope_ast, {"op": "NOT", "arg": union}]})

    registry_manifest = {
        "scope_id": scope_id,
        "scope_predicate_sha256": _sha256(scope_ast),
        "routes": [{
            "cell_id": r["cell_id"],
            "route_id": r["route_id"],
            "admission_predicate_id": r["admission_predicate_id"],
            "admission_predicate_blob_sha": r["admission_predicate_blob_sha"],
            "adequacy_certificate_blob_sha": r["adequacy_certificate_blob_sha"],
            "admission_soundness_receipt_blob_sha": r["admission_soundness_receipt_blob_sha"],
            "admission_predicate_ast_sha256": r["admission_predicate_ast_sha256"],
        } for r in normalized],
    }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SYMBOLIC_ADMISSION_SUCCESSOR_DEPLOYED",
        "scope_id": scope_id,
        "registry_manifest": registry_manifest,
        "registry_manifest_sha256": _sha256(registry_manifest),
        "sound_admission_union_ast": union,
        "sound_admission_union_ast_sha256": _sha256(union),
        "residual_definition": "S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE",
        "residual_ast": residual,
        "residual_ast_sha256": _sha256(residual),
        "symbolic_successor_deployed": True,
        "selected_cover_complete": False,
        "u_empty": False,
        "terminal": False,
        "terminal_credit_delta": 0,
        "next": "PROVE_RESIDUAL_AST_UNSAT_WITH_AN_INDEPENDENT_CONTENT_BOUND_SOLVER_OR_EXTRACT_ONE_SAT_WITNESS_CLASS",
    }
