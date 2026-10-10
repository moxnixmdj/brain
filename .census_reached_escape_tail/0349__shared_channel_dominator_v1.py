from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SHARED_CHANNEL_DOMINATOR_CERT_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_SHARED_CHANNEL_DOMINATOR_RESULT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class CertificateError(RuntimeError):
    pass


def _token(value: Any, name: str) -> str:
    out = str(value or "").strip()
    if not out:
        raise CertificateError(f"{name}_EMPTY")
    return out


def _unique_tokens(value: Any, name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(f"{name}_NOT_SEQUENCE")
    out = [_token(x, name) for x in value]
    if len(set(out)) != len(out):
        raise CertificateError(f"{name}_DUPLICATE")
    return out


def _receipt(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError("SCOPE_RECEIPT_INVALID")
    out = dict(value)
    for key in (
        "closed_world_channel_graph",
        "dynamic_edges_registered",
        "load_bearing_edges_total",
        "independent_or_objective",
    ):
        if out.get(key) is not True:
            raise CertificateError(f"SCOPE_RECEIPT_{key.upper()}_NOT_TRUE")
    return out


def _reachable_without(
    entries: Sequence[str],
    adjacency: Mapping[str, Sequence[str]],
    target: str,
    removed_node: str,
) -> bool:
    if target == removed_node:
        return False
    q = collections.deque(x for x in entries if x != removed_node)
    seen = set(q)
    while q:
        node = q.popleft()
        if node == target:
            return True
        for nxt in adjacency.get(node, ()):
            if nxt == removed_node or nxt in seen:
                continue
            seen.add(nxt)
            q.append(nxt)
    return False


def verify_channel_graph_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_MAPPING")
        if cert.get("schema") != SCHEMA:
            raise CertificateError("SCHEMA_MISMATCH")

        nodes = _unique_tokens(cert.get("nodes"), "NODES")
        node_set = set(nodes)
        entries = _unique_tokens(cert.get("entry_nodes"), "ENTRY_NODES")
        if not entries:
            raise CertificateError("ENTRY_NODES_EMPTY")
        unknown_entries = [x for x in entries if x not in node_set]
        if unknown_entries:
            raise CertificateError("UNKNOWN_ENTRY_NODE:" + unknown_entries[0])

        receipt = _receipt(cert.get("scope_receipt"))

        raw_edges = cert.get("edges")
        if not isinstance(raw_edges, Sequence) or isinstance(raw_edges, (str, bytes, bytearray)):
            raise CertificateError("EDGES_NOT_SEQUENCE")

        edge_ids: set[str] = set()
        edges: list[dict[str, Any]] = []
        adjacency: dict[str, list[str]] = collections.defaultdict(list)
        for i, raw in enumerate(raw_edges):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"EDGE_{i}_INVALID")
            edge_id = _token(raw.get("id"), f"EDGE_{i}_ID")
            if edge_id in edge_ids:
                raise CertificateError("DUPLICATE_EDGE_ID:" + edge_id)
            edge_ids.add(edge_id)
            src = _token(raw.get("from"), f"EDGE_{i}_FROM")
            dst = _token(raw.get("to"), f"EDGE_{i}_TO")
            if src not in node_set:
                raise CertificateError("UNKNOWN_EDGE_SOURCE:" + edge_id + ":" + src)
            if dst not in node_set:
                raise CertificateError("UNKNOWN_EDGE_TARGET:" + edge_id + ":" + dst)
            load_bearing = raw.get("load_bearing") is True
            requirements_raw = raw.get("requirements", [])
            if not isinstance(requirements_raw, Sequence) or isinstance(
                requirements_raw, (str, bytes, bytearray)
            ):
                raise CertificateError("EDGE_REQUIREMENTS_INVALID:" + edge_id)
            if load_bearing and not requirements_raw:
                raise CertificateError("LOAD_BEARING_EDGE_UNCLASSIFIED:" + edge_id)

            requirements: list[dict[str, Any]] = []
            seen_requirement_keys: set[tuple[str, tuple[str, ...]]] = set()
            for j, req in enumerate(requirements_raw):
                if not isinstance(req, Mapping):
                    raise CertificateError(f"EDGE_{edge_id}_REQUIREMENT_{j}_INVALID")
                mediator = _token(
                    req.get("mediator"), f"EDGE_{edge_id}_REQUIREMENT_{j}_MEDIATOR"
                )
                if mediator not in node_set:
                    raise CertificateError(
                        "UNKNOWN_MEDIATOR:" + edge_id + ":" + mediator
                    )
                mediator_class = _token(
                    req.get("mediator_class"),
                    f"EDGE_{edge_id}_REQUIREMENT_{j}_MEDIATOR_CLASS",
                )
                predicate_ids = _unique_tokens(
                    req.get("predicate_ids"),
                    f"EDGE_{edge_id}_REQUIREMENT_{j}_PREDICATES",
                )
                if not predicate_ids:
                    raise CertificateError(
                        "REQUIREMENT_PREDICATES_EMPTY:" + edge_id + ":" + mediator
                    )
                key = (mediator, tuple(sorted(predicate_ids)))
                if key in seen_requirement_keys:
                    raise CertificateError(
                        "DUPLICATE_EDGE_REQUIREMENT:" + edge_id + ":" + mediator
                    )
                seen_requirement_keys.add(key)
                requirements.append(
                    {
                        "mediator": mediator,
                        "mediator_class": mediator_class,
                        "predicate_ids": predicate_ids,
                    }
                )

            edges.append(
                {
                    "id": edge_id,
                    "from": src,
                    "to": dst,
                    "load_bearing": load_bearing,
                    "requirements": requirements,
                }
            )
            adjacency[src].append(dst)

        reachable_nodes = set(entries)
        q = collections.deque(entries)
        while q:
            node = q.popleft()
            for nxt in adjacency.get(node, ()):
                if nxt not in reachable_nodes:
                    reachable_nodes.add(nxt)
                    q.append(nxt)

        predicate_coverage: dict[str, set[str]] = collections.defaultdict(set)
        checked_requirements = 0
        for edge in edges:
            if not edge["load_bearing"]:
                continue
            if edge["from"] not in reachable_nodes:
                continue
            for req in edge["requirements"]:
                checked_requirements += 1
                mediator = req["mediator"]
                if _reachable_without(entries, adjacency, edge["from"], mediator):
                    raise CertificateError(
                        "BYPASS_PATH:" + edge["id"] + ":" + mediator
                    )
                for predicate_id in req["predicate_ids"]:
                    predicate_coverage[predicate_id].add(edge["id"])

        reachable_load_bearing = [
            edge["id"]
            for edge in edges
            if edge["load_bearing"] and edge["from"] in reachable_nodes
        ]
        unreachable_load_bearing = [
            edge["id"]
            for edge in edges
            if edge["load_bearing"] and edge["from"] not in reachable_nodes
        ]

        return {
            "schema": RESULT_SCHEMA,
            "status": "PASS",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "reachable_node_count": len(reachable_nodes),
            "reachable_load_bearing_edge_count": len(reachable_load_bearing),
            "unreachable_load_bearing_edge_count": len(unreachable_load_bearing),
            "unreachable_load_bearing_edge_ids": unreachable_load_bearing,
            "checked_mediator_requirements": checked_requirements,
            "predicate_coverage": {
                key: sorted(value) for key, value in sorted(predicate_coverage.items())
            },
            "shared_no_bypass_proved_for_declared_graph": True,
            "channel_totality_semantics_proved_by_kernel": False,
            "mediator_semantic_soundness_proved_by_kernel": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": RESULT_SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }


def _git_blob(root: pathlib.Path, path: str) -> str:
    rel = pathlib.PurePosixPath(_token(path, "SOURCE_PATH"))
    if rel.is_absolute() or ".." in rel.parts or "." in rel.parts:
        raise CertificateError("SOURCE_BINDING_PATH_INVALID:" + path)
    base = pathlib.Path(root).resolve()
    target = base.joinpath(*rel.parts)
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, RuntimeError, ValueError) as exc:
        raise CertificateError("SOURCE_BINDING_PATH_OUTSIDE_ROOT:" + path) from exc
    if not resolved.is_file():
        raise CertificateError("SOURCE_BINDING_NOT_REGULAR_FILE:" + path)
    raw = resolved.read_bytes()
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()

def verify_repository_bound_certificate(
    cert: Mapping[str, Any],
    root: pathlib.Path | None = None,
) -> dict[str, Any]:
    base = verify_channel_graph_certificate(cert)
    if base.get("status") != "PASS":
        return base
    try:
        receipt = cert["scope_receipt"]
        bindings = receipt.get("source_bindings")
        if not isinstance(bindings, Sequence) or isinstance(
            bindings, (str, bytes, bytearray)
        ) or not bindings:
            raise CertificateError("SOURCE_BINDINGS_MISSING")
        root = pathlib.Path(root or pathlib.Path(__file__).resolve().parents[2])
        observed: list[dict[str, str]] = []
        seen_paths: set[str] = set()
        for i, item in enumerate(bindings):
            if not isinstance(item, Mapping):
                raise CertificateError(f"SOURCE_BINDING_{i}_INVALID")
            path = _token(item.get("path"), f"SOURCE_BINDING_{i}_PATH")
            expected = _token(
                item.get("git_blob_sha"), f"SOURCE_BINDING_{i}_GIT_BLOB_SHA"
            )
            if path in seen_paths:
                raise CertificateError("DUPLICATE_SOURCE_BINDING:" + path)
            seen_paths.add(path)
            if not HEX40.fullmatch(expected):
                raise CertificateError("SOURCE_BINDING_SHA_INVALID:" + path)
            actual = _git_blob(root, path)
            if actual != expected:
                raise CertificateError(
                    "SOURCE_BINDING_DRIFT:" + path + ":" + expected + ":" + actual
                )
            observed.append({"path": path, "git_blob_sha": actual})
        return {
            **base,
            "repository_bindings_status": "PASS",
            "verified_source_bindings": observed,
        }
    except Exception as exc:
        return {
            "schema": RESULT_SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }


if __name__ == "__main__":
    import sys
    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(verify_repository_bound_certificate(payload), indent=2, sort_keys=True))
