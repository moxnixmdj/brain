"""Shared professional base-domain normal form verifier.

Proves a structural reduction only:
- the canonical professional behavior exposes exactly six target coordinates;
- the professional execution profile has exactly nine steps;
- those nine steps partition exactly into target compilation, hard-defect
  preflight, and seven proof-bound V7 steps;
- the router chain carrying those coordinates is V7 -> V6 -> V4 -> V3.

This is not a whole-leaf domain-equivalence proof. Root-specific admissibility,
property truth, execution adequacy, quality, acceptance, promotion and terminal
authority remain separate.
"""
from __future__ import annotations

import ast
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_BASE_DOMAIN_NORMAL_FORM_V1"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"

FILES={
    "router_v3":(
        "canonical/runtime/professional_quality_p1_router_v3.py",
        "cdb6716ac6d562d1ab222242d07aeecc5cdfac78",
    ),
    "router_v4":(
        "canonical/runtime/professional_quality_p1_router_v4.py",
        "8e5d473b5606251752c4968dfd35290e9b991f16",
    ),
    "router_v6":(
        "canonical/runtime/professional_quality_p1_router_v6.py",
        "88644e0517d472d9fbef8d5bc6cf3495f2b50005",
    ),
    "router_v7":(
        "canonical/runtime/professional_quality_p1_router_v7.py",
        "765b5994c2fcb5eb669b5fd0d989cc79c1609908",
    ),
    "target_semantics":(
        "canonical/runtime/professional_target_semantic_certificate_v1.py",
        "583612b0e2226053ac758683087b5c5d0f510996",
    ),
    "profile":(
        "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json",
        "f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5",
    ),
    "contract_registry":(
        "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json",
        "ae250d5bc5da73b23600670be354ffba31e65e53",
    ),
}

SEMANTIC_COORDINATES=(
    "objective",
    "audience",
    "source_evidence",
    "artifact_type",
    "constraints",
    "current_draft_or_render",
)
INPUT_ANCHORS=(
    "User objective",
    "audience",
    "source evidence",
    "artifact type",
    "constraints",
    "current draft/render",
)
EXPECTED_BASE_IMPORTS={
    "router_v4":"canonical.runtime.professional_quality_p1_router_v3",
    "router_v6":"canonical.runtime.professional_quality_p1_router_v4",
    "router_v7":"canonical.runtime.professional_quality_p1_router_v6",
}


def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "root_specific_domain_equivalence_proved":False,
        "whole_leaf_scope_complete":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }


def _tree(root:Path,key:str)->ast.Module:
    rel,expected=FILES[key]
    path=root/rel
    if not path.is_file() or path.is_symlink():
        raise ValueError("BOUND_FILE_MISSING:"+key)
    if _blob(path)!=expected:
        raise ValueError("BOUND_FILE_STALE:"+key)
    return ast.parse(path.read_text(encoding="utf-8"),filename=rel)


def _constant(tree:ast.Module,name:str)->Any:
    for node in tree.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            if any(isinstance(t,ast.Name) and t.id==name for t in targets):
                value=node.value
                if value is None:
                    break
                return ast.literal_eval(value)
    raise ValueError("CONSTANT_NOT_FOUND:"+name)


def _base_import(tree:ast.Module)->str|None:
    for node in tree.body:
        if isinstance(node,ast.ImportFrom):
            for alias in node.names:
                if alias.asname=="base":
                    prefix=(node.module+".") if node.module else ""
                    return prefix+alias.name
    return None


def _bound_json(root:Path,key:str)->dict[str,Any]:
    rel,expected=FILES[key]
    path=root/rel
    if not path.is_file() or path.is_symlink():
        raise ValueError("BOUND_FILE_MISSING:"+key)
    if _blob(path)!=expected:
        raise ValueError("BOUND_FILE_STALE:"+key)
    doc=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc,dict):
        raise ValueError("BOUND_JSON_NOT_OBJECT:"+key)
    return doc


def verify(
    *,
    repo_root:str|Path|None=None,
    expected_semantic_coordinates:Sequence[str]=SEMANTIC_COORDINATES,
    injected_preflight_step:str|None=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        v3=_tree(root,"router_v3")
        v4=_tree(root,"router_v4")
        v6=_tree(root,"router_v6")
        v7=_tree(root,"router_v7")
        sem=_tree(root,"target_semantics")
        profile=_bound_json(root,"profile")
        registry=_bound_json(root,"contract_registry")
    except Exception as exc:
        return _fail("DEPENDENCY_BINDING_INVALID",detail=type(exc).__name__+":"+str(exc))

    coords=tuple(_constant(v4,"TARGET_FIELDS"))
    expected=tuple(expected_semantic_coordinates)
    if coords!=expected:
        return _fail("TARGET_COORDINATE_SET_MISMATCH",actual=list(coords),expected=list(expected))

    anchors=tuple(_constant(sem,"EXPECTED_INPUT_ANCHORS"))
    if anchors!=INPUT_ANCHORS:
        return _fail("CONTRACT_INPUT_ANCHOR_SET_MISMATCH",actual=list(anchors))

    rows=registry.get("active_contracted_residuals")
    matches=[
        row for row in rows or []
        if isinstance(row,Mapping) and row.get("behavior_id")==BEHAVIOR_ID
    ]
    if len(matches)!=1:
        return _fail("PROFESSIONAL_BEHAVIOR_CONTRACT_NOT_UNIQUE")
    contract=matches[0]
    inputs=str(contract.get("inputs") or "")
    if any(anchor not in inputs for anchor in INPUT_ANCHORS):
        return _fail("PROFESSIONAL_BEHAVIOR_INPUT_ANCHOR_MISSING")

    if profile.get("behavior_id")!=BEHAVIOR_ID:
        return _fail("PROFILE_BEHAVIOR_ID_MISMATCH")
    steps=profile.get("steps")
    if not isinstance(steps,list) or not all(isinstance(x,str) and x for x in steps):
        return _fail("PROFILE_STEPS_INVALID")

    target_step=str(_constant(v6,"TARGET_STEP"))
    preflight_step=(
        injected_preflight_step
        if injected_preflight_step is not None
        else str(_constant(v3,"PREFLIGHT_STEP"))
    )
    proof_steps=tuple(_constant(v7,"AUTHENTICATED_STEPS"))
    v7_behavior=str(_constant(v7,"BEHAVIOR_ID"))
    if v7_behavior!=BEHAVIOR_ID:
        return _fail("V7_BEHAVIOR_ID_MISMATCH")

    partitions=[target_step,preflight_step,*proof_steps]
    if len(partitions)!=len(set(partitions)) or set(partitions)!=set(steps):
        return _fail(
            "PROFILE_STEP_PARTITION_OVERLAP_OR_GAP",
            profile_steps=steps,
            partition_steps=partitions,
        )
    if len(steps)!=9 or len(proof_steps)!=7:
        return _fail("PROFILE_STEP_CARDINALITY_MISMATCH")

    import_actual={
        "router_v4":_base_import(v4),
        "router_v6":_base_import(v6),
        "router_v7":_base_import(v7),
    }
    if import_actual!=EXPECTED_BASE_IMPORTS:
        return _fail("ROUTER_CHAIN_MISMATCH",actual=import_actual,expected=EXPECTED_BASE_IMPORTS)

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__SHARED_PROFESSIONAL_BASE_DOMAIN_NORMAL_FORM_BOUND__ZERO_LEAF_CREDIT",
        "behavior_id":BEHAVIOR_ID,
        "semantic_coordinate_count":len(coords),
        "semantic_coordinates":list(coords),
        "contract_input_anchors":list(anchors),
        "profile_step_count":len(steps),
        "target_compilation_step_count":1,
        "hard_defect_preflight_step_count":1,
        "proof_bound_remaining_step_count":len(proof_steps),
        "profile_step_partition_complete":True,
        "router_chain":["V7","V6","V4","V3"],
        "reduction":{
            "shared_base_domain":"EXACT_SIX_COORDINATE_TARGET_INSTANCE_PLUS_AUTHENTICATED_GOAL_DECISION_SUBJECT_AND_STEP_EVIDENCE_CONTEXT",
            "leaf_specific_remaining_work":"PROVE_EACH_ROOT_LEAF_ADMISSIBILITY_PREDICATE_IS_TOTAL_OR_EXACTLY_FACTORIZED_OVER_THIS_SHARED_BASE_DOMAIN",
            "reuse_law":"DO_NOT_REDEFINE_THE_SIX_BASE_TARGET_COORDINATES_PER_LEAF",
        },
        "root_specific_domain_equivalence_proved":False,
        "whole_leaf_scope_complete":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":[
            "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
            "NO_ROOT_SPECIFIC_DOMAIN_EQUIVALENCE",
            "NO_WHOLE_LEAF_SCOPE_COMPLETENESS",
            "NO_WHOLE_LEAF_PROPERTY_TRUTH",
            "NO_DOMAIN_SEMANTIC_OR_EXECUTION_CLOSURE",
            "NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_CREDIT",
        ],
    }


if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
