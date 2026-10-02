"""Exhaustive bounded semantic-graph proposal generation from explicit semantics.

This module owns structural proposal search only. It consumes source/JIT supplied typed
nodes and relation schemas, then enumerates every admissible finite relation graph within
declared bounds. It never invents semantic labels, chooses truth, or assigns authority.

That boundary is intentional: a relation/type meaning absent from all source, observation,
JIT knowledge, or declared schema is not truthfully identifiable by a structure generator.
"""
from __future__ import annotations

from itertools import combinations, product
from typing import Any, Mapping, Sequence
import json

SCHEMA = "BRAIN_BOUNDED_SEMANTIC_GRAPH_SYNTHESIZER_V1"


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _norm(v: Any) -> str:
    return " ".join(str(v if v is not None else "").split())


def _validate_nodes(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("nodes must be a sequence")
    out=[]; seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"nodes[{i}] must be object")
        nid=_norm(row.get("id")); typ=_norm(row.get("type"))
        if not nid or not typ:
            raise ValueError(f"nodes[{i}] requires nonempty id and type")
        if nid in seen:
            raise ValueError(f"duplicate node id: {nid}")
        seen.add(nid)
        d=dict(row); d["id"]=nid; d["type"]=typ
        out.append(d)
    return sorted(out,key=lambda x:x["id"])


def _validate_relations(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("relation_schemas must be a sequence")
    out=[]; seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"relation_schemas[{i}] must be object")
        rid=_norm(row.get("id"))
        roles=row.get("roles")
        if not rid or rid in seen:
            raise ValueError(f"relation_schemas[{i}] invalid/duplicate id")
        seen.add(rid)
        if not isinstance(roles, Sequence) or isinstance(roles,(str,bytes)) or not roles:
            raise ValueError(f"relation {rid} requires roles")
        role_out=[]; role_names=set()
        for j,role in enumerate(roles):
            if not isinstance(role, Mapping):
                raise ValueError(f"relation {rid} role[{j}] must be object")
            name=_norm(role.get("name"))
            allowed=role.get("allowed_types")
            if not name or name in role_names:
                raise ValueError(f"relation {rid} role[{j}] invalid/duplicate name")
            role_names.add(name)
            if not isinstance(allowed,Sequence) or isinstance(allowed,(str,bytes)) or not allowed:
                raise ValueError(f"relation {rid} role {name} requires allowed_types")
            vals=sorted({_norm(x) for x in allowed if _norm(x)})
            if not vals:
                raise ValueError(f"relation {rid} role {name} has no valid allowed_types")
            role_out.append({"name":name,"allowed_types":vals})
        d={
            "id":rid,
            "roles":role_out,
            "distinct_nodes":bool(row.get("distinct_nodes",True)),
            "symmetric":bool(row.get("symmetric",False)),
        }
        if d["symmetric"] and len(role_out)!=2:
            raise ValueError(f"symmetric relation {rid} must have exactly two roles")
        out.append(d)
    return sorted(out,key=lambda x:x["id"])


def _relation_instances(nodes: list[dict[str,Any]], schemas: list[dict[str,Any]]) -> list[dict[str,Any]]:
    by_type={}
    for n in nodes:
        by_type.setdefault(n["type"],[]).append(n["id"])
    instances=[]
    seen=set()
    for s in schemas:
        domains=[]
        for role in s["roles"]:
            ids=sorted({nid for typ in role["allowed_types"] for nid in by_type.get(typ,[])})
            if not ids:
                domains=[]
                break
            domains.append(ids)
        if not domains:
            continue
        for assignment in product(*domains):
            if s["distinct_nodes"] and len(set(assignment))!=len(assignment):
                continue
            if s["symmetric"] and assignment[0] > assignment[1]:
                continue
            roles={r["name"]:nid for r,nid in zip(s["roles"],assignment)}
            edge={"relation":s["id"],"roles":roles}
            key=_canon(edge)
            if key not in seen:
                seen.add(key); instances.append(edge)
    return sorted(instances,key=_canon)


def synthesize_graphs(contract: Mapping[str,Any]) -> dict[str,Any]:
    """Enumerate all relation graphs over explicit typed nodes within a finite edge bound."""
    if not isinstance(contract,Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["CONTRACT_NOT_OBJECT"]}
    try:
        nodes=_validate_nodes(contract.get("nodes",[]))
        schemas=_validate_relations(contract.get("relation_schemas",[]))
        max_edges=contract.get("max_edges",0)
        max_candidates=contract.get("max_candidates",10000)
        if not isinstance(max_edges,int) or isinstance(max_edges,bool) or max_edges<0:
            raise ValueError("max_edges must be nonnegative integer")
        if not isinstance(max_candidates,int) or isinstance(max_candidates,bool) or max_candidates<1:
            raise ValueError("max_candidates must be positive integer")

        instances=_relation_instances(nodes,schemas)
        limit=min(max_edges,len(instances))
        theoretical=sum(_n_choose_k(len(instances),k) for k in range(limit+1))
        if theoretical>max_candidates:
            return {
                "schema":SCHEMA,
                "status":"BOUND_EXCEEDED",
                "complete_within_declared_bound":False,
                "candidate_count_theoretical":theoretical,
                "max_candidates":max_candidates,
                "relation_instance_count":len(instances),
                "next":"TIGHTEN_BOUND_OR_ADD_DISCRIMINATING_CONSTRAINTS",
                "terminal_authority":False,
            }

        candidates=[]
        for k in range(limit+1):
            for chosen in combinations(instances,k):
                candidates.append({
                    "nodes":[{"id":n["id"],"type":n["type"]} for n in nodes],
                    "relations":list(chosen),
                })
        candidates=sorted(candidates,key=_canon)
        return {
            "schema":SCHEMA,
            "status":"COMPLETE",
            "complete_within_declared_bound":True,
            "node_count":len(nodes),
            "relation_instance_count":len(instances),
            "candidate_count":len(candidates),
            "max_edges":max_edges,
            "candidates":candidates,
            "semantic_vocabulary_authority":False,
            "truth_selection_authority":False,
            "terminal_authority":False,
            "scope":"EXHAUSTIVE_FINITE_TYPED_LABELED_RELATION_GRAPH_PROPOSALS_FROM_EXPLICIT_NODE_AND_RELATION_SEMANTICS",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":[f"{type(exc).__name__}:{exc}"],
            "terminal_authority":False,
        }


def _n_choose_k(n:int,k:int)->int:
    if k<0 or k>n:
        return 0
    k=min(k,n-k)
    out=1
    for i in range(1,k+1):
        out=out*(n-k+i)//i
    return out
