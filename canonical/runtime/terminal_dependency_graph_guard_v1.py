"""Fail-closed guard for the current terminal dependency graph V1."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_refinement_verifier_v1 import verify_certificate

SCHEMA = "PROJECT_BRAIN_TERMINAL_DEPENDENCY_GRAPH_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_TERMINAL_DEPENDENCY_GRAPH_RECEIPT_V1"
ALLOWED_LEAF_STATUSES = frozenset({"ENFORCED", "PROVED", "USER_AUTHORIZED", "ROOT", "UNRESOLVED"})
ALLOWED_LIFECYCLES = frozenset({"SPECIFIED", "IMPLEMENTED", "REFINEMENT_VERIFIED", "VERIFIED_LIVE"})


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": RECEIPT_SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _path(root: Path, raw: Any) -> Path | None:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        return None
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    return full if full.is_file() else None


def _verify_binding(root: Path, binding: Mapping[str, Any], *, prefix: str) -> str | None:
    if set(binding) != {"path", "git_blob_sha"}:
        return prefix + "_BINDING_INVALID"
    path = _path(root, binding.get("path"))
    if path is None:
        return prefix + "_PATH_INVALID"
    if binding.get("git_blob_sha") != git_blob_sha(path):
        return prefix + "_BLOB_DRIFT"
    return None


def verify_graph(raw: Mapping[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("GRAPH_NOT_OBJECT")
    if raw.get("schema") != SCHEMA:
        return _fail("GRAPH_SCHEMA_INVALID")
    if raw.get("claims_complete") is not False:
        return _fail("GRAPH_MUST_NOT_SELF_CLAIM_COMPLETENESS")
    leaves = raw.get("leaves")
    routes = raw.get("routes")
    if not isinstance(leaves, Sequence) or isinstance(leaves, (str, bytes)):
        return _fail("GRAPH_LEAVES_INVALID")
    if not isinstance(routes, Sequence) or isinstance(routes, (str, bytes)):
        return _fail("GRAPH_ROUTES_INVALID")
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]

    leaf_by_id: dict[str, Mapping[str, Any]] = {}
    for index, leaf in enumerate(leaves):
        if not isinstance(leaf, Mapping):
            return _fail("LEAF_NOT_OBJECT", index=index)
        leaf_id = str(leaf.get("id") or "").strip()
        if not leaf_id or leaf_id in leaf_by_id:
            return _fail("LEAF_ID_INVALID", index=index)
        if leaf.get("status") not in ALLOWED_LEAF_STATUSES:
            return _fail("LEAF_STATUS_INVALID", leaf_id=leaf_id)
        binding = leaf.get("binding")
        if binding is not None:
            if not isinstance(binding, Mapping):
                return _fail("LEAF_BINDING_INVALID", leaf_id=leaf_id)
            err = _verify_binding(root, binding, prefix="LEAF")
            if err:
                return _fail(err, leaf_id=leaf_id)
        leaf_by_id[leaf_id] = leaf

    checked_routes: list[str] = []
    for index, route in enumerate(routes):
        if not isinstance(route, Mapping):
            return _fail("ROUTE_NOT_OBJECT", index=index)
        route_id = str(route.get("id") or "").strip()
        lifecycle = route.get("lifecycle")
        if not route_id:
            return _fail("ROUTE_ID_REQUIRED", index=index)
        if lifecycle not in ALLOWED_LIFECYCLES:
            return _fail("ROUTE_LIFECYCLE_INVALID", route_id=route_id)
        if type(route.get("creditable")) is not bool or type(route.get("terminal_load_bearing")) is not bool:
            return _fail("ROUTE_BOOLEAN_INVALID", route_id=route_id)
        dep_ids = route.get("dependency_leaf_ids")
        if not isinstance(dep_ids, Sequence) or isinstance(dep_ids, (str, bytes)):
            return _fail("ROUTE_DEPENDENCIES_INVALID", route_id=route_id)
        for dep_id in dep_ids:
            if dep_id not in leaf_by_id:
                return _fail("ROUTE_DEPENDENCY_UNKNOWN", route_id=route_id, dependency=dep_id)

        refinement_leaf_id = route.get("executable_refinement_leaf_id")
        if lifecycle in {"REFINEMENT_VERIFIED", "VERIFIED_LIVE"}:
            if not refinement_leaf_id or refinement_leaf_id not in leaf_by_id:
                return _fail("REFINEMENT_DEPENDENCY_REQUIRED", route_id=route_id)
            leaf = leaf_by_id[refinement_leaf_id]
            if leaf.get("status") != "PROVED":
                return _fail("REFINEMENT_DEPENDENCY_NOT_PROVED", route_id=route_id)
            cert_binding = leaf.get("binding")
            if not isinstance(cert_binding, Mapping):
                return _fail("REFINEMENT_CERTIFICATE_BINDING_REQUIRED", route_id=route_id)
            cert_path = _path(root, cert_binding.get("path"))
            if cert_path is None:
                return _fail("REFINEMENT_CERTIFICATE_PATH_INVALID", route_id=route_id)
            try:
                cert = json.loads(cert_path.read_text(encoding="utf-8"))
            except Exception:
                return _fail("REFINEMENT_CERTIFICATE_JSON_INVALID", route_id=route_id)
            receipt = verify_certificate(cert, repo_root=root)
            if receipt.get("pass") is not True or receipt.get("refinement_verified") is not True:
                return _fail("REFINEMENT_CERTIFICATE_NOT_MECHANICALLY_VERIFIED", route_id=route_id)

        if lifecycle == "VERIFIED_LIVE":
            if route.get("creditable") is not True:
                return _fail("VERIFIED_LIVE_MUST_BE_CREDITABLE", route_id=route_id)
            deployment_leaf_id = route.get("deployment_identity_leaf_id")
            if not deployment_leaf_id or deployment_leaf_id not in leaf_by_id:
                return _fail("VERIFIED_LIVE_DEPLOYMENT_IDENTITY_REQUIRED", route_id=route_id)
            if leaf_by_id[deployment_leaf_id].get("status") not in {"PROVED", "ENFORCED"}:
                return _fail("VERIFIED_LIVE_DEPLOYMENT_IDENTITY_NOT_CLOSED", route_id=route_id)
        checked_routes.append(route_id)

    return {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "status": "PASS__TERMINAL_DEPENDENCY_GRAPH_STRUCTURALLY_VALID",
        "claims_complete": False,
        "leaf_count": len(leaf_by_id),
        "route_ids": sorted(checked_routes),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
