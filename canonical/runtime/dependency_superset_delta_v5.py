"""Sound dependency-superset novelty compression for Universal Learning V5."""
from __future__ import annotations
import hashlib, json
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_DEPENDENCY_SUPERSET_DELTA_V5"
RELATIONS={"EXACT","PROVEN_SUPERSET"}

class DependencySupersetDeltaError(ValueError):
    pass

def _items(values:Iterable[Any])->set[str]:
    return {str(x).strip() for x in values if str(x).strip()}

def _normalized(*,goals:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]])->dict[str,Any]:
    gs=sorted(_items(goals))
    graph={}
    for raw_parent,raw_children in dependencies.items():
        parent=str(raw_parent).strip()
        if not parent:
            raise DependencySupersetDeltaError("DEPENDENCY_PARENT_REQUIRED")
        graph[parent]=sorted(_items(raw_children))
    return {"goals":gs,"dependencies":dict(sorted(graph.items()))}

def dependency_digest(*,goals:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]])->str:
    body=json.dumps(_normalized(goals=goals,dependencies=dependencies),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _verify_receipt(*,environment_id:str,goal_id:str,goals,dependencies,receipt:Mapping[str,Any])->tuple[str,str]:
    env=str(environment_id or "").strip(); gid=str(goal_id or "").strip()
    if not env or not gid:
        raise DependencySupersetDeltaError("ENVIRONMENT_AND_GOAL_ID_REQUIRED")
    if receipt.get("independent_verified") is not True or receipt.get("exact_byte_bound") is not True or receipt.get("conclusion")!="success":
        raise DependencySupersetDeltaError("DEPENDENCY_RECEIPT_INVALID")
    relation=str(receipt.get("scope_relation") or "").strip()
    if relation not in RELATIONS:
        raise DependencySupersetDeltaError("DEPENDENCY_SCOPE_RELATION_NOT_ADMISSIBLE")
    if receipt.get("all_true_decision_relevant_dependencies_contained") is not True:
        raise DependencySupersetDeltaError("DEPENDENCY_SUPERSET_SOUNDNESS_NOT_PROVED")
    if str(receipt.get("environment_id") or "").strip()!=env or str(receipt.get("goal_id") or "").strip()!=gid:
        raise DependencySupersetDeltaError("DEPENDENCY_RECEIPT_SCOPE_MISMATCH")
    expected=dependency_digest(goals=goals,dependencies=dependencies)
    if receipt.get("dependency_graph_sha256")!=expected:
        raise DependencySupersetDeltaError("DEPENDENCY_RECEIPT_DIGEST_MISMATCH")
    rid=str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise DependencySupersetDeltaError("DEPENDENCY_RECEIPT_ID_REQUIRED")
    return rid,relation

def goal_delta_upper_bound(*,environment_id:str,goal_id:str,goals:Iterable[Any],verified_facts:Iterable[Any],dependencies:Mapping[Any,Iterable[Any]],dependency_receipt:Mapping[str,Any])->dict[str,Any]:
    normalized=_normalized(goals=goals,dependencies=dependencies)
    gs=normalized["goals"]; graph=normalized["dependencies"]
    rid,relation=_verify_receipt(environment_id=environment_id,goal_id=goal_id,goals=gs,dependencies=graph,receipt=dependency_receipt)
    verified=_items(verified_facts)
    required=set(); boundary=set(); visiting=set(); visited=set()

    def visit(node:str):
        if node in verified:
            boundary.add(node); return
        if node in visited:
            return
        if node in visiting:
            raise DependencySupersetDeltaError("DEPENDENCY_CYCLE:"+node)
        visiting.add(node); required.add(node)
        for dep in graph.get(node,[]):
            visit(dep)
        visiting.remove(node); visited.add(node)

    for goal in gs:
        visit(goal)

    exact=relation=="EXACT"
    return {
        "schema":SCHEMA,
        "status":"FULLY_COVERED" if not required else "SOUND_GOAL_NOVELTY_UPPER_BOUND_OPEN",
        "goal_id":str(goal_id),
        "goals":gs,
        "missing":sorted(required),
        "verified_boundary":sorted(boundary),
        "dependency_receipt":rid,
        "dependency_graph_sha256":dependency_digest(goals=gs,dependencies=graph),
        "scope_relation":relation,
        "sound_upper_bound_on_required_novelty":True,
        "minimality_proved":exact,
        "overlearning_possible":not exact,
        "safe_to_prune_outside_reachable_graph":True,
        "flat_environment_relearning_required":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
    }
