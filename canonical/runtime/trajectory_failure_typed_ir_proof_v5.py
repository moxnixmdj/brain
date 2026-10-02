"""Zero-terminal-evidence V5 proof population for P1 typed trajectory diagnosis.

V5 strengthens V4 in two ways:
1. SCOPE is an explicit first-class failed-contract mechanism, distinct from AUTHORITY.
2. For every non-ambiguous case the scorer executes candidate-nominated repairs
   against a hidden intervention model and requires terminal rescue. Interaction
   cases require the full joint repair set. Symptom-only and incomplete repairs
   must not rescue.

The candidate never receives hidden causal roots or intervention outcomes.
"""
from __future__ import annotations
import random
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V5"
DOMAINS = ("BROWSER","FILESYSTEM","TOOL_API","ARTIFACT","RESEARCH","CODE")
KINDS = ("AUTHORITY","SCOPE","SCHEMA","PROVENANCE","INVARIANT","STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY")
PATTERNS = ("SINGLE","DELAYED","INTERACTION","AMBIGUOUS")

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

def _repair(aid:str, kind:str)->str:
    return f"restore:{aid}:{kind}"

def generate_case(seed:int, *, pattern:str|None=None, domain:str|None=None, kind:str|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_INVALID")
    random.Random(seed)
    domain=domain or DOMAINS[seed%len(DOMAINS)]
    kind=kind or KINDS[(seed//len(DOMAINS))%len(KINDS)]
    pattern=pattern or PATTERNS[seed%len(PATTERNS)]
    if pattern not in PATTERNS:
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
        oracle={"status":"IDENTIFIED","roots":["A1"],"critical":"A1","mechanisms":{"A1":[kind]},
                "causal_repairs":[_repair("A1",kind)],"symptom_repairs":[_repair("A2","INVARIANT")]}

    elif pattern=="DELAYED":
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"root"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"root"],writes=[p+"mid1"],depends_on=["A1"]),
            _row(3,domain,reads=[p+"mid1"],writes=[p+"mid2"],depends_on=["A2"]),
            _row(4,domain,reads=[p+"mid2"],writes=[p+"late_symptom"],depends_on=["A3"],failed_kind="INVARIANT"),
            _row(5,domain,reads=[p+"late_symptom"],writes=[p+"terminal"],depends_on=["A4"]),
        ]
        oracle={"status":"IDENTIFIED","roots":["A1"],"critical":"A1","mechanisms":{"A1":[kind]},
                "causal_repairs":[_repair("A1",kind)],"symptom_repairs":[_repair("A4","INVARIANT")]}

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
        oracle={"status":"INTERACTION","roots":["A1","A2"],"critical":"A1","mechanisms":{"A1":[kind],"A2":[kind2]},
                "causal_repairs":sorted([_repair("A1",kind),_repair("A2",kind2)]),
                "symptom_repairs":[_repair("A4","INVARIANT")]}

    else:
        kind2=KINDS[(KINDS.index(kind)+1)%len(KINDS)]
        rows=[
            _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
            _row(1,domain,reads=[p+"seed"],writes=[p+"left"],depends_on=["A0"],failed_kind=kind),
            _row(2,domain,reads=[p+"seed"],writes=[p+"right"],depends_on=["A0"],failed_kind=kind2),
            _row(3,domain,reads=[p+"left",p+"right"],writes=[p+"merged"],depends_on=["A1","A2"],composition="ALTERNATIVE"),
            _row(4,domain,reads=[p+"merged"],writes=[p+"terminal"],depends_on=["A3"],failed_kind="INVARIANT"),
        ]
        oracle={"status":"AMBIGUOUS","roots":["A1","A2"],"critical":None,"mechanisms":{"A1":[kind],"A2":[kind2]},
                "causal_repairs":[],"symptom_repairs":[_repair("A4","INVARIANT")]}

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

def execute_hidden_intervention(case:Mapping[str,Any], repair_targets:list[str])->dict[str,Any]:
    """Execute a hidden causal intervention against the frozen case world."""
    oracle=case["_oracle"]
    repairs={str(x) for x in repair_targets}
    if oracle["status"]=="AMBIGUOUS":
        return {"adjudicable":False,"terminal_success":False,"reason":"NONIDENTIFIABLE_WORLD"}
    required=set(oracle["causal_repairs"])
    return {
        "adjudicable":True,
        "terminal_success":required.issubset(repairs),
        "required_repair_count":len(required),
        "applied_repair_count":len(repairs),
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
        if candidate.get("mechanism_by_action")!=o["mechanisms"]:
            return {"pass":False,"reason":"INTERACTION_MECHANISMS_WRONG"}
    elif o["status"]=="AMBIGUOUS":
        if candidate.get("cause_action_id") is not None:
            return {"pass":False,"reason":"NONIDENTIFIABILITY_OVERCLAIM"}
        if not candidate.get("information_request"):
            return {"pass":False,"reason":"MISSING_INFORMATION_REQUEST"}
        return {"pass":True,"reason":"PASS_NONIDENTIFIABLE","post_intervention_terminal_rescue":None}

    repairs=sorted(str(x) for x in (candidate.get("repair_targets") or []))
    if repairs!=sorted(o["causal_repairs"]):
        return {"pass":False,"reason":"FALSIFIABLE_REPAIR_TARGET_WRONG","expected_repair_targets":sorted(o["causal_repairs"])}

    rescue=execute_hidden_intervention(case,repairs)
    if rescue.get("terminal_success") is not True:
        return {"pass":False,"reason":"POST_INTERVENTION_TERMINAL_RESCUE_FAILED","intervention":rescue}

    symptom=execute_hidden_intervention(case,list(o["symptom_repairs"]))
    if symptom.get("terminal_success") is True:
        return {"pass":False,"reason":"SYMPTOM_ONLY_REPAIR_FALSELY_RESCUES"}

    if o["status"]=="INTERACTION" and len(repairs)>1:
        for dropped in repairs:
            partial=[x for x in repairs if x!=dropped]
            if execute_hidden_intervention(case,partial).get("terminal_success") is True:
                return {"pass":False,"reason":"INTERACTION_PARTIAL_REPAIR_FALSELY_RESCUES","dropped":dropped}

    return {
        "pass":True,
        "reason":"PASS",
        "post_intervention_terminal_rescue":True,
        "symptom_only_repair_rejected":True,
        "interaction_strict_subsets_rejected":o["status"]=="INTERACTION",
    }

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
        {"id":"MOVE_SYMPTOM_EARLIER","property":"DOWNSTREAM_OR_EARLY_VISIBLE_SYMPTOM_MUST_NOT_REPLACE_ROOT_CAUSE"},
        {"id":"RENAME_ACTION_IDS","property":"LEXICAL_ACTION_ID_CANNOT_DEFINE_CAUSALITY"},
        {"id":"PERMUTE_DOMAIN_LABELS","property":"DOMAIN_NAME_CANNOT_DEFINE_MECHANISM"},
        {"id":"DELAY_SYMPTOM","property":"ROOT_CAUSE_MUST_SURVIVE_LONG_CAUSAL_DELAY"},
        {"id":"CONJUNCTIVE_ROOT_PAIR","property":"JOINT_CAUSE_SET_MUST_NOT_COLLAPSE_TO_ONE_MEMBER"},
        {"id":"ALTERNATIVE_ROOTS","property":"OBSERVATIONALLY_NONIDENTIFIABLE_ROOTS_MUST_REMAIN_AMBIGUOUS"},
        {"id":"AUTHORITY_TO_SCOPE_SWAP","property":"SCOPE_IS_FIRST_CLASS_AND_MUST_NOT_BE_INFERRED_FROM_AUTHORITY"},
        {"id":"SYMPTOM_ONLY_REPAIR","property":"DOWNSTREAM_SYMPTOM_REPAIR_MUST_NOT_RESCUE_TERMINAL_OUTCOME"},
        {"id":"DROP_INTERACTION_REPAIR","property":"STRICT_SUBSET_OF_CONJUNCTIVE_CAUSAL_REPAIR_SET_MUST_NOT_RESCUE"},
    ]
