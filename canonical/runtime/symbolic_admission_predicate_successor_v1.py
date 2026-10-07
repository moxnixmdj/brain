"""Symbolic admission predicate successor V1.

Restricted, deterministic predicate DSL for executable admission regions.

This runtime closes one deployment seam only: it lets a sound admission proof bind
to an executable symbolic region instead of an exact context digest. It never
self-certifies adequacy, soundness, scope completeness, U-empty, or terminal.

Every admitted predicate must carry an independently verified receipt binding the
exact predicate expression, scope, route, and adequacy certificate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SYMBOLIC_ADMISSION_PREDICATE_SUCCESSOR_V1"
_ALLOWED = {"TRUE", "FALSE", "HAS_PATH", "EQ", "IN", "AND", "OR", "NOT"}


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def expression_sha256(expr: Mapping[str, Any]) -> str:
    return "sha256:" + sha256(_canon(expr).encode("utf-8")).hexdigest()


def _path_get(ctx: Mapping[str, Any], path: Sequence[str]) -> tuple[bool, Any]:
    cur: Any = ctx
    for key in path:
        if not isinstance(cur, Mapping) or key not in cur:
            return False, None
        cur = cur[key]
    return True, cur


def _valid_path(path: Any) -> bool:
    return (
        isinstance(path, Sequence)
        and not isinstance(path, (str, bytes))
        and bool(path)
        and all(isinstance(x, str) and bool(x) for x in path)
    )


def validate_expression(expr: Any) -> tuple[bool, str | None]:
    if not isinstance(expr, Mapping):
        return False, "EXPR_MAPPING_REQUIRED"
    op = expr.get("op")
    if op not in _ALLOWED:
        return False, "EXPR_OP_INVALID"

    if op in {"TRUE", "FALSE"}:
        return (set(expr) == {"op"}, None if set(expr) == {"op"} else "EXPR_FIELDS_INVALID")

    if op == "HAS_PATH":
        if set(expr) != {"op", "path"} or not _valid_path(expr.get("path")):
            return False, "HAS_PATH_INVALID"
        return True, None

    if op == "EQ":
        if set(expr) != {"op", "path", "value"} or not _valid_path(expr.get("path")):
            return False, "EQ_INVALID"
        try:
            _canon(expr.get("value"))
        except Exception:
            return False, "EQ_VALUE_NOT_JSON"
        return True, None

    if op == "IN":
        values = expr.get("values")
        if (
            set(expr) != {"op", "path", "values"}
            or not _valid_path(expr.get("path"))
            or not isinstance(values, list)
            or not values
        ):
            return False, "IN_INVALID"
        try:
            encoded = [_canon(v) for v in values]
        except Exception:
            return False, "IN_VALUES_NOT_JSON"
        if len(encoded) != len(set(encoded)):
            return False, "IN_VALUES_DUPLICATE"
        return True, None

    if op in {"AND", "OR"}:
        args = expr.get("args")
        if set(expr) != {"op", "args"} or not isinstance(args, list) or not args:
            return False, op + "_INVALID"
        for child in args:
            ok, reason = validate_expression(child)
            if not ok:
                return False, op + "_CHILD_" + str(reason)
        return True, None

    if op == "NOT":
        if set(expr) != {"op", "arg"}:
            return False, "NOT_INVALID"
        ok, reason = validate_expression(expr.get("arg"))
        if not ok:
            return False, "NOT_CHILD_" + str(reason)
        return True, None

    return False, "UNREACHABLE"


def evaluate_expression(expr: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    ok, reason = validate_expression(expr)
    if not ok:
        raise ValueError(reason)
    if not isinstance(context, Mapping):
        raise ValueError("CONTEXT_MAPPING_REQUIRED")

    op = expr["op"]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "HAS_PATH":
        return _path_get(context, expr["path"])[0]
    if op == "EQ":
        found, value = _path_get(context, expr["path"])
        return found and _canon(value) == _canon(expr["value"])
    if op == "IN":
        found, value = _path_get(context, expr["path"])
        if not found:
            return False
        needle = _canon(value)
        return any(needle == _canon(v) for v in expr["values"])
    if op == "AND":
        return all(evaluate_expression(x, context) for x in expr["args"])
    if op == "OR":
        return any(evaluate_expression(x, context) for x in expr["args"])
    if op == "NOT":
        return not evaluate_expression(expr["arg"], context)
    raise ValueError("UNREACHABLE")


def admit_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an executable symbolic admission predicate and its authority receipt."""
    if not isinstance(manifest, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "MANIFEST_MAPPING_REQUIRED"}

    required_ids = ("predicate_id", "scope_id", "route_id", "adequacy_certificate_blob_sha")
    for key in required_ids:
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": key.upper() + "_REQUIRED"}

    expr = manifest.get("expression")
    ok, reason = validate_expression(expr)
    if not ok:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason}

    digest = expression_sha256(expr)
    if manifest.get("expression_sha256") != digest:
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "EXPRESSION_DIGEST_MISMATCH"}

    receipt = manifest.get("admission_soundness_receipt")
    if not isinstance(receipt, Mapping):
        return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": "SOUNDNESS_RECEIPT_REQUIRED"}

    expected = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "admission_implies_route_adequacy": True,
        "predicate_id": manifest["predicate_id"],
        "scope_id": manifest["scope_id"],
        "route_id": manifest["route_id"],
        "expression_sha256": digest,
        "adequacy_certificate_blob_sha": manifest["adequacy_certificate_blob_sha"],
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "SOUNDNESS_RECEIPT_BINDING_MISMATCH",
                "field": key,
            }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SYMBOLIC_ADMISSION_PREDICATE_DEPLOYABLE",
        "predicate_id": manifest["predicate_id"],
        "scope_id": manifest["scope_id"],
        "route_id": manifest["route_id"],
        "expression_sha256": digest,
        "executable": True,
        "soundness_authenticated": True,
        "selected_cover_complete_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
