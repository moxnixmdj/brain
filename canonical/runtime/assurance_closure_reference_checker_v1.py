"""Independent structural reference checker for UVCK V2 assurance graphs.

This module intentionally does not import assurance_closure_compiler_v1.
It recomputes representation/proof closure with a fixed-point algorithm so the
primary compiler can be differentially checked against an independent
implementation.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_ASSURANCE_CLOSURE_REFERENCE_CHECKER_V1"
GRAPH_SCHEMA="PROJECT_BRAIN_ASSURANCE_CLOSURE_GRAPH_V1"
PRIMITIVE_TYPES=frozenset({
    "CLAIM","OBLIGATION","ASSUMPTION","EVIDENCE","DEPENDENCY","DEFEATER",
    "EFFECT","AUTHORITY","RESOURCE","MONITOR","EPOCH","TRANSITION",
})
TERMINAL_LEAF_TYPES=frozenset({"EVIDENCE","ASSUMPTION","EPOCH"})
VALID_STATUSES=frozenset({
    "SUPPORTED","OPEN","STALE","PROVEN_IRRELEVANT","REJECTED",
})


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "terminal_authority":False,**extra,
    }


def check(graph:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(graph,Mapping):
        return _fail("GRAPH_NOT_OBJECT")
    if graph.get("schema")!=GRAPH_SCHEMA:
        return _fail("GRAPH_SCHEMA_INVALID")
    roots=graph.get("root_ids")
    rows=graph.get("nodes")
    if not isinstance(roots,list) or not roots or not all(
        isinstance(x,str) and x for x in roots
    ):
        return _fail("ROOT_IDS_INVALID")
    if not isinstance(rows,list):
        return _fail("NODES_NOT_LIST")

    nodes={}
    unsupported=set()
    for row in rows:
        if not isinstance(row,Mapping):
            return _fail("NODE_NOT_OBJECT")
        nid=row.get("id"); typ=row.get("type"); status=row.get("status")
        if not isinstance(nid,str) or not nid or nid in nodes:
            return _fail("NODE_ID_INVALID_OR_DUPLICATE")
        if not isinstance(typ,str) or not typ:
            return _fail("NODE_TYPE_INVALID")
        if typ not in PRIMITIVE_TYPES:
            unsupported.add(typ)
        if status not in VALID_STATUSES:
            return _fail("NODE_STATUS_INVALID",node_id=nid)
        deps=row.get("depends_on",[])
        defeats=row.get("defeated_by",[])
        if not isinstance(deps,list) or not all(isinstance(x,str) and x for x in deps):
            return _fail("DEPENDS_ON_INVALID",node_id=nid)
        if not isinstance(defeats,list) or not all(isinstance(x,str) and x for x in defeats):
            return _fail("DEFEATED_BY_INVALID",node_id=nid)
        if len(deps)!=len(set(deps)) or len(defeats)!=len(set(defeats)):
            return _fail("DUPLICATE_REFERENCE",node_id=nid)
        nodes[nid]={
            "type":typ,"status":status,
            "deps":tuple(deps),"defeaters":tuple(defeats),
            "authoritative_leaf":row.get("authoritative_leaf") is True,
        }

    if any(r not in nodes for r in roots):
        return _fail("ROOT_NODE_MISSING")
    refs={x for n in nodes.values() for x in (*n["deps"],*n["defeaters"])}
    dangling=sorted(refs-set(nodes))
    if dangling:
        return _fail("DANGLING_NODE_REFERENCE",dangling_ids=dangling)

    reachable=set()
    frontier=list(roots)
    while frontier:
        nid=frontier.pop()
        if nid in reachable:
            continue
        reachable.add(nid)
        n=nodes[nid]
        frontier.extend(n["deps"])
        frontier.extend(n["defeaters"])

    # Defeater classification mirrors the semantic law independently:
    # for each supported node, any SUPPORTED defeater dominates OPEN/STALE
    # defeaters. Only when that node has no active defeater may unresolved
    # defeaters keep it open. This is order-independent.
    active_defeaters=set()
    unresolved_defeaters=set()
    for nid in reachable:
        defeaters=nodes[nid]["defeaters"]
        supported={
            d for d in defeaters
            if nodes[d]["status"]=="SUPPORTED"
        }
        if supported:
            active_defeaters.update(supported)
            continue
        unresolved_defeaters.update(
            d for d in defeaters
            if nodes[d]["status"] in {"OPEN","STALE"}
        )

    true=set()
    residual=set()
    for nid in reachable:
        n=nodes[nid]
        if n["status"]=="PROVEN_IRRELEVANT":
            true.add(nid)
        elif n["status"] in {"OPEN","STALE","REJECTED"}:
            residual.add(nid)
        elif (
            n["status"]=="SUPPORTED"
            and not n["deps"]
            and n["type"] in TERMINAL_LEAF_TYPES
            and n["authoritative_leaf"]
        ):
            true.add(nid)
        elif n["status"]=="SUPPORTED" and not n["deps"]:
            residual.add(nid)

    changed=True
    while changed:
        changed=False
        for nid in sorted(reachable):
            if nid in true or nid in residual:
                continue
            n=nodes[nid]
            if n["status"]!="SUPPORTED":
                continue
            if any(d in active_defeaters or d in unresolved_defeaters for d in n["defeaters"]):
                continue
            if n["deps"] and all(dep in true for dep in n["deps"]):
                true.add(nid); changed=True

    unresolved_supported={
        nid for nid in reachable
        if nodes[nid]["status"]=="SUPPORTED"
        and nid not in true
        and nid not in residual
        and not any(
            d in active_defeaters or d in unresolved_defeaters
            for d in nodes[nid]["defeaters"]
        )
    }
    unsupported_cycle_or_leaf=sorted(
        nid for nid in unresolved_supported
        if not any(dep in residual for dep in nodes[nid]["deps"])
        and not any(d in unresolved_defeaters for d in nodes[nid]["defeaters"])
    )
    if unsupported_cycle_or_leaf:
        return _fail(
            "UNSUPPORTED_CYCLE_OR_LEAF",
            unresolved_supported_ids=unsupported_cycle_or_leaf,
            representation_closure=(not unsupported),
            unsupported_primitive_types=sorted(unsupported),
        )

    root_closed={r:r in true and not nodes[r]["defeaters"] for r in roots}
    for r in roots:
        if any(d in active_defeaters or d in unresolved_defeaters for d in nodes[r]["defeaters"]):
            root_closed[r]=False

    proof_closure=all(root_closed.values()) and not active_defeaters and not unresolved_defeaters
    return {
        "schema":SCHEMA,
        "pass":proof_closure and not unsupported,
        "status":"STRUCTURAL_CLOSED" if proof_closure and not unsupported else "STRUCTURAL_OPEN",
        "representation_closure":not unsupported,
        "proof_closure":proof_closure,
        "root_closed":root_closed,
        "open_residual_ids":sorted(residual|unresolved_defeaters),
        "active_defeater_ids":sorted(active_defeaters),
        "unresolved_defeater_ids":sorted(unresolved_defeaters),
        "unsupported_primitive_types":sorted(unsupported),
        "terminal_authority":False,
    }
