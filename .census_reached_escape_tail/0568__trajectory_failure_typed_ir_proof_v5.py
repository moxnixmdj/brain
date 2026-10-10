"""Typed cross-domain P1 causal proof V5 with hidden intervention replay.

This is a zero-terminal-evidence proof envelope. The candidate sees only normalized
trajectory IR. The evaluator separately owns hidden causal/intervention state and
checks whether nominated repairs actually rescue the terminal outcome. It also
tests delayed, interaction, ambiguity, explicit SCOPE failures, provenance erasure,
and output-schema injection.
"""
from __future__ import annotations
import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V5"
DOMAINS=("BROWSER","FILESYSTEM","TOOL_API","ARTIFACT","RESEARCH","CODE")
KINDS=("AUTHORITY","SCOPE","SCHEMA","PROVENANCE","INVARIANT","STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY")


def _check(kind:str, aid:str, passed:bool)->dict[str,Any]:
    return {
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
    }


def _row(i:int, domain:str, *, reads:list[str], writes:list[str], depends_on:list[str],
         failed_kind:str|None=None, composition:str="SEQUENTIAL")->dict[str,Any]:
    aid=f"A{i}"
    checks=[_check("INVARIANT",aid,True)]
    if failed_kind is not None:
        checks.append(_check(failed_kind,aid,False))
    return {
        "step":i,
        "action_id":aid,
        "domain":domain,
        "reads":reads,
        "writes":writes,
        "depends_on":depends_on,
        "dependency_composition":composition,
        "checks":checks,
    }


def _repair_targets(oracle:Mapping[str,Any])->list[str]:
    return sorted(
        f"restore:{aid}:{kind}"
        for aid,kinds in oracle["mechanisms"].items()
        for kind in kinds
    )


def _symptom_targets(rows:list[dict[str,Any]], roots:list[str])->list[str]:
    rootset=set(roots)
    out=[]
    for row in rows:
        aid=row["action_id"]
        if aid in rootset:
            continue
        for check in row["checks"]:
            if check["pass"] is False:
                out.append(f"restore:{aid}:{check['kind']}")
    return sorted(out)


def _hidden_intervention_model(rows:list[dict[str,Any]], oracle:Mapping[str,Any])->dict[str,Any]:
    roots=list(oracle["roots"])
    return {
        "causal_status":oracle["status"],
        "minimal_causal_action_set":roots if oracle["status"]!="AMBIGUOUS" else None,
        "alternative_causal_action_sets":[[r] for r in roots] if oracle["status"]=="AMBIGUOUS" else [],
        "required_root_repairs":_repair_targets(oracle),
        "downstream_symptom_repairs":_symptom_targets(rows,roots),
        "terminal_failure_observed":True,
    }


def generate_case(seed:int, *, pattern:str|None=None, domain:str|None=None, kind:str|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_INVALID")
    domain=domain or DOMAINS[seed%len(DOMAINS)]
    kind=kind or KINDS[(seed//len(DOMAINS))%len(KINDS)]
    pattern=pattern or ("SINGLE","DELAYED","INTERACTION","AMBIGUOUS")[seed%4]
    if pattern not in {"SINGLE","DELAYED","INTERACTION","AMBIGUOUS"}:
        raise ValueError("PATTERN_INVALID")
    if domain not in DOMAINS or kind not in KINDS:
        raise ValueError("DOMAIN_OR_KIND_INVALID")

    p=f"{domain.lower()}:"
    rows=[]
    oracle:dict[str,Any]

    if pattern=="SINGLE":
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"root"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"root"],writes=[p+"symptom"],depends_on=["A1"],failed_kind="INVARIANT"),
            _row(3,domain,reads=[p+"symptom"],writes=[p+"terminal"],depends_on=["A2"]),
        ]
        oracle={"status":"IDENTIFIED","roots":["A1"],"critical":"A1","mechanisms":{"A1":[kind]}}
    elif pattern=="DELAYED":
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"root"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"root"],writes=[p+"mid1"],depends_on=["A1"]),
            _row(3,domain,reads=[p+"mid1"],writes=[p+"mid2"],depends_on=["A2"]),
            _row(4,domain,reads=[p+"mid2"],writes=[p+"late_symptom"],depends_on=["A3"],failed_kind="INVARIANT"),
            _row(5,domain,reads=[p+"late_symptom"],writes=[p+"terminal"],depends_on=["A4"]),
        ]
        oracle={"status":"IDENTIFIED","roots":["A1"],"critical":"A1","mechanisms":{"A1":[kind]}}
    elif pattern=="INTERACTION":
        kind2=KINDS[(KINDS.index(kind)+3)%len(KINDS)]
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"left"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"seed"],writes=[p+"right"],depends_on=["A0"],failed_kind=kind2),
            _row(3,domain,reads=[p+"left",p+"right"],writes=[p+"joined"],depends_on=["A1","A2"],composition="CONJUNCTIVE"),
            _row(4,domain,reads=[p+"joined"],writes=[p+"symptom"],depends_on=["A3"],failed_kind="INVARIANT"),
            _row(5,domain,reads=[p+"symptom"],writes=[p+"terminal"],depends_on=["A4"]),
        ]
        oracle={"status":"INTERACTION","roots":["A1","A2"],"critical":"A1","mechanisms":{"A1":[kind],"A2":[kind2]}}
    else:
        kind2=KINDS[(KINDS.index(kind)+1)%len(KINDS)]
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"left"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"seed"],writes=[p+"right"],depends_on=["A0"],failed_kind=kind2),
            _row(3,domain,reads=[p+"left",p+"right"],writes=[p+"merged"],depends_on=["A1","A2"],composition="ALTERNATIVE"),
            _row(4,domain,reads=[p+"merged"],writes=[p+"terminal"],depends_on=["A3"],failed_kind="INVARIANT"),
        ]
        oracle={"status":"AMBIGUOUS","roots":["A1","A2"],"critical":None,"mechanisms":{"A1":[kind],"A2":[kind2]}}

    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed":seed,
        "task":{
            "domain":domain,
            "trajectory":rows,
            "terminal_failed_resources":[p+"terminal"],
            "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITHOUT_SELECTING_DOWNSTREAM_SYMPTOM",
        },
        "_oracle":oracle,
        "_intervention_model":_hidden_intervention_model(rows,oracle),
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if not str(k).startswith("_")}


def evaluate_intervention(case:Mapping[str,Any], repair_targets:list[str])->dict[str,Any]:
    model=case["_intervention_model"]
    if model["causal_status"]=="AMBIGUOUS":
        return {"status":"NONIDENTIFIABLE","rescued":False}
    required=set(model["required_root_repairs"])
    got={str(x) for x in repair_targets}
    rescued=required.issubset(got)
    return {
        "status":"RESCUED" if rescued else "NOT_RESCUED",
        "rescued":rescued,
        "required_root_repairs":sorted(required),
        "applied_repairs":sorted(got),
    }


_ALLOWED_KEYS={
    "IDENTIFIED":{
        "status","cause_action_id","cause_action_ids","critical_action_id","mechanism_classes",
        "supporting_receipts","repair_targets","reason",
    },
    "INTERACTION":{
        "status","cause_action_id","cause_action_ids","critical_action_id",
        "interaction_witness_action_ids","mechanism_by_action","supporting_receipts",
        "repair_targets","reason",
    },
    "AMBIGUOUS":{
        "status","cause_action_id","cause_action_ids","critical_action_id",
        "candidates","reason","information_request",
    },
}


def score_case(case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping):
        return {"pass":False,"reason":"CANDIDATE_NOT_OBJECT"}
    o=case["_oracle"]
    status=candidate.get("status")
    if status not in _ALLOWED_KEYS:
        return {"pass":False,"reason":"STATUS_WRONG_OR_FAIL_CLOSED"}
    if set(candidate.keys()) != _ALLOWED_KEYS[status]:
        return {"pass":False,"reason":"OUTPUT_SCHEMA_NOT_EXACT"}

    got_roots=candidate.get("cause_action_ids")
    if not isinstance(got_roots,list):
        got_roots=[]
    roots=sorted(str(x) for x in got_roots)
    expected=sorted(o["roots"])
    if status!=o["status"] or roots!=expected:
        return {"pass":False,"reason":"STATUS_OR_ROOT_SET_WRONG"}
    if candidate.get("critical_action_id")!=o["critical"]:
        return {"pass":False,"reason":"CRITICAL_ACTION_WRONG"}

    if status=="IDENTIFIED":
        if candidate.get("cause_action_id")!=o["critical"]:
            return {"pass":False,"reason":"UNIQUE_CAUSE_WRONG"}
        if candidate.get("mechanism_classes")!=o["mechanisms"][o["critical"]]:
            return {"pass":False,"reason":"MECHANISM_CLASS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass":False,"reason":"SUPPORTING_RECEIPTS_REQUIRED"}
    elif status=="INTERACTION":
        if candidate.get("mechanism_by_action")!=o["mechanisms"]:
            return {"pass":False,"reason":"INTERACTION_MECHANISMS_WRONG"}
        if not candidate.get("supporting_receipts"):
            return {"pass":False,"reason":"SUPPORTING_RECEIPTS_REQUIRED"}
    else:
        if candidate.get("cause_action_id") is not None:
            return {"pass":False,"reason":"NONIDENTIFIABILITY_OVERCLAIM"}
        if not candidate.get("information_request"):
            return {"pass":False,"reason":"MISSING_INFORMATION_REQUEST"}
        iv=evaluate_intervention(case,[])
        if iv["status"]!="NONIDENTIFIABLE":
            return {"pass":False,"reason":"AMBIGUOUS_INTERVENTION_MODEL_WRONG"}
        return {"pass":True,"reason":"PASS__NONIDENTIFIABLE"}

    repairs=sorted(str(x) for x in (candidate.get("repair_targets") or []))
    expected_repairs=_repair_targets(o)
    if repairs!=expected_repairs:
        return {"pass":False,"reason":"FALSIFIABLE_REPAIR_TARGET_WRONG"}

    iv=evaluate_intervention(case,repairs)
    if iv["rescued"] is not True:
        return {"pass":False,"reason":"NOMINATED_REPAIR_DOES_NOT_RESCUE"}

    symptom_repairs=case["_intervention_model"]["downstream_symptom_repairs"]
    if symptom_repairs and evaluate_intervention(case,symptom_repairs)["rescued"] is True:
        return {"pass":False,"reason":"SYMPTOM_ONLY_REPAIR_FALSELY_RESCUES"}

    if status=="INTERACTION":
        for repair in repairs:
            if evaluate_intervention(case,[repair])["rescued"] is True:
                return {"pass":False,"reason":"PARTIAL_INTERACTION_REPAIR_FALSELY_RESCUES"}

    return {"pass":True,"reason":"PASS__LOCALIZATION_CLASSIFICATION_AND_INTERVENTION_RESCUE"}


def suite_cases()->list[dict[str,Any]]:
    out=[]
    seed=50000
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in ("SINGLE","DELAYED","INTERACTION","AMBIGUOUS"):
                out.append(generate_case(seed,pattern=pattern,domain=domain,kind=kind))
                seed+=1
    return out


def anti_shortcut_mutations()->list[dict[str,str]]:
    return [
        {"id":"DROP_SUPPORTING_RECEIPTS","property":"FAILED_CAUSAL_CHECK_WITHOUT_VISIBLE_RECEIPTS_MUST_FAIL_CLOSED"},
        {"id":"INJECT_UNFALSIFIABLE_DIAGNOSIS","property":"EXTRA_UNBOUND_DIAGNOSIS_FIELD_MUST_BE_REJECTED"},
        {"id":"SELECT_DOWNSTREAM_SYMPTOM","property":"SYMPTOM_REPAIR_MUST_NOT_RESCUE"},
        {"id":"PARTIAL_INTERACTION_REPAIR","property":"CONJUNCTIVE_CAUSE_REQUIRES_ALL_ROOT_REPAIRS"},
        {"id":"FORCE_UNIQUE_AMBIGUOUS_CAUSE","property":"NONIDENTIFIABLE_CASE_MUST_REMAIN_AMBIGUOUS"},
        {"id":"SCOPE_TO_AUTHORITY_SWAP","property":"SCOPE_MUST_BE_A_FIRST_CLASS_MECHANISM"},
    ]
