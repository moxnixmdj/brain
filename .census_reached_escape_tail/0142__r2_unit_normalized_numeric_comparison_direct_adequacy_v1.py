"""R2 direct adequacy for unit-normalized explicit numeric comparisons.

Bounded family only:
- one verified generic V2 grounded-evidence extraction;
- one explicit comparison objective quoted in the raw goal;
- semantic left/right role binding is reused from the independently-qualified
  bounded objective binder;
- numeric operands may use different units only when both units are in this
  module's explicit multiplicative conversion table and share one dimension;
- producer arithmetic uses fractions.Fraction;
- acceptance independently parses numeric text to integer rational pairs and
  recomputes conversion and comparison by cross multiplication.

Affine units (for example Celsius/Fahrenheit), arbitrary units, inferred
dimensions, unit aliases outside the table, and compound dimensional algebra
outside the explicitly enumerated unit surfaces are rejected.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import objective_claim_operand_binding
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_UNIT_NORMALIZED_NUMERIC_COMPARISON_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::UNIT_NORMALIZED_GROUNDED_NUMERIC_COMPARISON_FAMILY_V1"
CAPABILITY_ID="evidence.claim_spec.bind.explicit_comparison.stdlib"
ROOT=Path(__file__).resolve().parents[2]
_PATH=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
    r'^Using grounded evidence in (?P<extraction>'+_PATH+r'\.json), '
    r'verify unit-normalized comparison objective "(?P<objective>[^"\r\n]{1,2000})" '
    r'and save the verified comparison result to (?P<output>'+_PATH+r'\.json)\.?$',
    re.IGNORECASE,
)
_NUM=re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"([-+]?(?:(?:\d{1,3}(?:,\d{3})+)|\d+|\.\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"(?:\s*([%A-Za-zµμ°][A-Za-z0-9µμ°/%^·*._-]{0,31}))?"
)
OPS={"LT","LTE","GT","GTE","EQ","NE","ABS_DIFF_LTE"}

# Exact multiplicative factors into one canonical unit per dimension.
# Case is significant where SI prefixes are case-sensitive.
_UNIT_TABLE={
    # length -> m
    "m":("length",1,1),"km":("length",1000,1),"cm":("length",1,100),
    "mm":("length",1,1000),"µm":("length",1,1_000_000),"μm":("length",1,1_000_000),
    # time -> s
    "s":("time",1,1),"ms":("time",1,1000),"min":("time",60,1),"h":("time",3600,1),
    # mass -> kg
    "kg":("mass",1,1),"g":("mass",1,1000),"mg":("mass",1,1_000_000),"t":("mass",1000,1),
    # force -> N
    "N":("force",1,1),"kN":("force",1000,1),"MN":("force",1_000_000,1),
    # power -> W
    "W":("power",1,1),"kW":("power",1000,1),"MW":("power",1_000_000,1),"GW":("power",1_000_000_000,1),
    # energy -> J
    "J":("energy",1,1),"kJ":("energy",1000,1),"MJ":("energy",1_000_000,1),"GJ":("energy",1_000_000_000,1),
    "Wh":("energy",3600,1),"kWh":("energy",3_600_000,1),"MWh":("energy",3_600_000_000,1),
    # pressure -> Pa
    "Pa":("pressure",1,1),"kPa":("pressure",1000,1),"MPa":("pressure",1_000_000,1),"GPa":("pressure",1_000_000_000,1),
    # voltage -> V
    "V":("voltage",1,1),"mV":("voltage",1,1000),"kV":("voltage",1000,1),
    # current -> A
    "A":("current",1,1),"mA":("current",1,1000),"kA":("current",1000,1),
    # frequency -> Hz
    "Hz":("frequency",1,1),"kHz":("frequency",1000,1),"MHz":("frequency",1_000_000,1),"GHz":("frequency",1_000_000_000,1),
    # speed -> m/s
    "m/s":("speed",1,1),"km/h":("speed",5,18),"km/s":("speed",1000,1),"m/min":("speed",1,60),
}


def _base(status:str, passed:bool=False)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,"matched":False,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "direct_adequacy_authority":False,"execution_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _canon(value:Any)->str:
    return " ".join(str(value or "").strip().split())


def _sha_text(value:str)->str:
    return sha256(value.encode("utf-8")).hexdigest()


def _sha_file(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _inside(root:Path, rel:str)->Path:
    rr=root.resolve(); p=(rr/str(rel)).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _validate_extraction(extraction:Any)->dict[str,dict[str,Any]]:
    if not isinstance(extraction,Mapping):
        raise ValueError("EXTRACTION_NOT_OBJECT")
    if extraction.get("schema")!="PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2":
        raise ValueError("EXTRACTION_SCHEMA_INVALID")
    if extraction.get("status")!="OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED" or extraction.get("output_verified") is not True:
        raise ValueError("VERIFIED_GENERIC_EXTRACTION_REQUIRED")
    page_sha=str(extraction.get("page_raw_sha256") or "")
    visible_sha=str(extraction.get("visible_text_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}",page_sha) or not re.fullmatch(r"[0-9a-f]{64}",visible_sha):
        raise ValueError("EXTRACTION_HASH_INVALID")
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
        start=row.get("visible_text_start"); end=row.get("visible_text_end")
        if not re.fullmatch(r"[0-9a-f]{64}",uid) or uid in out:
            raise ValueError("EVIDENCE_UNIT_ID_INVALID")
        if not text or _sha_text(text)!=text_sha:
            raise ValueError("EVIDENCE_UNIT_TEXT_HASH_MISMATCH")
        if str(row.get("page_raw_sha256") or "")!=page_sha or str(row.get("visible_text_sha256") or "")!=visible_sha:
            raise ValueError("EVIDENCE_UNIT_PAGE_BINDING_MISMATCH")
        if not isinstance(start,int) or isinstance(start,bool) or not isinstance(end,int) or isinstance(end,bool) or start<0 or end<=start or end-start!=len(text):
            raise ValueError("EVIDENCE_UNIT_OFFSET_INVALID")
        if uid!=_sha_text(f"{page_sha}:{start}:{end}:{text_sha}"):
            raise ValueError("EVIDENCE_UNIT_ID_BINDING_MISMATCH")
        out[uid]={"evidence_unit_id":uid,"text":text,"text_sha256":text_sha}
    return out


def _numbers(text:str)->list[dict[str,Any]]:
    rows=[]
    for index,m in enumerate(_NUM.finditer(text)):
        unit=(m.group(2) or "").strip().rstrip(".,;:")
        rows.append({
            "numeric_literal_index":index,
            "number_surface":m.group(1),
            "surface":m.group(0).strip().rstrip(".,;:"),
            "unit":unit,
        })
    return rows


def _unit(unit:str)->tuple[str,int,int]:
    row=_UNIT_TABLE.get(str(unit or ""))
    if row is None:
        raise ValueError("UNIT_NOT_IN_EXPLICIT_MULTIPLICATIVE_TABLE:"+str(unit))
    return row


def _bind_convertible_pair(extraction:Mapping[str,Any], parsed:Mapping[str,Any])->dict[str,Any]:
    binder_units=objective_claim_operand_binding._validated_units(extraction)
    left,reason=objective_claim_operand_binding._bind_role(binder_units,parsed["left_tokens"])
    if reason:
        raise ValueError("LEFT_"+reason)
    right,reason=objective_claim_operand_binding._bind_role(binder_units,parsed["right_tokens"])
    if reason:
        raise ValueError("RIGHT_"+reason)
    if left["evidence_unit_id"]==right["evidence_unit_id"]:
        raise ValueError("LEFT_RIGHT_ROLE_COLLISION")
    candidates=[]
    for a in _numbers(left["text"]):
        if not a["unit"] or a["unit"] not in _UNIT_TABLE:
            continue
        adim,anum,aden=_unit(a["unit"])
        for b in _numbers(right["text"]):
            if not b["unit"] or b["unit"] not in _UNIT_TABLE:
                continue
            bdim,bnum,bden=_unit(b["unit"])
            if adim==bdim and a["unit"]!=b["unit"]:
                candidates.append((a,b,adim,anum,aden,bnum,bden))
    if len(candidates)!=1:
        raise ValueError("CONVERTIBLE_OPERAND_PAIR_NOT_UNIQUE:"+str(len(candidates)))
    a,b,dim,anum,aden,bnum,bden=candidates[0]
    threshold=None
    if parsed["operator"]=="ABS_DIFF_LTE":
        nums=_numbers(str(parsed.get("threshold") or ""))
        if len(nums)!=1 or not nums[0]["unit"]:
            raise ValueError("THRESHOLD_EXPLICIT_UNIT_REQUIRED")
        t=nums[0]
        if t["unit"] not in _UNIT_TABLE:
            raise ValueError("THRESHOLD_UNIT_NOT_SUPPORTED")
        tdim,tnum,tden=_unit(t["unit"])
        if tdim!=dim:
            raise ValueError("THRESHOLD_DIMENSION_MISMATCH")
        threshold={**t,"dimension":tdim,"factor_num":tnum,"factor_den":tden}
    return {
        "left_binding":left,"right_binding":right,"dimension":dim,
        "left":{**a,"evidence_unit_id":left["evidence_unit_id"],"factor_num":anum,"factor_den":aden},
        "right":{**b,"evidence_unit_id":right["evidence_unit_id"],"factor_num":bnum,"factor_den":bden},
        "threshold":threshold,
    }


def _fraction_number(surface:str)->Fraction:
    text=str(surface).replace(",","")
    try:
        return Fraction(text)
    except Exception as exc:
        raise ValueError("NUMERIC_LITERAL_INVALID") from exc


def _producer_eval(bound:Mapping[str,Any], op:str)->dict[str,Any]:
    left=bound["left"]; right=bound["right"]
    lv=_fraction_number(left["number_surface"])*Fraction(int(left["factor_num"]),int(left["factor_den"]))
    rv=_fraction_number(right["number_surface"])*Fraction(int(right["factor_num"]),int(right["factor_den"]))
    threshold=None
    if op=="LT": pred=lv<rv
    elif op=="LTE": pred=lv<=rv
    elif op=="GT": pred=lv>rv
    elif op=="GTE": pred=lv>=rv
    elif op=="EQ": pred=lv==rv
    elif op=="NE": pred=lv!=rv
    elif op=="ABS_DIFF_LTE":
        t=bound["threshold"]
        threshold=_fraction_number(t["number_surface"])*Fraction(int(t["factor_num"]),int(t["factor_den"]))
        pred=abs(lv-rv)<=threshold
    else:
        raise ValueError("OPERATOR_UNSUPPORTED")
    return {
        "operator":op,"predicate":bool(pred),"dimension":bound["dimension"],
        "left_canonical_numerator":lv.numerator,"left_canonical_denominator":lv.denominator,
        "right_canonical_numerator":rv.numerator,"right_canonical_denominator":rv.denominator,
        "threshold_canonical_numerator":threshold.numerator if threshold is not None else None,
        "threshold_canonical_denominator":threshold.denominator if threshold is not None else None,
    }


def _decimal_ratio(surface:str)->tuple[int,int]:
    text=str(surface).replace(",","").strip()
    m=re.fullmatch(r"([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?",text)
    if not m:
        raise ValueError("INDEPENDENT_NUMERIC_LITERAL_INVALID")
    sign=-1 if m.group(1)=="-" else 1
    whole=m.group(2) or "0"
    frac=m.group(3) if m.group(2) is not None else m.group(4)
    frac=frac or ""
    exp=int(m.group(5) or "0")
    digits=(whole+frac).lstrip("0") or "0"
    num=sign*int(digits)
    den=10**len(frac)
    if exp>=0: num*=10**exp
    else: den*=10**(-exp)
    return num,den


def _mul_ratio(a:tuple[int,int], bnum:int, bden:int)->tuple[int,int]:
    return a[0]*int(bnum),a[1]*int(bden)


def _cmp_ratio(a:tuple[int,int],b:tuple[int,int])->int:
    x=a[0]*b[1]; y=b[0]*a[1]
    return -1 if x<y else (1 if x>y else 0)


def _abs_diff_lte(a:tuple[int,int],b:tuple[int,int],t:tuple[int,int])->bool:
    diff_num=abs(a[0]*b[1]-b[0]*a[1]); diff_den=a[1]*b[1]
    return diff_num*t[1] <= t[0]*diff_den


def _independent_eval(bound:Mapping[str,Any],op:str)->dict[str,Any]:
    left=bound["left"]; right=bound["right"]
    lv=_mul_ratio(_decimal_ratio(left["number_surface"]),left["factor_num"],left["factor_den"])
    rv=_mul_ratio(_decimal_ratio(right["number_surface"]),right["factor_num"],right["factor_den"])
    order=_cmp_ratio(lv,rv)
    threshold=None
    if op=="LT": pred=order<0
    elif op=="LTE": pred=order<=0
    elif op=="GT": pred=order>0
    elif op=="GTE": pred=order>=0
    elif op=="EQ": pred=order==0
    elif op=="NE": pred=order!=0
    elif op=="ABS_DIFF_LTE":
        t=bound["threshold"]
        threshold=_mul_ratio(_decimal_ratio(t["number_surface"]),t["factor_num"],t["factor_den"])
        pred=_abs_diff_lte(lv,rv,threshold)
    else:
        raise ValueError("OPERATOR_UNSUPPORTED")
    return {"operator":op,"predicate":bool(pred),"left_ratio":lv,"right_ratio":rv,"threshold_ratio":threshold}


def _raw_contract(goal:str)->dict[str,Any]:
    contract=compile_contract(goal,source_id="user",routing_target_effects=["evidence.numeric_relation.unit_normalized"])
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids=list((contract.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def preflight(request:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
    task_id=str(request.get("task_id") or "").strip(); goal=str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
    match=GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"),"matched":False}
    try:
        extraction_rel=match.group("extraction"); output_rel=match.group("output"); objective=_canon(match.group("objective"))
        extraction_path=_inside(root,extraction_rel); output_path=_inside(root,output_rel)
        if extraction_path==output_path: raise ValueError("EXTRACTION_OUTPUT_COLLISION")
        if not extraction_path.is_file(): raise ValueError("EXTRACTION_INPUT_MISSING")
        extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
        units=_validate_extraction(extraction)

        parsed,reason=objective_claim_operand_binding._parse_objective(objective)
        if reason or not isinstance(parsed,Mapping) or parsed.get("mode")!="NUMERIC_RELATION" or parsed.get("operator") not in OPS:
            raise ValueError("OBJECTIVE_NOT_IN_EXPLICIT_BOUNDED_NUMERIC_COMPARISON_SURFACE:"+str(reason))
        bound=_bind_convertible_pair(extraction,parsed)
        producer=_producer_eval(bound,parsed["operator"])
        independent=_independent_eval(bound,parsed["operator"])
        if producer["predicate"]!=independent["predicate"]:
            raise ValueError("PRODUCER_INDEPENDENT_PREFLIGHT_DISAGREEMENT")

        registry=live_bound.load_verified_registry()
        entry=registry.get(CAPABILITY_ID)
        if not isinstance(entry,Mapping) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            raise ValueError("ROLE_BINDER_VERIFIED_CAPABILITY_REQUIRED")
        if str(entry.get("adapter_module") or "")!="objective_claim_operand_binding":
            raise ValueError("ROLE_BINDER_ADAPTER_MISMATCH")
        ver=entry.get("verification")
        if not isinstance(ver,Mapping) or ver.get("independent_full_surface_cross_domain_status")!="PASS":
            raise ValueError("ROLE_BINDER_INDEPENDENT_QUALIFICATION_REQUIRED")

        contract=_raw_contract(goal); raw_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
            "task_id":task_id,"goal":goal,"goal_sha256":_sha_text(goal),
            "policy_id":goal_scoped_policy_id(CAPABILITY_ID,goal),"capability_id":CAPABILITY_ID,
            "extraction_path":extraction_rel,"extraction_sha256":_sha_file(extraction_path),
            "objective":objective,"objective_sha256":_sha_text(objective),"operator":parsed["operator"],
            "expected_predicate":producer["predicate"],"dimension":bound["dimension"],
            "left":bound["left"],"right":bound["right"],"threshold":bound["threshold"],
            "output_path":output_rel,"raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids":raw_ids,
            "semantic_scope":"EXPLICIT_MULTIPLICATIVE_UNIT_NORMALIZED_GROUNDED_NUMERIC_COMPARISON",
            "preflight_execution_authority":False,
        }
    except Exception as exc:
        return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,"reason":type(exc).__name__+":"+str(exc)}


def _restore(path:Path,existed:bool,original:bytes|None)->None:
    if existed:
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(original or b"")
    elif path.exists():
        path.unlink()


def run(request:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    pf=preflight(request,repo_root=root)
    if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED":
        return pf
    extraction_path=_inside(root,str(pf["extraction_path"])); output_path=_inside(root,str(pf["output_path"]))
    existed=output_path.is_file(); original=output_path.read_bytes() if existed else None
    try:
        if _sha_file(extraction_path)!=pf["extraction_sha256"]:
            raise RuntimeError("EXTRACTION_DRIFT_BEFORE_EXECUTION")
        extraction=json.loads(extraction_path.read_text(encoding="utf-8"))
        _validate_extraction(extraction)
        parsed,reason=objective_claim_operand_binding._parse_objective(pf["objective"])
        if reason or not isinstance(parsed,Mapping):
            raise RuntimeError("OBJECTIVE_BINDING_DRIFT")
        bound=_bind_convertible_pair(extraction,parsed)
        producer=_producer_eval(bound,parsed["operator"])
        independent=_independent_eval(bound,parsed["operator"])
        if producer["predicate"]!=independent["predicate"]:
            raise RuntimeError("INDEPENDENT_UNIT_NORMALIZED_COMPARISON_MISMATCH")
        if producer["predicate"]!=pf["expected_predicate"] or bound["dimension"]!=pf["dimension"]:
            raise RuntimeError("UNIT_NORMALIZED_COMPARISON_PREFLIGHT_DRIFT")
        if bound["left"]!=pf["left"] or bound["right"]!=pf["right"] or bound["threshold"]!=pf["threshold"]:
            raise RuntimeError("UNIT_NORMALIZED_OPERAND_BINDING_DRIFT")
        if _sha_file(extraction_path)!=pf["extraction_sha256"]:
            raise RuntimeError("EXTRACTION_MUTATED_DURING_EXECUTION")

        payload={
            "schema":SCHEMA,"status":"UNIT_NORMALIZED_NUMERIC_RELATION_VERIFIED",
            "objective":pf["objective"],"operator":pf["operator"],"predicate":producer["predicate"],
            "dimension":pf["dimension"],"left":pf["left"],"right":pf["right"],"threshold":pf["threshold"],
            "producer_fraction_result":producer,
            "independent_integer_ratio_result":independent,
            "output_verified":True,
        }
        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        readback=json.loads(output_path.read_text(encoding="utf-8"))
        if readback.get("status")!="UNIT_NORMALIZED_NUMERIC_RELATION_VERIFIED" or readback.get("predicate")!=producer["predicate"]:
            raise RuntimeError("UNIT_NORMALIZED_RESULT_FILE_BINDING_MISMATCH")

        contract=_raw_contract(str(request["goal"]))
        accepted_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
        if accepted_ids!=pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,"route_id":ROUTE_ID,
            "capability_id":CAPABILITY_ID,"selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
            "extraction_path":pf["extraction_path"],"extraction_sha256":pf["extraction_sha256"],
            "objective":pf["objective"],"operator":pf["operator"],"predicate":producer["predicate"],
            "dimension":pf["dimension"],"left":pf["left"],"right":pf["right"],"threshold":pf["threshold"],
            "output_path":pf["output_path"],"output_sha256":_sha_file(output_path),
            "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
            "accepted_raw_obligation_ids":accepted_ids,"raw_acceptance_obligation_count":len(accepted_ids),
            "acceptance_receipt":{
                "verified":True,"producer_independent_arithmetic_recomputation":True,
                "producer_arithmetic":"fractions.Fraction",
                "independent_arithmetic":"manual_integer_decimal_ratio_and_cross_multiplication",
                "predicate":producer["predicate"],"dimension":pf["dimension"],
                "left_unit":pf["left"]["unit"],"right_unit":pf["right"]["unit"],
                "semantic_role_binding_authority":"INHERITED_FROM_INDEPENDENTLY_QUALIFIED_BOUNDED_PRODUCER",
                "extraction_immutability_verified":True,
            },
            "execution_attempted":True,"retry_by_other_route_authorized":False,
            "transaction_committed":True,"transaction_rolled_back":False,
            "authority_boundary":(
                "EXPLICIT_BOUNDED_NUMERIC_COMPARISON_WITH_DIFFERENT_UNITS_ONLY;"
                "ONLY_ENUMERATED_MULTIPLICATIVE_UNIT_SURFACES_WITH_SHARED_EXPLICIT_DIMENSION;"
                "NO_AFFINE_TEMPERATURE_ARBITRARY_UNIT_DIMENSION_INFERENCE_OR_GENERAL_COMPOUND_UNIT_ALGEBRA;"
                "INHERITED_VERIFIED_LEXICAL_ROLE_BINDING_PLUS_DUAL_EXACT_RATIONAL_RECOMPUTATION"
            ),
        }
    except Exception as exc:
        _restore(output_path,existed,original)
        return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,
                "policy_id":pf.get("policy_id"),"goal_sha256":pf.get("goal_sha256"),
                "reason":type(exc).__name__+":"+str(exc),"execution_attempted":True,
                "retry_by_other_route_authorized":False,"transaction_rolled_back":True}
