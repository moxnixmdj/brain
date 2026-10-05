"""Fail-closed finite channel-graph dominator verifier.

This kernel proves only graph-theoretic non-bypassability on a content-addressed
channel certificate.  It deliberately does not manufacture the harder
premise that the declared graph is scope-complete for a Python runtime.
That premise must arrive as an independently bound totality receipt.
"""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
import pathlib
import re
import subprocess
from typing import Any

SCHEMA = "PROJECT_BRAIN_CHANNEL_DOMINATOR_VERIFIER_V1"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class CertificateError(ValueError):
    pass


def _seq(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    return list(value)


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _unique_tokens(value: Any, label: str) -> list[str]:
    out = [_token(x, label + "_ITEM") for x in _seq(value, label)]
    if len(out) != len(set(out)):
        raise CertificateError(label + "_DUPLICATE")
    return out


def _sha(value: Any, label: str) -> str:
    out = _token(value, label).lower()
    if not _SHA40.fullmatch(out):
        raise CertificateError(label + "_INVALID")
    return out


def _receipt(value: Any, label: str, required_true: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    out = {
        "path": _token(value.get("path"), label + "_PATH"),
        "git_blob_sha": _sha(value.get("git_blob_sha"), label + "_SHA"),
    }
    for field in required_true:
        if value.get(field) is not True:
            raise CertificateError(label + "_" + field.upper() + "_NOT_TRUE")
        out[field] = True
    return out


def _git_blob(root: pathlib.Path, path: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD:" + path],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CertificateError("SOURCE_BINDING_GIT_READ_FAILED:" + path)
    return proc.stdout.strip()


def _validate_source_bindings(
    raw: Any, root: pathlib.Path | None
) -> list[dict[str, str]]:
    rows = _seq(raw, "SOURCE_BINDINGS")
    if not rows:
        raise CertificateError("SOURCE_BINDINGS_EMPTY")
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for i, item in enumerate(rows):
        if not isinstance(item, Mapping):
            raise CertificateError(f"SOURCE_BINDING_{i}_INVALID")
        path = _token(item.get("path"), f"SOURCE_BINDING_{i}_PATH")
        sha = _sha(item.get("git_blob_sha"), f"SOURCE_BINDING_{i}_SHA")
        if path in seen:
            raise CertificateError("SOURCE_BINDING_PATH_DUPLICATE:" + path)
        seen.add(path)
        if root is not None:
            observed = _git_blob(root, path)
            if observed != sha:
                raise CertificateError(
                    "SOURCE_BINDING_DRIFT:" + path + ":" + sha + ":" + observed
                )
        out.append({"path": path, "git_blob_sha": sha})
    return out


def _reachable(
    entrypoints: Sequence[str], adjacency: Mapping[str, set[str]]
) -> set[str]:
    reached = set(entrypoints)
    queue = deque(entrypoints)
    while queue:
        node = queue.popleft()
        for nxt in adjacency.get(node, set()):
            if nxt not in reached:
                reached.add(nxt)
                queue.append(nxt)
    return reached


def _dominators(
    nodes: set[str],
    entrypoints: Sequence[str],
    predecessors: Mapping[str, set[str]],
) -> dict[str, set[str]]:
    """Compute classic node dominators with a synthetic multi-entry root."""
    synthetic = "__PROJECT_BRAIN_SYNTHETIC_ENTRY__"
    if synthetic in nodes:
        raise CertificateError("RESERVED_SYNTHETIC_NODE_USED")
    universe = set(nodes) | {synthetic}
    preds: dict[str, set[str]] = {n: set(predecessors.get(n, set())) for n in nodes}
    preds[synthetic] = set()
    for entry in entrypoints:
        preds.setdefault(entry, set()).add(synthetic)

    dom: dict[str, set[str]] = {synthetic: {synthetic}}
    for node in nodes:
        dom[node] = set(universe)

    changed = True
    while changed:
        changed = False
        for node in sorted(nodes):
            incoming = preds.get(node, set())
            if not incoming:
                new = {node}
            else:
                iterator = iter(incoming)
                first = next(iterator)
                common = set(dom[first])
                for pred in iterator:
                    common.intersection_update(dom[pred])
                new = {node} | common
            if new != dom[node]:
                dom[node] = new
                changed = True
    return dom


def verify_channel_graph(
    certificate: Mapping[str, Any],
    *,
    root: pathlib.Path | str | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(certificate, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")
        if certificate.get("schema") != SCHEMA:
            raise CertificateError("SCHEMA_MISMATCH")

        repo_root = pathlib.Path(root).resolve() if root is not None else None
        bindings = _validate_source_bindings(
            certificate.get("source_bindings"), repo_root
        )

        totality = _receipt(
            certificate.get("channel_totality_receipt"),
            "CHANNEL_TOTALITY_RECEIPT",
            (
                "scope_complete",
                "static_edges_complete",
                "dynamic_edges_complete",
                "independent_or_objective",
            ),
        )

        nodes = set(_unique_tokens(certificate.get("nodes"), "NODES"))
        if not nodes:
            raise CertificateError("NODES_EMPTY")
        entrypoints = _unique_tokens(certificate.get("entrypoints"), "ENTRYPOINTS")
        if not entrypoints:
            raise CertificateError("ENTRYPOINTS_EMPTY")
        if any(x not in nodes for x in entrypoints):
            raise CertificateError("ENTRYPOINT_UNKNOWN")

        raw_mediators = _seq(certificate.get("mediators"), "MEDIATORS")
        mediator_classes: dict[str, str] = {}
        for i, item in enumerate(raw_mediators):
            if not isinstance(item, Mapping):
                raise CertificateError(f"MEDIATOR_{i}_INVALID")
            node = _token(item.get("node"), f"MEDIATOR_{i}_NODE")
            cls = _token(item.get("class"), f"MEDIATOR_{i}_CLASS")
            if node not in nodes:
                raise CertificateError("MEDIATOR_NODE_UNKNOWN:" + node)
            if node in mediator_classes:
                raise CertificateError("MEDIATOR_NODE_DUPLICATE:" + node)
            mediator_classes[node] = cls

        edges: list[dict[str, Any]] = []
        edge_ids: set[str] = set()
        adjacency: dict[str, set[str]] = defaultdict(set)
        predecessors: dict[str, set[str]] = defaultdict(set)
        for i, raw in enumerate(_seq(certificate.get("edges"), "EDGES")):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"EDGE_{i}_INVALID")
            edge_id = _token(raw.get("id"), f"EDGE_{i}_ID")
            if edge_id in edge_ids:
                raise CertificateError("EDGE_ID_DUPLICATE:" + edge_id)
            edge_ids.add(edge_id)
            src = _token(raw.get("from"), f"EDGE_{i}_FROM")
            dst = _token(raw.get("to"), f"EDGE_{i}_TO")
            kind = _token(raw.get("kind"), f"EDGE_{i}_KIND")
            if src not in nodes or dst not in nodes:
                raise CertificateError("EDGE_NODE_UNKNOWN:" + edge_id)
            load_bearing = raw.get("load_bearing")
            if not isinstance(load_bearing, bool):
                raise CertificateError("EDGE_LOAD_BEARING_INVALID:" + edge_id)
            required = _unique_tokens(
                raw.get("required_mediators", []),
                f"EDGE_{i}_REQUIRED_MEDIATORS",
            )
            if load_bearing and not required:
                raise CertificateError("LOAD_BEARING_EDGE_UNMEDIATED:" + edge_id)
            for mediator in required:
                if mediator not in mediator_classes:
                    raise CertificateError(
                        "EDGE_MEDIATOR_UNDECLARED:" + edge_id + ":" + mediator
                    )
            row = {
                "id": edge_id,
                "from": src,
                "to": dst,
                "kind": kind,
                "load_bearing": load_bearing,
                "required_mediators": required,
            }
            edges.append(row)
            adjacency[src].add(dst)
            predecessors[dst].add(src)

        if not edges:
            raise CertificateError("EDGES_EMPTY")

        dynamic_sites = _seq(certificate.get("dynamic_sites", []), "DYNAMIC_SITES")
        dynamic_ids: set[str] = set()
        for i, raw in enumerate(dynamic_sites):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"DYNAMIC_SITE_{i}_INVALID")
            site_id = _token(raw.get("id"), f"DYNAMIC_SITE_{i}_ID")
            if site_id in dynamic_ids:
                raise CertificateError("DYNAMIC_SITE_DUPLICATE:" + site_id)
            dynamic_ids.add(site_id)
            status = _token(raw.get("status"), f"DYNAMIC_SITE_{i}_STATUS")
            if status != "REGISTERED":
                raise CertificateError("DYNAMIC_SITE_NOT_REGISTERED:" + site_id)
            _token(raw.get("source_ref"), f"DYNAMIC_SITE_{i}_SOURCE_REF")
            registered = _unique_tokens(
                raw.get("registered_edge_ids"),
                f"DYNAMIC_SITE_{i}_REGISTERED_EDGE_IDS",
            )
            if not registered:
                raise CertificateError("DYNAMIC_SITE_EDGELESS:" + site_id)
            unknown = [x for x in registered if x not in edge_ids]
            if unknown:
                raise CertificateError(
                    "DYNAMIC_SITE_UNKNOWN_EDGE:" + site_id + ":" + unknown[0]
                )

        reached = _reachable(entrypoints, adjacency)
        reached_predecessors = {
            node: {p for p in predecessors.get(node, set()) if p in reached}
            for node in reached
        }
        dom = _dominators(reached, entrypoints, reached_predecessors)

        checked_edges = 0
        for edge in edges:
            if not edge["load_bearing"] or edge["from"] not in reached:
                continue
            checked_edges += 1
            for mediator in edge["required_mediators"]:
                if mediator not in dom[edge["from"]]:
                    raise CertificateError(
                        "MEDIATOR_BYPASS:"
                        + edge["id"]
                        + ":"
                        + mediator
                        + ":"
                        + edge["from"]
                    )

        if checked_edges == 0:
            raise CertificateError("NO_REACHABLE_LOAD_BEARING_EDGES")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "DECLARED_SCOPE_COMPLETE_CHANNEL_GRAPH_HAS_NO_MEDIATOR_BYPASS",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "reachable_node_count": len(reached),
            "reachable_load_bearing_edge_count": checked_edges,
            "mediator_count": len(mediator_classes),
            "dynamic_site_count": len(dynamic_sites),
            "source_binding_count": len(bindings),
            "channel_totality_receipt": totality,
            "scope_limit": (
                "PASS_PROVES_GRAPH_THEORETIC_NON_BYPASSABILITY_ONLY_BECAUSE_THE_"
                "INDEPENDENT_TOTALITY_RECEIPT_IS_AN_EXPLICIT_LOAD_BEARING_PREMISE"
            ),
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "fresh_reality_authority": False,
        }
