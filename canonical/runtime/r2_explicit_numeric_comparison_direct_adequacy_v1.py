"""R2 direct adequacy for explicit bounded numeric comparison objectives.

Bounded family:
- one repository-local verified generic V2 grounded-evidence extraction;
- one explicit comparison objective quoted verbatim in the raw goal;
- one repository-local JSON result;
- producer is evidence.claim_spec.bind.explicit_comparison.stdlib;
- acceptance independently revalidates evidence-unit integrity, referenced
  numeric literals, exact unit compatibility, optional threshold, and Decimal
  predicate.

The producer's lexical semantic-role binding authority is inherited only from
its already independently-qualified bounded capability. This family adds no
general-language, unit-conversion, factual-correctness, causality, evidence-
sufficiency, or source-independence authority.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import objective_claim_operand_binding
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_EXPLICIT_NUMERIC_COMPARISON_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::EXPLICIT_GROUNDED_NUMERIC_COMPARISON_FAMILY_V1"
CAPABILITY_ID="evidence.claim_spec.bind.explicit_comparison.stdlib"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r'^Using grounded evidence in (?P<extraction>'+_PATH+r'\.json), '
    r'verify comparison objective "(?P<objective>[^"\r\n]{1,2000})" and save '
    r'the verified comparison result to (?P<output>'+_PATH+r'\.json)\.?$',
    re.IGNORECASE,
)
_NUMERIC=re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?"
)
OPS={"LT","LTE","GT","GTE","EQ","NE","ABS_DIFF_LTE"}


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


def _sha_text(value:str)->str:
    return sha256(value.encode("utf-8")).hexdigest()


def _sha_file(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _inside(root:Path, rel:str)->Path:
    rr=root.resolve()
    p=(rr/str(rel)).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _validated_units(extraction:Any)->dict[str,dict[str,Any]]:
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
            not isinstance(start,int) or isinstance(start,bool)
            or not isinstance(end,int) or isinstance(end,bool)
            or start<0 or end<=start or end-start!=len(text)
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
        }
    return out


def _numbers(text:str)->list[dict[str,Any]]:
    out=[]
    for index,m in enumerate(_NUMERIC.finditer(text)):
        raw=m.group(0).strip().rstrip(".,;:")
        number=m.group(1).replace(",","")
        unit=_canon(m.group(2)).lower().rstrip(".,;:")
        try:
            value=Decimal(number)
        except InvalidOperation as exc:
            raise ValueError("NUMERIC_LITERAL_PARSE_FAILED") from exc
        if not value.is_finite():
            raise ValueError("NUMERIC_LITERAL_NONFINITE")
        out.append({
            "numeric_literal_index":index,
            "raw":raw,
            "value":value,
            "unit":unit,
        })
    return out


def _resolve(units:Mapping[str,Mapping[str,Any]], ref:Any)->dict[str,Any]:
    if not isinstance(ref,Mapping):
        raise ValueError("NUMERIC_REFERENCE_INVALID")
    uid=str(ref.get("evidence_unit_id") or "")
    if uid not in units:
        raise ValueError("EVIDENCE_UNIT_REFERENCE_NOT_FOUND")
    index=ref.get("numeric_literal_index")
    if not isinstance(index,int) or isinstance(index,bool) or index<0:
        raise ValueError("NUMERIC_LITERAL_INDEX_INVALID")
    nums=_numbers(str(units[uid]["text"]))
    if index>=len(nums):
        raise ValueError("NUMERIC_LITERAL_INDEX_INVALID")
    x=dict(nums[index])
    x["evidence_unit_id"]=uid
    x["text_sha256"]=units[uid]["text_sha256"]
    return x


def _threshold(raw:Any, expected_unit:str)->Decimal:
    m=re.fullmatch(
        r"\s*([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
        r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?\s*",
        str(raw or ""),
    )
    if not m:
        raise ValueError("NUMERIC_RELATION_THRESHOLD_INVALID")
    value=Decimal(m.group(1).replace(",",""))
    unit=_canon(m.group(2)).lower().rstrip(".,;:")
    if value<0:
        raise ValueError("NUMERIC_RELATION_THRESHOLD_NEGATIVE")
    if unit!=expected_unit:
        raise ValueError("NUMERIC_RELATION_THRESHOLD_UNIT_MISMATCH")
    return value


def _independent_relation(extraction:Any, spec:Any)->dict[str,Any]:
    units=_validated_units(extraction)
    if not isinstance(spec,Mapping) or str(spec.get("mode") or "").upper()!="NUMERIC_RELATION":
        raise ValueError("NUMERIC_RELATION_SPEC_REQUIRED")
    op=str(spec.get("operator") or "").upper()
    if op not in OPS:
        raise ValueError("NUMERIC_RELATION_OPERATOR_INVALID")
    left=_resolve(units,spec.get("left"))
    right=_resolve(units,spec.get("right"))
    if left["unit"]!=right["unit"]:
        raise ValueError("NUMERIC_RELATION_UNIT_MISMATCH")
    lv,rv=left["value"],right["value"]
    threshold=None
    if op=="LT": predicate=lv<rv
    elif op=="LTE": predicate=lv<=rv
    elif op=="GT": predicate=lv>rv
    elif op=="GTE": predicate=lv>=rv
    elif op=="EQ": predicate=lv==rv
    elif op=="NE": predicate=lv!=rv
    else:
        threshold=_threshold(spec.get("threshold"),left["unit"])
        predicate=abs(lv-rv)<=threshold
    return {
        "operator":op,
        "predicate":bool(predicate),
        "left":{
            "evidence_unit_id":left["evidence_unit_id"],
            "numeric_literal_index":left["numeric_literal_index"],
            "value":str(left["value"]),
            "unit":left["unit"],
            "text_sha256":left["text_sha256"],
        },
        "right":{
            "evidence_unit_id":right["evidence_unit_id"],
            "numeric_literal_index":right["numeric_literal_index"],
            "value":str(right["value"]),
            "unit":right["unit"],
            "text_sha256":right["text_sha256"],
        },
        "threshold_value":str(threshold) if threshold is not None else None,
    }


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["evidence.numeric_relation.objective_bound"],
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
        objective=_canon(match.group("objective"))
        extraction_path=_inside(root,extraction_rel)
        output_path=_inside(root,output_rel)
        if extraction_path==output_path:
            raise ValueError("EXTRACTION_OUTPUT_COLLISION")
        if not extraction_path.is_file():
            raise ValueError("EXTRACTION_INPUT_MISSING")
        extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
        _validated_units(extraction)

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("CLAIM_BINDING_VERIFIED_BOUND_CAPABILITY_REQUIRED")
        if str(entry.get("adapter_module") or "")!="objective_claim_operand_binding":
            raise ValueError("CLAIM_BINDING_ADAPTER_MISMATCH")
        verification=entry.get("verification")
        if (
            not isinstance(verification,Mapping)
            or verification.get("independent_full_surface_cross_domain_status")!="PASS"
        ):
            raise ValueError("CLAIM_BINDING_INDEPENDENT_QUALIFICATION_REQUIRED")

        bound=objective_claim_operand_binding.bind(
            objective,extraction,evaluate_relation=False
        )
        if (
            not isinstance(bound,Mapping)
            or bound.get("status")!="CLAIM_SPEC_AND_OPERANDS_BOUND"
            or bound.get("output_verified") is not True
            or str((bound.get("relation_spec") or {}).get("mode") or "").upper()!="NUMERIC_RELATION"
        ):
            raise ValueError(
                "OBJECTIVE_NOT_IN_EXPLICIT_BOUNDED_NUMERIC_COMPARISON_SURFACE:"
                +str(bound.get("reason") if isinstance(bound,Mapping) else bound)
            )
        independent=_independent_relation(extraction,bound["relation_spec"])

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
            "extraction_sha256":_sha_file(extraction_path),
            "objective":objective,
            "objective_sha256":_sha_text(objective),
            "operator":independent["operator"],
            "expected_predicate":independent["predicate"],
            "expected_left":independent["left"],
            "expected_right":independent["right"],
            "expected_threshold_value":independent["threshold_value"],
            "output_path":output_rel,
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids":raw_ids,
            "semantic_scope":"EXPLICIT_BOUNDED_GROUNDED_NUMERIC_COMPARISON_GT_LT_GTE_LTE_EQ_NE_ABS_DIFF_LTE",
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
        if _sha_file(extraction_path)!=pf["extraction_sha256"]:
            raise RuntimeError("EXTRACTION_DRIFT_BEFORE_EXECUTION")

        producer=objective_claim_operand_binding.run(
            {
                "objective":pf["objective"],
                "extraction_path":pf["extraction_path"],
                "output_path":pf["output_path"],
            },
            root,
        )
        relation=producer.get("relation_result") if isinstance(producer,Mapping) else None
        if (
            not isinstance(producer,Mapping)
            or producer.get("status")!="CLAIM_SPEC_AND_OPERANDS_BOUND"
            or producer.get("output_verified") is not True
            or not isinstance(relation,Mapping)
            or relation.get("status")!="NUMERIC_RELATION_VERIFIED"
            or relation.get("output_verified") is not True
        ):
            raise RuntimeError("NUMERIC_COMPARISON_PRODUCER_DID_NOT_VERIFY")
        if _sha_file(extraction_path)!=pf["extraction_sha256"]:
            raise RuntimeError("EXTRACTION_MUTATED_BY_PRODUCER")
        if not output_path.is_file():
            raise RuntimeError("NUMERIC_COMPARISON_OUTPUT_MISSING")

        extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
        independent=_independent_relation(extraction,producer.get("relation_spec"))
        if (
            independent["operator"]!=pf["operator"]
            or independent["predicate"]!=pf["expected_predicate"]
            or independent["left"]!=pf["expected_left"]
            or independent["right"]!=pf["expected_right"]
            or independent["threshold_value"]!=pf["expected_threshold_value"]
        ):
            raise RuntimeError("INDEPENDENT_NUMERIC_COMPARISON_PREFLIGHT_DRIFT")

        if (
            str(relation.get("operator") or "").upper()!=independent["operator"]
            or bool(relation.get("predicate"))!=independent["predicate"]
            or str((relation.get("left") or {}).get("value"))!=independent["left"]["value"]
            or str((relation.get("right") or {}).get("value"))!=independent["right"]["value"]
            or str((relation.get("left") or {}).get("unit") or "")!=independent["left"]["unit"]
            or str((relation.get("right") or {}).get("unit") or "")!=independent["right"]["unit"]
        ):
            raise RuntimeError("INDEPENDENT_NUMERIC_COMPARISON_RESULT_MISMATCH")

        result_file=json.loads(output_path.read_text(encoding="utf-8"))
        file_relation=result_file.get("relation_result") if isinstance(result_file,Mapping) else None
        if (
            result_file.get("status")!="CLAIM_SPEC_AND_OPERANDS_BOUND"
            or not isinstance(file_relation,Mapping)
            or file_relation.get("status")!="NUMERIC_RELATION_VERIFIED"
            or bool(file_relation.get("predicate"))!=independent["predicate"]
        ):
            raise RuntimeError("NUMERIC_COMPARISON_FILE_BINDING_MISMATCH")

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
            "objective":pf["objective"],
            "objective_sha256":pf["objective_sha256"],
            "operator":independent["operator"],
            "predicate":independent["predicate"],
            "left":independent["left"],
            "right":independent["right"],
            "threshold_value":independent["threshold_value"],
            "output_path":pf["output_path"],
            "output_sha256":_sha_file(output_path),
            "semantic_scope":pf["semantic_scope"],
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted_ids,
            "raw_acceptance_obligation_count":len(accepted_ids),
            "producer_result":producer,
            "acceptance_receipt":{
                "verified":True,
                "producer_independent_relation_recomputation":True,
                "verifier":"python_decimal_plus_independent_evidence_integrity_recomputation",
                "operator":independent["operator"],
                "predicate":independent["predicate"],
                "left_value":independent["left"]["value"],
                "right_value":independent["right"]["value"],
                "unit":independent["left"]["unit"],
                "threshold_value":independent["threshold_value"],
                "extraction_immutability_verified":True,
                "semantic_role_binding_authority":"INHERITED_FROM_INDEPENDENTLY_QUALIFIED_BOUNDED_PRODUCER",
            },
            "execution_attempted":True,
            "retry_by_other_route_authorized":False,
            "transaction_committed":True,
            "transaction_rolled_back":False,
            "authority_boundary":(
                "EXPLICIT_BOUNDED_NUMERIC_COMPARISON_OBJECTIVES_ONLY;"
                "GT_LT_GTE_LTE_EQ_NE_ABS_DIFF_LTE;"
                "UNIQUE_LEXICAL_ROLE_BINDING_AND_EXACT_UNIT_COMPATIBLE_OPERANDS_ONLY;"
                "INDEPENDENT_DECIMAL_RELATION_AND_EVIDENCE_INTEGRITY_RECOMPUTATION;"
                "NO_GENERAL_LANGUAGE_UNIT_CONVERSION_FACTUAL_CORRECTNESS_CAUSALITY_SUFFICIENCY_OR_SOURCE_INDEPENDENCE_AUTHORITY"
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
