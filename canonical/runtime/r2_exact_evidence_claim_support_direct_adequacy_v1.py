"""R2 direct adequacy for exact evidence-backed quoted claim support.

Bounded family only:
- one repository-local verified generic V2 evidence extraction;
- one exact quoted claim embedded in the raw goal;
- one repository-local JSON result;
- producer is evidence.claim_relation.generic_units.stdlib;
- acceptance independently reconstructs evidence-unit integrity and exact
  normalized substring support.

This proves only exact textual support inside already-grounded evidence units.
It does not prove paraphrase, entailment, factual correctness, causality,
quality, sufficiency, or source independence.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import generic_evidence_claim_relation
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_EXACT_EVIDENCE_CLAIM_SUPPORT_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::EXACT_GROUNDED_EVIDENCE_CLAIM_SUPPORT_FAMILY_V1"
CAPABILITY_ID="evidence.claim_relation.generic_units.stdlib"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r'^Verify that grounded evidence in (?P<extraction>'+_PATH+r'\.json) '
    r'contains exactly "(?P<claim>[^"\r\n]{1,2000})" and save the verified '
    r'claim result to (?P<output>'+_PATH+r'\.json)\.?$',
    re.IGNORECASE,
)


def _base(status:str, passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "matched":False,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "direct_adequacy_authority":False,
        "execution_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _canon(value:Any)->str:
    return " ".join(str(value or "").split())


def _sha_bytes(value:bytes)->str:
    return sha256(value).hexdigest()


def _sha_text(value:str)->str:
    return sha256(value.encode("utf-8")).hexdigest()


def _inside(root:Path, rel:str)->Path:
    rr=root.resolve()
    p=(rr/str(rel)).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _validate_extraction(extraction:Any)->dict[str,dict[str,Any]]:
    if not isinstance(extraction,Mapping):
        raise ValueError("EXTRACTION_NOT_OBJECT")
    if extraction.get("schema")!="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2":
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if (
        extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
        or extraction.get("output_verified") is not True
    ):
        raise ValueError("VERIFIED_GENERIC_EXTRACTION_REQUIRED")
    page_sha=str(extraction.get("page_raw_sha256") or "")
    visible_sha=str(extraction.get("visible_text_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",page_sha):
        raise ValueError("PAGE_SHA_INVALID")
    if not re.fullmatch(r"[0-9a-f]{64}",visible_sha):
        raise ValueError("VISIBLE_SHA_INVALID")
    rows=extraction.get("evidence_units")
    if not isinstance(rows,list) or not rows:
        raise ValueError("EVIDENCE_UNITS_REQUIRED")
    out={}
    for row in rows:
        if not isinstance(row,Mapping):
            raise ValueError("EVIDENCE_UNIT_INVALID")
        uid=str(row.get("evidence_unit_id") or "")
        text=_canon(row.get("text"))
        text_sha=str(row.get("text_sha256") or "")
        start=row.get("visible_text_start")
        end=row.get("visible_text_end")
        if not re.fullmatch(r"[0-9a-f]{64}",uid):
            raise ValueError("EVIDENCE_UNIT_ID_INVALID")
        if uid in out:
            raise ValueError("EVIDENCE_UNIT_ID_DUPLICATE")
        if not text or _sha_text(text)!=text_sha:
            raise ValueError("EVIDENCE_UNIT_TEXT_HASH_MISMATCH")
        if (
            str(row.get("page_raw_sha256") or "")!=page_sha
            or str(row.get("visible_text_sha256") or "")!=visible_sha
        ):
            raise ValueError("EVIDENCE_UNIT_PAGE_BINDING_MISMATCH")
        if (
            not isinstance(start,int)
            or isinstance(start,bool)
            or not isinstance(end,int)
            or isinstance(end,bool)
            or start<0
            or end<=start
            or end-start!=len(text)
        ):
            raise ValueError("EVIDENCE_UNIT_OFFSET_INVALID")
        expected_uid=_sha_text(f"{page_sha}:{start}:{end}:{text_sha}")
        if uid!=expected_uid:
            raise ValueError("EVIDENCE_UNIT_ID_BINDING_MISMATCH")
        out[uid]={
            "evidence_unit_id":uid,
            "text":text,
            "text_sha256":text_sha,
            "source_url":str(row.get("source_url") or extraction.get("source_url") or ""),
            "visible_text_start":start,
            "visible_text_end":end,
        }
    return out


def _independent_matches(extraction:Any, claim:str)->list[dict[str,Any]]:
    units=_validate_extraction(extraction)
    needle=_canon(claim).casefold()
    if not needle:
        raise ValueError("CLAIM_TEXT_REQUIRED")
    matches=[]
    for uid in sorted(units):
        unit=units[uid]
        hay=unit["text"].casefold()
        pos=hay.find(needle)
        if pos>=0:
            matches.append({
                "evidence_unit_id":uid,
                "source_url":unit["source_url"],
                "text_sha256":unit["text_sha256"],
                "claim_text":_canon(claim),
                "match_start":pos,
                "match_end":pos+len(_canon(claim)),
            })
    return matches


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["evidence.claim.exact_text_support"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids=list(
        (contract.get("acceptance_contract") or {}).get("required_obligation_ids")
        or []
    )
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def preflight(
    request:Mapping[str,Any],
    *,
    repo_root:str|Path|None=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    task_id=str(request.get("task_id") or "").strip()
    goal=str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    match=GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"),"matched":False}

    try:
        extraction_rel=match.group("extraction")
        output_rel=match.group("output")
        claim=_canon(match.group("claim"))
        extraction_path=_inside(root,extraction_rel)
        output_path=_inside(root,output_rel)
        if extraction_path==output_path:
            raise ValueError("EXTRACTION_OUTPUT_COLLISION")
        if not extraction_path.is_file():
            raise ValueError("EXTRACTION_INPUT_MISSING")

        extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
        matches=_independent_matches(extraction,claim)
        if not matches:
            raise ValueError("EXACT_CLAIM_NOT_PRESENT_IN_GROUNDED_EVIDENCE")

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("CLAIM_RELATION_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        if str(entry.get("adapter_module") or "")!="generic_evidence_claim_relation":
            raise ValueError("CLAIM_RELATION_ADAPTER_BINDING_MISMATCH")
        verification=entry.get("verification")
        if not isinstance(verification,Mapping):
            raise ValueError("CLAIM_RELATION_VERIFICATION_REQUIRED")

        contract=_raw_contract(goal)
        raw_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        goal_sha=_sha_text(goal)
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "task_id":task_id,
            "goal":goal,
            "goal_sha256":goal_sha,
            "policy_id":goal_scoped_policy_id(CAPABILITY_ID,goal),
            "capability_id":CAPABILITY_ID,
            "extraction_path":extraction_rel,
            "extraction_sha256":_sha_bytes(extraction_path.read_bytes()),
            "claim_text":claim,
            "claim_sha256":_sha_text(claim),
            "expected_match_ids":[row["evidence_unit_id"] for row in matches],
            "output_path":output_rel,
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids":raw_ids,
            "semantic_scope":"EXACT_NORMALIZED_SUBSTRING_SUPPORT_OVER_INTEGRITY_CHECKED_GROUNDED_EVIDENCE_UNITS",
            "preflight_execution_authority":False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "reason":type(exc).__name__+":"+str(exc),
        }


def _restore(path:Path, existed:bool, original:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(original or b"")
    elif path.exists():
        path.unlink()


def run(
    request:Mapping[str,Any],
    *,
    repo_root:str|Path|None=None,
)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf

    extraction_path=_inside(root,str(pf["extraction_path"]))
    output_path=_inside(root,str(pf["output_path"]))
    existed=output_path.is_file()
    original=output_path.read_bytes() if existed else None

    try:
        if _sha_bytes(extraction_path.read_bytes())!=pf["extraction_sha256"]:
            raise RuntimeError("EXTRACTION_DRIFT_BEFORE_EXECUTION")

        producer=generic_evidence_claim_relation.run(
            {
                "extraction_path":pf["extraction_path"],
                "spec":{
                    "mode":"VERBATIM_SUPPORT",
                    "claim_text":pf["claim_text"],
                },
                "output_path":pf["output_path"],
            },
            root,
        )
        if (
            not isinstance(producer,Mapping)
            or producer.get("output_verified") is not True
            or producer.get("status")!="EXACT_TEXT_SUPPORT_VERIFIED"
            or _canon(producer.get("claim_text"))!=pf["claim_text"]
        ):
            raise RuntimeError("CLAIM_SUPPORT_PRODUCER_DID_NOT_VERIFY")
        if _sha_bytes(extraction_path.read_bytes())!=pf["extraction_sha256"]:
            raise RuntimeError("EXTRACTION_MUTATED_BY_PRODUCER")
        if not output_path.is_file():
            raise RuntimeError("CLAIM_RESULT_OUTPUT_MISSING")

        extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
        independent=_independent_matches(extraction,pf["claim_text"])
        independent_ids=[row["evidence_unit_id"] for row in independent]
        producer_ids=sorted(
            str(row.get("evidence_unit_id") or "")
            for row in (producer.get("matches") or [])
            if isinstance(row,Mapping)
        )
        expected_ids=sorted(pf["expected_match_ids"])
        if sorted(independent_ids)!=expected_ids or producer_ids!=expected_ids:
            raise RuntimeError("INDEPENDENT_EXACT_CLAIM_SUPPORT_MISMATCH")

        result_json=json.loads(output_path.read_text(encoding="utf-8"))
        if (
            result_json.get("status")!="EXACT_TEXT_SUPPORT_VERIFIED"
            or _canon(result_json.get("claim_text"))!=pf["claim_text"]
            or sorted(
                str(row.get("evidence_unit_id") or "")
                for row in (result_json.get("matches") or [])
                if isinstance(row,Mapping)
            )!=expected_ids
        ):
            raise RuntimeError("CLAIM_RESULT_FILE_BINDING_MISMATCH")

        contract=_raw_contract(str(request["goal"]))
        accepted_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        if accepted_ids!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "selected_policy_id":pf["policy_id"],
            "goal_sha256":pf["goal_sha256"],
            "extraction_path":pf["extraction_path"],
            "extraction_sha256":pf["extraction_sha256"],
            "claim_text":pf["claim_text"],
            "claim_sha256":pf["claim_sha256"],
            "output_path":pf["output_path"],
            "output_sha256":_sha_bytes(output_path.read_bytes()),
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted_ids,
            "raw_acceptance_obligation_count":len(accepted_ids),
            "producer_result":deepcopy(dict(producer)),
            "acceptance_receipt":{
                "verified":True,
                "producer_independent":True,
                "verifier":"r2_exact_claim_support_independent_integrity_and_substring_recomputation",
                "claim_text":pf["claim_text"],
                "match_count":len(expected_ids),
                "matched_evidence_unit_ids":expected_ids,
                "extraction_immutability_verified":True,
            },
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_committed":True,
            "transaction_rolled_back":False,
            "authority_boundary":(
                "EXACT_QUOTED_CLAIM_SUPPORT_OVER_ALREADY_GROUNDED_GENERIC_V2_EVIDENCE_ONLY;"
                "EXACT_NORMALIZED_SUBSTRING_OCCURRENCE_ONLY;"
                "INDEPENDENT_EVIDENCE_HASH_OFFSET_AND_MATCH_RECOMPUTATION;"
                "ONE_REPOSITORY_LOCAL_JSON_OUTPUT;"
                "NO_PARAPHRASE_ENTAILMENT_FACTUAL_CORRECTNESS_CAUSALITY_QUALITY_SUFFICIENCY_OR_SOURCE_INDEPENDENCE_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(output_path,existed,original)
        return {
            **_base("FAIL_CLOSED"),
            "matched":True,
            "route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,
            "policy_id":pf.get("policy_id"),
            "goal_sha256":pf.get("goal_sha256"),
            "reason":type(exc).__name__+":"+str(exc),
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_rolled_back":True,
        }
