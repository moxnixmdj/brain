"""Fail-closed guard for the current terminal dependency graph V1.

The graph is an inventory of terminal-load-bearing obligations. It does not
prove its own completeness. In particular, IMPLEMENTED is strictly weaker than
REFINEMENT_VERIFIED, and no creditable route may be represented as live without
an independently bound refinement-verification receipt.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CURRENT_TERMINAL_DEPENDENCY_GRAPH_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_TERMINAL_DEPENDENCY_GRAPH_GUARD_RECEIPT_V1"
LEAF_STATUSES = frozenset(
    {"ENFORCED", "PROVED", "USER_AUTHORIZED", "ROOT", "UNRESOLVED"}
)
ROUTE_LIFECYCLES = frozenset(
    {"SPECIFIED", "IMPLEMENTED", "REFINEMENT_VERIFIED", "VERIFIED_LIVE"}
)


def _attack_families(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    rows = [str(x).strip() for x in value]
    # An empty list is a valid explicit representation of unknown applicability.
    # The caller records it as an unresolved terminal obligation rather than
    # silently treating it as covered.
    return all(rows) and len(rows) == len(set(rows))

_REQUIRED_FIELDS = frozenset(
    {
        "schema",
        "date",
        "terminal_objective",
        "nodes",
        "terminal_closure",
        "terminal_credit_delta",
    }
)


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


def _repo_path(root: Path, raw: Any) -> Path | None:
    value = str(raw or "").strip()
    if not value:
        return None
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        return None
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    return full if full.is_file() else None


def _bound_file(
    raw: Any, *, root: Path, label: str
) -> tuple[Path | None, str | None]:
    if not isinstance(raw, Mapping) or set(raw) != {"path", "git_blob_sha"}:
        return None, f"{label}_BINDING_INVALID"
    path = _repo_path(root, raw.get("path"))
    if path is None:
        return None, f"{label}_PATH_INVALID"
    if raw.get("git_blob_sha") != git_blob_sha(path):
        return None, f"{label}_BLOB_DRIFT"
    return path, None


def _load_json(path: Path, *, label: str) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, Mapping) else None


def validate_graph(
    raw: Mapping[str, Any], *, repo_root: Path | None = None
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("GRAPH_NOT_OBJECT")
    if raw.get("schema") != SCHEMA:
        return _fail("GRAPH_SCHEMA_INVALID")
    if set(raw) != _REQUIRED_FIELDS:
        return _fail(
            "GRAPH_FIELD_SET_INVALID",
            missing_fields=sorted(_REQUIRED_FIELDS - set(raw)),
            extra_fields=sorted(set(raw) - _REQUIRED_FIELDS),
        )
    if not str(raw.get("terminal_objective") or "").strip():
        return _fail("TERMINAL_OBJECTIVE_REQUIRED")
    if type(raw.get("terminal_closure")) is not bool:
        return _fail("TERMINAL_CLOSURE_FLAG_INVALID")
    if raw.get("terminal_credit_delta") != 0:
        return _fail("NONZERO_TERMINAL_CREDIT_FORBIDDEN")

    nodes = raw.get("nodes")
    if (
        not isinstance(nodes, Sequence)
        or isinstance(nodes, (str, bytes))
        or not nodes
    ):
        return _fail("GRAPH_NODES_REQUIRED")

    root = (
        Path(repo_root)
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    seen: set[str] = set()
    unresolved: list[str] = []
    route_states: dict[str, str] = {}

    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            return _fail("NODE_NOT_OBJECT", index=index)
        node_id = str(node.get("id") or "").strip()
        if not node_id or node_id in seen:
            return _fail("NODE_ID_INVALID", index=index)
        seen.add(node_id)
        kind = str(node.get("kind") or "").strip()

        if kind == "LEAF":
            if set(node) != {"id", "kind", "status", "attack_families", "note"}:
                return _fail("LEAF_FIELD_SET_INVALID", node_id=node_id)
            if not _attack_families(node.get("attack_families")):
                return _fail("ATTACK_FAMILIES_INVALID", node_id=node_id)
            status = node.get("status")
            if status not in LEAF_STATUSES:
                return _fail("LEAF_STATUS_INVALID", node_id=node_id)
            if not node.get("attack_families"):
                unresolved.append(node_id + "::ATTACK_APPLICABILITY")
            if status == "UNRESOLVED":
                unresolved.append(node_id)
            continue

        if kind != "ROUTE":
            return _fail("NODE_KIND_UNSUPPORTED", node_id=node_id)

        required = {
            "id",
            "kind",
            "lifecycle",
            "creditable",
            "terminal_authority",
            "implementation",
            "refinement",
            "live_authority_status",
            "attack_families",
            "note",
        }
        if set(node) != required:
            return _fail("ROUTE_FIELD_SET_INVALID", node_id=node_id)

        if not _attack_families(node.get("attack_families")):
            return _fail("ATTACK_FAMILIES_INVALID", node_id=node_id)

        lifecycle = node.get("lifecycle")
        if lifecycle not in ROUTE_LIFECYCLES:
            return _fail("ROUTE_LIFECYCLE_INVALID", node_id=node_id)
        if type(node.get("creditable")) is not bool:
            return _fail("ROUTE_CREDITABLE_FLAG_INVALID", node_id=node_id)
        if type(node.get("terminal_authority")) is not bool:
            return _fail("ROUTE_TERMINAL_AUTHORITY_FLAG_INVALID", node_id=node_id)
        if node.get("live_authority_status") not in LEAF_STATUSES:
            return _fail("ROUTE_LIVE_AUTHORITY_STATUS_INVALID", node_id=node_id)

        implementation = node.get("implementation")
        if lifecycle != "SPECIFIED":
            _, reason = _bound_file(
                implementation, root=root, label=f"{node_id}_IMPLEMENTATION"
            )
            if reason:
                return _fail(reason, node_id=node_id)

        refinement = node.get("refinement")
        if not isinstance(refinement, Mapping):
            return _fail("ROUTE_REFINEMENT_NOT_OBJECT", node_id=node_id)
        refinement_status = refinement.get("status")
        if refinement_status not in LEAF_STATUSES:
            return _fail("ROUTE_REFINEMENT_STATUS_INVALID", node_id=node_id)

        cert = refinement.get("certificate")
        if cert is not None:
            _, reason = _bound_file(
                cert, root=root, label=f"{node_id}_REFINEMENT_CERTIFICATE"
            )
            if reason:
                return _fail(reason, node_id=node_id)

        receipt = refinement.get("verification_receipt")
        needs_verified = lifecycle in {"REFINEMENT_VERIFIED", "VERIFIED_LIVE"}
        if needs_verified:
            if refinement_status != "PROVED":
                return _fail("REFINEMENT_PROOF_REQUIRED", node_id=node_id)
            receipt_path, reason = _bound_file(
                receipt,
                root=root,
                label=f"{node_id}_REFINEMENT_RECEIPT",
            )
            if reason:
                return _fail(reason, node_id=node_id)
            receipt_obj = _load_json(
                receipt_path, label=f"{node_id}_REFINEMENT_RECEIPT"
            )
            if receipt_obj is None:
                return _fail("REFINEMENT_RECEIPT_INVALID_JSON", node_id=node_id)
            if receipt_obj.get("subject_id") != node_id:
                return _fail("REFINEMENT_RECEIPT_SUBJECT_MISMATCH", node_id=node_id)
            if receipt_obj.get("refinement_verified") is not True:
                return _fail("REFINEMENT_RECEIPT_NOT_VERIFIED", node_id=node_id)

        if node.get("creditable") is True and not needs_verified:
            return _fail("CREDITABLE_ROUTE_REFINEMENT_REQUIRED", node_id=node_id)

        if lifecycle == "VERIFIED_LIVE":
            if node.get("live_authority_status") not in {
                "ENFORCED",
                "PROVED",
                "USER_AUTHORIZED",
            }:
                return _fail("VERIFIED_LIVE_AUTHORITY_UNPROVED", node_id=node_id)

        if node.get("terminal_authority") is True and lifecycle != "VERIFIED_LIVE":
            return _fail("TERMINAL_AUTHORITY_REQUIRES_VERIFIED_LIVE", node_id=node_id)

        if not node.get("attack_families"):
            unresolved.append(node_id + "::ATTACK_APPLICABILITY")
        if refinement_status == "UNRESOLVED":
            unresolved.append(node_id + "::EXECUTABLE_REFINEMENT")
        if node.get("live_authority_status") == "UNRESOLVED":
            unresolved.append(node_id + "::LIVE_AUTHORITY")
        route_states[node_id] = str(lifecycle)

    if raw.get("terminal_closure") is True and unresolved:
        return _fail(
            "TERMINAL_CLOSURE_WITH_UNRESOLVED_LEAVES",
            unresolved=sorted(unresolved),
        )

    return {
        "pass": True,
        "schema": RECEIPT_SCHEMA,
        "status": "PASS__TERMINAL_DEPENDENCY_GRAPH_STRUCTURALLY_VALID",
        "node_count": len(nodes),
        "route_states": route_states,
        "unresolved": sorted(unresolved),
        "terminal_closure": bool(raw.get("terminal_closure")),
        "graph_completeness_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
