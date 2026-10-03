"""Goal-conditioned novelty delta for Universal Learning V4.

A dependency graph may shrink learning work only when its exact graph and goals
are independently receipt-bound. Otherwise callers must use the flat V2 delta.
Verified intermediate facts terminate traversal, preserving already-earned work.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_GOAL_DEPENDENCY_DELTA_V4"

class GoalDependencyDeltaError(ValueError):
    pass

def _items(values:Iterable[Any])->set[str]:
    return {str(x).strip() for x in values if str(x).strip()}

def _normalized(*,goals:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]])->dict[str,Any]:
    gs=sorted(_items(goals))
    graph={}
    for raw_parent,raw_children in dependencies.items():
        parent=str(raw_parent).strip()
        if not parent:
            raise GoalDependencyDeltaError("DEPENDENCY_PARENT_REQUIRED")
        graph[parent]=sorted(_items(raw_children))
    return {"goals":gs,"dependencies":dict(sorted(graph.items()))}

def dependency_digest(*,goals:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]])->str:
    body=json.dumps(_normalized(goals=goals,dependencies=dependencies),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _verify_receipt(*,environment_id:str,goal_id:str,goals,dependencies,receipt:Mapping[str,Any])->str:
    env=str(environment_id or "").strip(); gid=str(goal_id or "").strip()
    if not env or not gid:
        raise GoalDependencyDeltaError("ENVIRONMENT_AND_GOAL_ID_REQUIRED")
    if receipt.get("independent_verified") is not True or receipt.get("exact_byte_bound") is not True or receipt.get("conclusion")!="success":
        raise GoalDependencyDeltaError("DEPENDENCY_RECEIPT_INVALID")
    if receipt.get("decision_relevant_dependency_graph_complete") is not True:
        raise GoalDependencyDeltaError("DEPENDENCY_GRAPH_COMPLETENESS_NOT_PROVED")
    if str(receipt.get("environment_id") or "").strip()!=env or str(receipt.get("goal_id") or "").strip()!=gid:
        raise GoalDependencyDeltaError("DEPENDENCY_RECEIPT_SCOPE_MISMATCH")
    expected=dependency_digest(goals=goals,dependencies=dependencies)
    if receipt.get("dependency_graph_sha256")!=expected:
        raise GoalDependencyDeltaError("DEPENDENCY_RECEIPT_DIGEST_MISMATCH")
    rid=str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise GoalDependencyDeltaError("DEPENDENCY_RECEIPT_ID_REQUIRED")
    return rid

def minimum_goal_delta(*,environment_id:str,goal_id:str,goals:Iterable[Any],verified_facts:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]],dependency_receipt:Mapping[str,Any])->dict[str,Any]:
    normalized=_normalized(goals=goals,dependencies=dependencies)
    gs=normalized["goals"]; graph=normalized["dependencies"]
    rid=_verify_receipt(environment_id=environment_id,goal_id=goal_id,goals=gs,dependencies=graph,receipt=dependency_receipt)
    verified=_items(verified_facts)
    required=set(); boundary=set(); visiting=set(); visited=set()

    def visit(node:str):
        if node in verified:
            boundary.add(node); return
        if node in visited:
            return
        if node in visiting:
            raise GoalDependencyDeltaError("DEPENDENCY_CYCLE:"+node)
        visiting.add(node); required.add(node)
        for dep in graph.get(node,[]):
            visit(dep)
        visiting.remove(node); visited.add(node)

    for goal in gs:
        visit(goal)

    return {
        "schema":SCHEMA,
        "status":"FULLY_COVERED" if not required else "GOAL_NOVELTY_DELTA_OPEN",
        "goal_id":str(goal_id),
        "goals":gs,
        "missing":sorted(required),
        "verified_boundary":sorted(boundary),
        "dependency_receipt":rid,
        "dependency_graph_sha256":dependency_digest(goals=gs,dependencies=graph),
        "decision_relevant_graph_complete":True,
        "flat_environment_relearning_required":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
    }
