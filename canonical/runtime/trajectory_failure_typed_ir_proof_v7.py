"""V7 proof population for typed cross-domain trajectory diagnosis.

V7 extends the V6 forward-causal envelope in two load-bearing ways:
1) SCOPE is a first-class failure mechanism.
2) nominated repairs are actually applied to a public-semantics intervention model;
   non-ambiguous cases pass only when the intervention eliminates terminal failure.
No hidden cause label or rescue result is exposed to the candidate.
"""
from __future__ import annotations
import copy
import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V7"
DOMAINS=("BROWSER","FILESYSTEM","TOOL_API","ARTIFACT","RESEARCH","CODE")
KINDS=("AUTHORITY","SCOPE","SCHEMA","PROVENANCE","INVARIANT","STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY")
PATTERNS=("SINGLE","DELAYED","INTERACTION","SERIAL_COFAULT","AMBIGUOUS")


def _check(kind:str, aid:str, passed:bool, *, derived:bool=False)->dict[str,Any]:
    return {
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        "failure_semantics":"DERIVED_UPSTREAM" if (not passed and derived) else "DIRECT_CONTRACT",
    }


def _row(i:int, domain:str, *, reads:list[str], writes:list[str], depends_on:list[str],
         failed_kind:str|None=None, composition:str="SEQUENTIAL",
         derived_failure:bool=False)->dict[str,Any]:
    aid=f"A{i}"
    checks=[_check("INVARIANT",aid,True)]
    if failed_kind is not None:
        checks.append(_check(failed_kind,aid,False,derived=derived_failure))
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


def generate_case(seed:int, *, pattern:str|None=None, domain:str|None=None, kind:str|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_INVALID")
    r=random.Random(seed)
    domain=domain or DOMAINS[seed%len(DOMAINS)]
    kind=kind or KINDS[(seed//len(DOMAINS))%len(KINDS)]
    pattern=pattern or PATTERNS[seed%len(PATTERNS)]
    if pattern not in set(PATTERNS):
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
            _row(2,domain,reads=[p+"root"],writes=[p+"symptom"],depends_on=["A1"],failed_kind="INVARIANT",derived_failure=True),
            _row(3,domain,reads=[p+"symptom"],writes=[p+"terminal"],depends_on=["A2"]),
        ]
        oracle={"status":"IDENTIFIED","roots":["A1"],"critical":"A1","mechanisms":{"A1":[kind]}}

    elif pattern=="DELAYED":
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"root"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"root"],writes=[p+"mid1"],depends_on=["A1"]),
            _row(3,domain,reads=[p+"mid1"],writes=[p+"mid2"],depends_on=["A2"]),
            _row(4,domain,reads=[p+"mid2"],writes=[p+"late_symptom"],depends_on=["A3"],failed_kind="INVARIANT",derived_failure=True),
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
            _row(4,domain,reads=[p+"joined"],writes=[p+"symptom"],depends_on=["A3"],failed_kind="INVARIANT",derived_failure=True),
            _row(5,domain,reads=[p+"symptom"],writes=[p+"terminal"],depends_on=["A4"]),
        ]
        oracle={"status":"INTERACTION","roots":["A1","A2"],"critical":"A1","mechanisms":{"A1":[kind],"A2":[kind2]}}

    elif pattern=="SERIAL_COFAULT":
        kind2=KINDS[(KINDS.index(kind)+3)%len(KINDS)]
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"scope_state"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"scope_state"],writes=[p+"tool_state"],depends_on=["A1"],failed_kind=kind2),
            _row(3,domain,reads=[p+"tool_state"],writes=[p+"symptom"],depends_on=["A2"],failed_kind="INVARIANT",derived_failure=True),
            _row(4,domain,reads=[p+"symptom"],writes=[p+"terminal"],depends_on=["A3"]),
        ]
        oracle={"status":"INTERACTION","roots":["A1","A2"],"critical":"A1","mechanisms":{"A1":[kind],"A2":[kind2]}}

    else:
        kind2=KINDS[(KINDS.index(kind)+1)%len(KINDS)]
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"left"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"seed"],writes=[p+"right"],depends_on=["A0"],failed_kind=kind2),
            _row(3,domain,reads=[p+"left",p+"right"],writes=[p+"merged"],depends_on=["A1","A2"],composition="ALTERNATIVE"),
            _row(4,domain,reads=[p+"merged"],writes=[p+"terminal"],depends_on=["A3"],failed_kind="INVARIANT",derived_failure=True),
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
            "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
        "_oracle":oracle,
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:copy.deepcopy(v) for k,v in case.items() if k!="_oracle"}


def _repair_set(candidate:Mapping[str,Any])->set[tuple[str,str]]:
    out:set[tuple[str,str]]=set()
    repairs=candidate.get("repair_targets")
    if not isinstance(repairs,list):
        return out
    for raw in repairs:
        if not isinstance(raw,str):
            continue
        parts=raw.split(":")
        if len(parts)==3 and parts[0]=="restore" and parts[1] and parts[2]:
            out.add((parts[1],parts[2]))
    return out


def execute_intervention(public_case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    """Apply proposed repairs and recompute derived failures from visible dependency semantics."""
    task=public_case.get("task")
    if not isinstance(task,Mapping):
        return {"terminal_rescued":False,"reason":"TASK_INVALID"}
    rows=task.get("trajectory")
    failed_resources=task.get("terminal_failed_resources")
    if not isinstance(rows,list) or not isinstance(failed_resources,list):
        return {"terminal_rescued":False,"reason":"TRAJECTORY_INVALID"}

    by_id={}
    deps={}
    last_writer={}
    for row in rows:
        if not isinstance(row,Mapping):
            return {"terminal_rescued":False,"reason":"ROW_INVALID"}
        aid=row.get("action_id")
        if not isinstance(aid,str):
            return {"terminal_rescued":False,"reason":"ACTION_ID_INVALID"}
        by_id[aid]=row
        deps[aid]=set(str(x) for x in (row.get("depends_on") or []))
        for resource in row.get("reads") or []:
            if resource in last_writer:
                deps[aid].add(last_writer[resource])
        for resource in row.get("writes") or []:
            last_writer[resource]=aid

    terminal_actions={last_writer[r] for r in failed_resources if r in last_writer}
    relevant=set()
    stack=list(terminal_actions)
    while stack:
        aid=stack.pop()
        if aid in relevant:
            continue
        relevant.add(aid)
        stack.extend(deps.get(aid,set()))

    ancestors={}
    def anc(aid:str)->set[str]:
        if aid in ancestors:
            return ancestors[aid]
        out=set()
        todo=list(deps.get(aid,set()))
        while todo:
            x=todo.pop()
            if x in out:
                continue
            out.add(x)
            todo.extend(deps.get(x,set()))
        ancestors[aid]=out
        return out

    repairs=_repair_set(candidate)
    direct_unrepaired:set[tuple[str,str]]=set()
    direct_repaired:set[tuple[str,str]]=set()
    derived_failed:list[tuple[str,str]]=[]

    for aid,row in by_id.items():
        for check in row.get("checks") or []:
            if not isinstance(check,Mapping) or check.get("pass") is not False:
                continue
            kind=check.get("kind")
            if not isinstance(kind,str):
                continue
            key=(aid,kind)
            semantics=check.get("failure_semantics","DIRECT_CONTRACT")
            if semantics=="DERIVED_UPSTREAM":
                derived_failed.append(key)
            elif key in repairs:
                direct_repaired.add(key)
            else:
                direct_unrepaired.add(key)

    active_derived=[]
    for aid,kind in derived_failed:
        upstream=anc(aid)
        if any(root_aid in upstream for root_aid,_ in direct_unrepaired):
            active_derived.append((aid,kind))

    active_direct=[x for x in direct_unrepaired if x[0] in relevant]
    active_derived=[x for x in active_derived if x[0] in relevant]
    rescued=bool(terminal_actions) and not active_direct and not active_derived and bool(direct_repaired)

    return {
        "terminal_rescued":rescued,
        "repaired_direct_failures":[f"{a}:{k}" for a,k in sorted(direct_repaired)],
        "active_direct_failures":[f"{a}:{k}" for a,k in sorted(active_direct)],
        "active_derived_failures":[f"{a}:{k}" for a,k in sorted(active_derived)],
        "reason":"TERMINAL_CAUSAL_SLICE_CLEAR" if rescued else "TERMINAL_CAUSAL_SLICE_STILL_FAILED",
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
    status=candidate.get("status")
    if status not in _ALLOWED_KEYS:
        return {"pass":False,"reason":"STATUS_WRONG_OR_FAIL_CLOSED"}
    if set(candidate.keys()) != _ALLOWED_KEYS[status]:
        return {"pass":False,"reason":"OUTPUT_SCHEMA_NOT_EXACT"}
    o=case["_oracle"]
    got_roots=candidate.get("cause_action_ids")
    if not isinstance(got_roots,list):
        got_roots=[]
    roots=sorted(str(x) for x in got_roots)
    expected=sorted(o["roots"])
    if status!=o["status"] or roots!=expected:
        return {"pass":False,"reason":"STATUS_OR_ROOT_SET_WRONG","expected_status":o["status"],"expected_roots":expected}
    if candidate.get("critical_action_id")!=o["critical"]:
        return {"pass":False,"reason":"CRITICAL_ACTION_WRONG"}
    if o["status"]=="IDENTIFIED":
        if candidate.get("cause_action_id")!=o["critical"]:
            return {"pass":False,"reason":"UNIQUE_CAUSE_WRONG"}
        if candidate.get("mechanism_classes")!=o["mechanisms"][o["critical"]]:
            return {"pass":False,"reason":"MECHANISM_CLASS_WRONG"}
    elif o["status"]=="INTERACTION":
        if candidate.get("mechanism_by_action")!=o["mechanisms"]:
            return {"pass":False,"reason":"INTERACTION_MECHANISMS_WRONG"}
    elif o["status"]=="AMBIGUOUS":
        if candidate.get("cause_action_id") is not None:
            return {"pass":False,"reason":"NONIDENTIFIABILITY_OVERCLAIM"}
        if not candidate.get("information_request"):
            return {"pass":False,"reason":"MISSING_INFORMATION_REQUEST"}

    repairs=candidate.get("repair_targets") or []
    if o["status"]!="AMBIGUOUS":
        expected_repairs=sorted(
            f"restore:{aid}:{kind}"
            for aid,kinds in o["mechanisms"].items()
            for kind in kinds
        )
        if sorted(str(x) for x in repairs)!=expected_repairs:
            return {"pass":False,"reason":"FALSIFIABLE_REPAIR_TARGET_WRONG","expected_repair_targets":expected_repairs}
        intervention=execute_intervention(public_task(case),candidate)
        if intervention.get("terminal_rescued") is not True:
            return {"pass":False,"reason":"INTERVENTION_DID_NOT_RESCUE_TERMINAL","intervention":intervention}
        return {"pass":True,"reason":"PASS","intervention_rescue_verified":True,"intervention":intervention}

    if repairs:
        return {"pass":False,"reason":"AMBIGUOUS_CASE_MUST_NOT_FORCE_REPAIR"}
    intervention=execute_intervention(public_task(case),candidate)
    if intervention.get("terminal_rescued") is True:
        return {"pass":False,"reason":"AMBIGUOUS_CASE_FALSE_RESCUE"}
    return {"pass":True,"reason":"PASS","intervention_rescue_verified":False,"intervention":intervention}


def suite_cases()->list[dict[str,Any]]:
    out=[]
    seed=2000
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in PATTERNS:
                out.append(generate_case(seed,pattern=pattern,domain=domain,kind=kind))
                seed+=1
    return out


def anti_shortcut_mutations()->list[dict[str,str]]:
    return [
        {"id":"SCOPE_FIRST_CLASS","property":"SCOPE_MUST_BE_A_DISTINCT_MECHANISM_NOT_AN_AUTHORITY_ALIAS"},
        {"id":"DELAY_SYMPTOM","property":"ROOT_CAUSE_MUST_SURVIVE_LONG_CAUSAL_DELAY"},
        {"id":"CONJUNCTIVE_ROOT_PAIR","property":"JOINT_CAUSE_SET_MUST_NOT_COLLAPSE_TO_ONE_MEMBER"},
        {"id":"ALTERNATIVE_ROOTS","property":"OBSERVATIONALLY_NONIDENTIFIABLE_ROOTS_MUST_REMAIN_AMBIGUOUS"},
        {"id":"REPAIR_NOT_RESCUE","property":"NAMING_A_REPAIR_IS_INSUFFICIENT_UNLESS_APPLYING_IT_CLEARS_THE_TERMINAL_CAUSAL_SLICE"},
        {"id":"DERIVED_SYMPTOM_RECOMPUTE","property":"DERIVED_FAILURE_MUST_CLEAR_ONLY_AFTER_ITS_UPSTREAM_DIRECT_FAILURES_ARE_REPAIRED"},
        {"id":"SERIAL_DIRECT_COFAULT","property":"A_DOWNSTREAM_DIRECT_CONTRACT_DEFECT_MUST_NOT_BE_ERASED_BY_A_FAILED_ANCESTOR"},
        {"id":"FAILURE_SEMANTICS_LOAD_BEARING","property":"CHANGING_DIRECT_CONTRACT_TO_DERIVED_UPSTREAM_MUST_CHANGE_THE_CAUSAL_REPAIR_SET"},
    ]
