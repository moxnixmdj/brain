"""Zero-terminal-evidence V5 proof population for typed cross-domain trajectory diagnosis.

V5 composes V4's heterogeneous typed causal envelope with a hidden
counterfactual intervention model. Candidate-visible data never contains the
intervention worlds. The scorer tests nominated repairs by applying them to
hidden fault worlds rather than crediting repair-target names alone."""
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

    # Hidden intervention worlds are evaluator-only. Each world contains
    # the root-fault repair tokens that must all be applied to rescue that world.
    # IDENTIFIED/INTERACTION have one actual world; AMBIGUOUS has one
    # observationally equivalent world per surviving root.
    repair_by_root={
        aid: sorted(
            f"restore:{aid}:{kind}"
            for kind in oracle["mechanisms"][aid]
        )
        for aid in oracle["roots"]
    }
    if oracle["status"]=="AMBIGUOUS":
        oracle["intervention_worlds"]=[
            list(repair_by_root[aid]) for aid in oracle["roots"]
        ]
    else:
        oracle["intervention_worlds"]=[
            sorted({token for aid in oracle["roots"] for token in repair_by_root[aid]})
        ]

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


def _intervention_outcome(case:Mapping[str,Any], repair_targets:list[str])->dict[str,Any]:
    """Apply repair tokens to hidden fault worlds and report terminal rescue."""
    oracle=case.get("_oracle")
    if not isinstance(oracle,Mapping):
        raise ValueError("ORACLE_MISSING")
    worlds=oracle.get("intervention_worlds")
    if not isinstance(worlds,list) or not worlds:
        raise ValueError("INTERVENTION_WORLDS_MISSING")
    repairs={x for x in repair_targets if isinstance(x,str)}
    world_rescued=[]
    for world in worlds:
        if not isinstance(world,list) or not world or any(not isinstance(x,str) for x in world):
            raise ValueError("INTERVENTION_WORLD_INVALID")
        world_rescued.append(set(world).issubset(repairs))
    return {
        "world_rescued":world_rescued,
        "any_world_rescued":any(world_rescued),
        "all_worlds_rescued":all(world_rescued),
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
        candidate_rows=candidate.get("candidates")
        if not isinstance(candidate_rows,list) or len(candidate_rows)!=len(o["roots"]):
            return {"pass":False,"reason":"AMBIGUOUS_INTERVENTION_CANDIDATES_MISSING"}
        union_repairs=[]
        for row in candidate_rows:
            if not isinstance(row,Mapping):
                return {"pass":False,"reason":"AMBIGUOUS_INTERVENTION_CANDIDATE_INVALID"}
            row_repairs=row.get("repair_targets") or []
            outcome=_intervention_outcome(case,[str(x) for x in row_repairs])
            if not outcome["any_world_rescued"] or outcome["all_worlds_rescued"]:
                return {"pass":False,"reason":"AMBIGUOUS_REPAIR_DOES_NOT_PRESERVE_WORLD_UNCERTAINTY"}
            union_repairs.extend(str(x) for x in row_repairs)
        if not _intervention_outcome(case,union_repairs)["all_worlds_rescued"]:
            return {"pass":False,"reason":"AMBIGUOUS_REPAIR_UNION_DOES_NOT_RESCUE_ALL_WORLDS"}
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
        intervention=_intervention_outcome(case,[str(x) for x in repairs])
        if not intervention["all_worlds_rescued"]:
            return {"pass":False,"reason":"NOMINATED_REPAIR_DOES_NOT_RESCUE_TERMINAL_OUTCOME"}
        if o["status"]=="INTERACTION":
            for token in expected_repairs:
                if _intervention_outcome(case,[token])["all_worlds_rescued"]:
                    return {"pass":False,"reason":"INTERACTION_SINGLETON_FALSE_RESCUE"}
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
        {"id":"SCOPE_TO_AUTHORITY_SWAP","property":"EXPLICIT_SCOPE_FAILURE_MUST_REMAIN_DISTINCT_FROM_AUTHORITY"},
        {"id":"INTERACTION_SINGLETON_REPAIR","property":"CONJUNCTIVE_ROOT_RESCUE_REQUIRES_THE_FULL_ROOT_REPAIR_SET"},
        {"id":"HIDE_INTERVENTION_WORLDS","property":"CANDIDATE_MUST_NOT_RECEIVE_HIDDEN_POST_INTERVENTION_OUTCOMES"},
    ]
