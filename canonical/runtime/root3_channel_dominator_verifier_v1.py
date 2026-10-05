"""Fail-closed finite dominator verifier for Project Brain load-bearing runtime channels.

This module does not discover runtime channels. It verifies a content-addressed,
closed-world channel manifest supplied by a compiler/auditor.

A bound mediator dominates a load-bearing sink iff, after removing the mediator,
no runtime entrypoint can reach that sink. Unknown dynamic edges, unclassified
load-bearing sinks, malformed content-address bindings, and any bypass path fail
closed.

This verifier grants no execution, promotion, capability, family, ownership, or
terminal credit. Scope completeness of the supplied manifest and guard semantic
soundness remain separate proof obligations.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ROOT3_CHANNEL_DOMINATOR_VERIFIER_V1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

KINDS = {
    "RUNTIME_ENTRYPOINT",
    "CONTROL",
    "PLANNER_OR_CONTROLLER_TRANSITION",
    "STATE_OR_EVIDENCE_MEDIATOR",
    "MATERIAL_EFFECT_MEDIATOR",
    "CROSS_ROLE_STATE_OR_EVIDENCE_USE",
    "MATERIAL_EFFECT_SINK",
    "USER_VISIBLE_LOAD_BEARING_OUTPUT",
}
LOAD_BEARING_KINDS = {
    "CROSS_ROLE_STATE_OR_EVIDENCE_USE",
    "MATERIAL_EFFECT_SINK",
    "USER_VISIBLE_LOAD_BEARING_OUTPUT",
}
MEDIATOR_CLASSES = {
    "STATE_CAPSULE",
    "AUTHORITY_GUARD",
    "INVARIANT_GUARD",
    "OTHER_EXPLICIT_PREUSE_OR_PRECOMMIT_GUARD",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(
    value: Any,
    field: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        errors.append(field + "_NOT_" + ("LIST" if allow_empty else "NONEMPTY_LIST"))
        return []
    out: list[str] = []
    for i, item in enumerate(value):
        if not _nonempty(item):
            errors.append(f"{field}_INVALID:{i}")
        else:
            out.append(item.strip())
    if len(out) != len(set(out)):
        errors.append(field + "_DUPLICATE")
    return out


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _reachable(
    adjacency: Mapping[str, list[str]],
    starts: Sequence[str],
    target: str,
) -> bool:
    q: deque[str] = deque(starts)
    seen = set(starts)
    while q:
        node = q.popleft()
        if node == target:
            return True
        for nxt in adjacency.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return False


def _bypass_path(
    adjacency: Mapping[str, list[str]],
    starts: Sequence[str],
    target: str,
    blocked: str,
) -> list[str] | None:
    if target == blocked:
        return None
    q: deque[str] = deque()
    parent: dict[str, str | None] = {}
    for start in starts:
        if start == blocked or start in parent:
            continue
        parent[start] = None
        q.append(start)
    while q:
        node = q.popleft()
        if node == target:
            path: list[str] = []
            cur: str | None = node
            while cur is not None:
                path.append(cur)
                cur = parent[cur]
            return list(reversed(path))
        for nxt in adjacency.get(node, ()):
            if nxt == blocked or nxt in parent:
                continue
            parent[nxt] = node
            q.append(nxt)
    return None


def evaluate(manifest: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    bypasses: list[dict[str, Any]] = []

    if not isinstance(manifest, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["MANIFEST_NOT_OBJECT"],
            "bypasses": [],
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
        }

    source_blobs = manifest.get("source_blobs")
    normalized_sources: list[dict[str, str]] = []
    if not isinstance(source_blobs, list) or not source_blobs:
        errors.append("SOURCE_BLOBS_NOT_NONEMPTY_LIST")
    else:
        paths: list[str] = []
        for i, row in enumerate(source_blobs):
            if not isinstance(row, Mapping):
                errors.append(f"SOURCE_BLOB_NOT_OBJECT:{i}")
                continue
            path = str(row.get("path") or "").strip()
            sha = str(row.get("git_blob_sha") or "").strip()
            if not path:
                errors.append(f"SOURCE_BLOB_PATH_MISSING:{i}")
            if not SHA40.fullmatch(sha):
                errors.append(f"SOURCE_BLOB_SHA_INVALID:{i}")
            if path:
                paths.append(path)
            if path and SHA40.fullmatch(sha):
                normalized_sources.append(
                    {"path": path, "git_blob_sha": sha}
                )
        if len(paths) != len(set(paths)):
            errors.append("SOURCE_BLOB_PATH_DUPLICATE")

    nodes_raw = manifest.get("nodes")
    nodes: dict[str, str] = {}
    if not isinstance(nodes_raw, list) or not nodes_raw:
        errors.append("NODES_NOT_NONEMPTY_LIST")
        nodes_raw = []
    for i, row in enumerate(nodes_raw):
        if not isinstance(row, Mapping):
            errors.append(f"NODE_NOT_OBJECT:{i}")
            continue
        nid = str(row.get("id") or "").strip()
        kind = str(row.get("kind") or "").strip()
        if not nid:
            errors.append(f"NODE_ID_MISSING:{i}")
            continue
        if nid in nodes:
            errors.append("DUPLICATE_NODE_ID:" + nid)
            continue
        if kind not in KINDS:
            errors.append("NODE_KIND_INVALID:" + nid)
        nodes[nid] = kind

    entrypoints = _string_list(
        manifest.get("entrypoints"),
        "ENTRYPOINTS",
        errors,
    )
    for eid in entrypoints:
        if eid not in nodes:
            errors.append("UNKNOWN_ENTRYPOINT:" + eid)
        elif nodes[eid] != "RUNTIME_ENTRYPOINT":
            errors.append("ENTRYPOINT_KIND_INVALID:" + eid)

    edges_raw = manifest.get("edges")
    adjacency: dict[str, list[str]] = {nid: [] for nid in nodes}
    edge_ids: set[str] = set()
    normalized_edges: list[dict[str, Any]] = []
    if not isinstance(edges_raw, list):
        errors.append("EDGES_NOT_LIST")
        edges_raw = []
    for i, row in enumerate(edges_raw):
        if not isinstance(row, Mapping):
            errors.append(f"EDGE_NOT_OBJECT:{i}")
            continue
        eid = str(row.get("id") or "").strip()
        src = str(row.get("from") or "").strip()
        dst = str(row.get("to") or "").strip()
        dynamic = row.get("dynamic")
        if not eid:
            errors.append(f"EDGE_ID_MISSING:{i}")
            continue
        if eid in edge_ids:
            errors.append("DUPLICATE_EDGE_ID:" + eid)
            continue
        edge_ids.add(eid)
        if src not in nodes or dst not in nodes:
            errors.append(f"DANGLING_EDGE:{eid}:{src}->{dst}")
            continue
        if dynamic not in (True, False):
            errors.append("EDGE_DYNAMIC_FLAG_INVALID:" + eid)
            continue
        adjacency[src].append(dst)
        normalized_edges.append(
            {"id": eid, "from": src, "to": dst, "dynamic": dynamic}
        )

    if manifest.get("dynamic_edge_registry_complete") is not True:
        errors.append("DYNAMIC_EDGE_REGISTRY_NOT_COMPLETE")

    unknown_dynamic = _string_list(
        manifest.get("unknown_dynamic_edges", []),
        "UNKNOWN_DYNAMIC_EDGES",
        errors,
        allow_empty=True,
    )
    if unknown_dynamic:
        errors.extend("UNKNOWN_DYNAMIC_EDGE:" + x for x in unknown_dynamic)

    unclassified = _string_list(
        manifest.get("unclassified_load_bearing_channels", []),
        "UNCLASSIFIED_LOAD_BEARING_CHANNELS",
        errors,
        allow_empty=True,
    )
    if unclassified:
        errors.extend(
            "UNCLASSIFIED_LOAD_BEARING_CHANNEL:" + x for x in unclassified
        )

    bindings_raw = manifest.get("mediator_bindings")
    bindings: dict[str, dict[str, Any]] = {}
    if not isinstance(bindings_raw, list):
        errors.append("MEDIATOR_BINDINGS_NOT_LIST")
        bindings_raw = []
    for i, row in enumerate(bindings_raw):
        if not isinstance(row, Mapping):
            errors.append(f"MEDIATOR_BINDING_NOT_OBJECT:{i}")
            continue
        sink = str(row.get("sink_id") or "").strip()
        mediator = str(row.get("required_mediator_id") or "").strip()
        mclass = str(row.get("mediator_class") or "").strip()
        predicates = row.get("predicate_ids")

        if not sink:
            errors.append(f"BINDING_SINK_MISSING:{i}")
            continue
        if sink in bindings:
            errors.append("DUPLICATE_SINK_BINDING:" + sink)
            continue

        if sink not in nodes:
            errors.append("BINDING_UNKNOWN_SINK:" + sink)
        elif nodes[sink] not in LOAD_BEARING_KINDS:
            errors.append("BINDING_TARGET_NOT_LOAD_BEARING:" + sink)

        if mediator not in nodes:
            errors.append("BINDING_UNKNOWN_MEDIATOR:" + mediator)
        if sink == mediator:
            errors.append("SINK_EQUALS_MEDIATOR:" + sink)
        if mclass not in MEDIATOR_CLASSES:
            errors.append("MEDIATOR_CLASS_INVALID:" + sink)
        if mediator in nodes:
            mediator_kind = nodes[mediator]
            if mclass == "STATE_CAPSULE" and mediator_kind != "STATE_OR_EVIDENCE_MEDIATOR":
                errors.append("STATE_CAPSULE_MEDIATOR_KIND_INVALID:" + sink)
            if mclass in {"AUTHORITY_GUARD", "INVARIANT_GUARD"} and mediator_kind != "MATERIAL_EFFECT_MEDIATOR":
                errors.append("MATERIAL_EFFECT_MEDIATOR_KIND_INVALID:" + sink)

        plist: list[str] = []
        if not isinstance(predicates, list) or not predicates:
            errors.append("PREDICATE_IDS_NOT_NONEMPTY_LIST:" + sink)
        else:
            for j, pid in enumerate(predicates):
                if not _nonempty(pid):
                    errors.append(f"PREDICATE_ID_INVALID:{sink}:{j}")
                else:
                    plist.append(pid.strip())
            if len(plist) != len(set(plist)):
                errors.append("PREDICATE_ID_DUPLICATE:" + sink)

        bindings[sink] = {
            "sink_id": sink,
            "required_mediator_id": mediator,
            "mediator_class": mclass,
            "predicate_ids": sorted(set(plist)),
        }

    load_bearing = sorted(
        nid for nid, kind in nodes.items()
        if kind in LOAD_BEARING_KINDS
    )
    for sink in load_bearing:
        if sink not in bindings:
            errors.append("LOAD_BEARING_SINK_UNBOUND:" + sink)
    for sink in sorted(set(bindings) - set(load_bearing)):
        errors.append("NON_LOAD_BEARING_BINDING:" + sink)

    if not errors:
        for sink in load_bearing:
            binding = bindings[sink]
            mediator = binding["required_mediator_id"]
            if not _reachable(adjacency, entrypoints, sink):
                errors.append("DECLARED_LOAD_BEARING_SINK_UNREACHABLE:" + sink)
                continue
            witness = _bypass_path(
                adjacency,
                entrypoints,
                sink,
                mediator,
            )
            if witness is not None:
                bypasses.append(
                    {
                        "sink_id": sink,
                        "required_mediator_id": mediator,
                        "bypass_path": witness,
                    }
                )
                errors.append(
                    "MEDIATOR_BYPASS:" + sink + ":" + mediator
                )

    payload = {
        "source_blobs": sorted(
            normalized_sources,
            key=lambda x: x["path"],
        ),
        "entrypoints": sorted(entrypoints),
        "nodes": sorted(
            (
                {"id": nid, "kind": kind}
                for nid, kind in nodes.items()
            ),
            key=lambda x: x["id"],
        ),
        "edges": sorted(
            normalized_edges,
            key=lambda x: x["id"],
        ),
        "mediator_bindings": sorted(
            bindings.values(),
            key=lambda x: x["sink_id"],
        ),
        "dynamic_edge_registry_complete": (
            manifest.get("dynamic_edge_registry_complete") is True
        ),
        "unknown_dynamic_edges": sorted(unknown_dynamic),
        "unclassified_load_bearing_channels": sorted(unclassified),
    }
    graph_digest = _digest(payload)

    declared_digest = manifest.get("expected_graph_manifest_sha256")
    if declared_digest is not None:
        if not isinstance(declared_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}",
            declared_digest,
        ):
            errors.append("EXPECTED_GRAPH_MANIFEST_SHA256_INVALID")
        elif declared_digest != graph_digest:
            errors.append("GRAPH_MANIFEST_DIGEST_MISMATCH")

    unique = sorted(set(errors))
    passed = not unique and not bypasses

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__DECLARED_CLOSED_WORLD_GRAPH_DOMINATOR_CONDITIONS_HOLD"
            if passed
            else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": unique,
        "bypasses": bypasses,
        "graph_manifest_sha256": graph_digest,
        "node_count": len(nodes),
        "edge_count": len(normalized_edges),
        "entrypoint_count": len(entrypoints),
        "load_bearing_sink_count": len(load_bearing),
        "mediator_binding_count": len(bindings),
        "source_blob_count": len(normalized_sources),
        "scope_limit": (
            "PROVES_DOMINANCE_ONLY_FOR_THE_SUPPLIED_CONTENT_ADDRESSED_"
            "CLOSED_WORLD_GRAPH__DOES_NOT_SELF_PROVE_CHANNEL_DISCOVERY_"
            "COMPLETENESS_OR_GUARD_SEMANTIC_SOUNDNESS"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    manifest = args.get("manifest")
    return evaluate(manifest if isinstance(manifest, Mapping) else {})


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ns = ap.parse_args()
    document = json.loads(ns.manifest.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(document), indent=2, sort_keys=True))
