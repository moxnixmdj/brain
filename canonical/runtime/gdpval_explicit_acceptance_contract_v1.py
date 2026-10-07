"""GDPval explicit acceptance-contract compiler V1.

Combines two already-owned one-sided sound surfaces:
1) human-authored rubric acceptance criteria;
2) source-bound explicit modal / imperative prompt requirements.

It does not infer the meaning of unresolved prompt text and does not claim that the
result is the whole GDPval task semantics or a human-preference model.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.gdpval_rubric_acceptance_index_v1 import build_rubric_acceptance_index
from canonical.runtime.explicit_requirement_index_v2 import build_index as build_requirement_index

SCHEMA="PROJECT_BRAIN_GDPVAL_EXPLICIT_ACCEPTANCE_CONTRACT_V1"


def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _fail(reason:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "terminal_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
    }


def compile_task(row:Mapping[str,Any],*,source_revision:str)->dict[str,Any]:
    if not isinstance(row,Mapping):
        return _fail("ROW_NOT_MAPPING")
    task_id=row.get("task_id")
    prompt=row.get("prompt")
    if not isinstance(task_id,str) or not task_id.strip():
        return _fail("TASK_ID_MISSING")
    if not isinstance(prompt,str) or not prompt.strip():
        return _fail("PROMPT_MISSING")
    if not isinstance(source_revision,str) or not source_revision.strip():
        return _fail("SOURCE_REVISION_MISSING")

    rubric=build_rubric_acceptance_index([row],source_revision=source_revision)
    if rubric.get("status")!="INDEXED_EXPLICIT_RUBRIC_ACCEPTANCE_CRITERIA":
        return _fail("RUBRIC_INDEX_FAIL_CLOSED:"+str(rubric.get("errors") or rubric.get("status")))

    req=build_requirement_index(prompt,source_id=task_id)
    if str(req.get("status") or "").startswith("FAIL_CLOSED"):
        return _fail("PROMPT_REQUIREMENT_INDEX_FAIL_CLOSED:"+str(req.get("errors") or req.get("status")))

    task_contracts=rubric.get("tasks") or []
    if len(task_contracts)!=1:
        return _fail("RUBRIC_SINGLE_TASK_CONTRACT_MISSING")
    rubric_contract=task_contracts[0]

    requirements=[]
    for x in req.get("modal_obligations") or []:
        requirements.append({
            "requirement_id":x["requirement_id"],
            "kind":"MODAL_OBLIGATION",
            "source_id":x["source_id"],
            "segment_span":x["segment_span"],
            "segment_sha256":x["segment_sha256"],
            "semantic_graph":x["semantic_graph"],
            "condition":x.get("condition"),
        })
    for x in req.get("imperative_directives") or []:
        requirements.append({
            "requirement_id":x["requirement_id"],
            "kind":"IMPERATIVE_RAW_ACTION",
            "source_id":x["source_id"],
            "segment_span":x["segment_span"],
            "segment_sha256":x["segment_sha256"],
            "directive":x["directive"],
            "context":x.get("context"),
        })

    explicit_atoms=[
        {"atom_id":"CRITERION::"+x["criterion_id"],"kind":"RUBRIC_CRITERION"}
        for x in rubric_contract.get("criteria") or []
    ]+[
        {"atom_id":"REQUIREMENT::"+x["requirement_id"],"kind":x["kind"]}
        for x in requirements
    ]

    payload={
        "task_id":task_id.strip(),
        "source_revision":source_revision.strip(),
        "prompt_sha256":sha256(prompt.encode("utf-8")).hexdigest(),
        "rubric_contract_sha256":rubric_contract["contract_sha256"],
        "criteria":rubric_contract.get("criteria") or [],
        "requirements":requirements,
        "explicit_acceptance_atoms":explicit_atoms,
        "unresolved_prompt_segments":req.get("unresolved_segments") or [],
        "ignored_prompt_segments":req.get("ignored_segments") or [],
    }
    contract_sha=sha256(_canon(payload).encode("utf-8")).hexdigest()

    return {
        "schema":SCHEMA,
        "status":"COMPILED_EXPLICIT_ACCEPTANCE_CONTRACT_WITH_OPEN_COMPLEMENT",
        **payload,
        "explicit_criterion_count":len(payload["criteria"]),
        "explicit_requirement_count":len(requirements),
        "explicit_acceptance_atom_count":len(explicit_atoms),
        "contract_sha256":contract_sha,
        "open_complement":{
            "unresolved_prompt_segment_count":len(payload["unresolved_prompt_segments"]),
            "ignored_prompt_segment_count":len(payload["ignored_prompt_segments"]),
            "unstated_task_meaning_closed":False,
            "holistic_pairwise_human_preference_closed":False,
            "reference_file_semantics_closed":False,
            "gold_deliverable_quality_closed":False,
        },
        "one_sided_sound_explicit_surface":True,
        "whole_task_semantic_completeness_claim":False,
        "policy_adequacy_claim":False,
        "human_preference_adequacy_claim":False,
        "terminal_authority":False,
        "promotion_authority":False,
        "terminal_credit_delta":0,
        "next_interface":{
            "rule":"MATCH_ONLY_EXPLICIT_ACCEPTANCE_ATOMS_TO_CONTENT_ADDRESSED_BRAIN_OWNED_ADEQUACY_OR_DOMINANCE_ROUTES__KEEP_ALL_UNMATCHED_OR_UNRESOLVED_COMPLEMENT_OPEN",
            "adaptive_solver_target_atoms":[x["atom_id"] for x in explicit_atoms],
        },
    }


def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    args=args or {}
    return compile_task(args.get("row") or {},source_revision=str(args.get("source_revision") or ""))
