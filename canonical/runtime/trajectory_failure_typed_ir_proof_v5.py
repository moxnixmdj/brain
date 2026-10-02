"""Zero-terminal-evidence V5 proof population for typed cross-domain trajectory diagnosis."""
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


def generate_case(seed:int, *, pattern:str|None=None, domain:str|None=None, kind:str|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_INVALID")
    r=random.Random(seed)
    domain=domain or DOMAINS[seed%len(DOMAINS)]
    kind=kind or KINDS[(seed//len(DOMAINS))%len(KINDS)]
    pattern=pattern or ("SINGLE","DELAYED","INTERACTION","AMBIGUOUS")[seed%4]
    if pattern not in {"SINGLE","DELAYED","INTERACTION","AMBIGUOUS"}:
        raise ValueError("PATTERN_INVALID")
    if domain not in DOMAINS or kind not in KINDS:
        raise ValueError("DOMAIN_OR_KIND_INVALID")

    # Domain labels and resource names vary, but the candidate sees only generic
    # normalized IR semantics.
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

    else:  # AMBIGUOUS
        kind2=KINDS[(KINDS.index(kind)+1)%len(KINDS)]
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"left"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"seed"],writes=[p+"right"],depends_on=["A0"],failed_kind=kind2),
            # ALTERNATIVE encodes that the observed trace alone does not identify
            # which independent violating branch was causal.
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
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}



def intervention_rescue(case:Mapping[str,Any], repair_targets:list[str])->dict[str,Any]:
    """Apply candidate repairs to hidden root defects, then propagate failure to terminal resources.

    The candidate never receives the hidden oracle. This evaluator uses it only after
    the candidate has committed to repair targets. A repair is causal only if removing
    the corresponding hidden root defect makes the terminal failed resource unreachable
    from every remaining hidden defect through the declared dependency/dataflow graph.
    """
    if not isinstance(repair_targets,list) or any(not isinstance(x,str) for x in repair_targets):
        return {"applicable":True,"rescued":False,"reason":"REPAIR_TARGETS_INVALID"}

    task=case.get("task")
    oracle=case.get("_oracle")
    if not isinstance(task,Mapping) or not isinstance(oracle,Mapping):
        return {"applicable":False,"rescued":False,"reason":"CASE_OR_ORACLE_INVALID"}
    if oracle.get("status")=="AMBIGUOUS":
        return {"applicable":False,"rescued":False,"reason":"NONIDENTIFIABLE_CASE_REQUIRES_DISCRIMINATOR"}

    rows=task.get("trajectory")
    terminal_failed=task.get("terminal_failed_resources")
    if not isinstance(rows,list) or not isinstance(terminal_failed,list):
        return {"applicable":True,"rescued":False,"reason":"TASK_INVALID"}

    parsed:set[tuple[str,str]]=set()
    for target in repair_targets:
        parts=target.split(":",2)
        if len(parts)==3 and parts[0]=="restore" and parts[1] and parts[2]:
            parsed.add((parts[1],parts[2]))

    root_defects={
        (str(aid),str(kind))
        for aid,kinds in (oracle.get("mechanisms") or {}).items()
        for kind in kinds
    }
    unrepaired=root_defects-parsed

    by_id:dict[str,Mapping[str,Any]]={}
    deps:dict[str,set[str]]={}
    reads:dict[str,set[str]]={}
    writes:dict[str,set[str]]={}
    last_writer:dict[str,str]={}
    for row in rows:
        if not isinstance(row,Mapping):
            return {"applicable":True,"rescued":False,"reason":"ROW_INVALID"}
        aid=row.get("action_id")
        if not isinstance(aid,str) or aid in by_id:
            return {"applicable":True,"rescued":False,"reason":"ACTION_ID_INVALID"}
        raw_deps=row.get("depends_on")
        raw_reads=row.get("reads")
        raw_writes=row.get("writes")
        if not isinstance(raw_deps,list) or not isinstance(raw_reads,list) or not isinstance(raw_writes,list):
            return {"applicable":True,"rescued":False,"reason":"GRAPH_FIELDS_INVALID"}
        by_id[aid]=row
        deps[aid]=set(str(x) for x in raw_deps)
        reads[aid]=set(str(x) for x in raw_reads)
        writes[aid]=set(str(x) for x in raw_writes)
        for resource in reads[aid]:
            prior=last_writer.get(resource)
            if prior is not None:
                deps[aid].add(prior)
        for resource in writes[aid]:
            last_writer[resource]=aid

    poisoned:set[str]={aid for aid,_kind in unrepaired}
    changed=True
    while changed:
        changed=False
        for aid in by_id:
            if aid in poisoned:
                continue
            if deps[aid] & poisoned:
                poisoned.add(aid)
                changed=True

    terminal_actions={last_writer[r] for r in terminal_failed if r in last_writer}
    terminal_still_failed=bool(terminal_actions & poisoned)
    return {
        "applicable":True,
        "rescued":not terminal_still_failed,
        "reason":"TERMINAL_FAILURE_CLEARED" if not terminal_still_failed else "UNREPAIRED_CAUSAL_PATH_REACHES_TERMINAL",
        "hidden_root_defect_count":len(root_defects),
        "repaired_hidden_root_defect_count":len(root_defects & parsed),
        "unrepaired_hidden_root_defect_count":len(unrepaired),
        "terminal_action_count":len(terminal_actions),
        "poisoned_action_count":len(poisoned),
    }


def score_case(case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping):
        return {"pass":False,"reason":"CANDIDATE_NOT_OBJECT"}
    o=case["_oracle"]
    status=candidate.get("status")
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
        mb=candidate.get("mechanism_by_action")
        if mb!=o["mechanisms"]:
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
            return {
                "pass":False,
                "reason":"FALSIFIABLE_REPAIR_TARGET_WRONG",
                "expected_repair_targets":expected_repairs,
            }
        rescue=intervention_rescue(case,list(repairs))
        if rescue.get("rescued") is not True:
            return {
                "pass":False,
                "reason":"POST_INTERVENTION_TERMINAL_RESCUE_FAILED",
                "intervention":rescue,
            }
    # Downstream symptom actions are deliberately failed too; selecting them as
    # roots would already fail the exact root-set comparison above.
    return {"pass":True,"reason":"PASS"}


def suite_cases()->list[dict[str,Any]]:
    out=[]
    seed=1000
    for domain in DOMAINS:
        for kind in KINDS:
            for pattern in ("SINGLE","DELAYED","INTERACTION","AMBIGUOUS"):
                out.append(generate_case(seed,pattern=pattern,domain=domain,kind=kind))
                seed+=1
    return out


def anti_shortcut_mutations()->list[dict[str,str]]:
    return [
        {"id":"MOVE_SYMPTOM_EARLIER","property":"DOWNSTREAM_OR_EARLY_VISIBLE_SYMPTOM_MUST_NOT_REPLACE_ROOT_CAUSE"},
        {"id":"RENAME_ACTION_IDS","property":"LEXICAL_ACTION_ID_CANNOT_DEFINE_CAUSALITY"},
        {"id":"PERMUTE_DOMAIN_LABELS","property":"DOMAIN_NAME_CANNOT_DEFINE_MECHANISM"},
        {"id":"DELAY_SYMPTOM","property":"ROOT_CAUSE_MUST_SURVIVE_LONG_CAUSAL_DELAY"},
        {"id":"CONJUNCTIVE_ROOT_PAIR","property":"JOINT_CAUSE_SET_MUST_NOT_COLLAPSE_TO_ONE_MEMBER"},
        {"id":"ALTERNATIVE_ROOTS","property":"OBSERVATIONALLY_NONIDENTIFIABLE_ROOTS_MUST_REMAIN_AMBIGUOUS"},
        {"id":"AUTHORITY_TO_SCHEMA_SWAP","property":"MECHANISM_CLASS_MUST_FOLLOW_FAILED_CONTRACT_CHECK_NOT_POSITION"},
        {"id":"AUTHORITY_TO_SCOPE_SWAP","property":"SCOPE_MUST_BE_A_FIRST_CLASS_MECHANISM_NOT_AN_AUTHORITY_ALIAS"},
        {"id":"REMOVE_ONE_INTERACTION_REPAIR","property":"NOMINATED_REPAIR_SET_MUST_MACHINE_RESCUE_TERMINAL_FAILURE"},
    ]
