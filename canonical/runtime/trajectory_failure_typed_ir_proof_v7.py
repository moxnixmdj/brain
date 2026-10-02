"""P1 V7 proof envelope: V6 regression plus nested competing-cause ambiguity."""
from __future__ import annotations
import copy
from typing import Any, Mapping
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as v6

SCHEMA="PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V7"
DOMAINS=v6.DOMAINS
KINDS=v6.KINDS
PATTERNS=v6.PATTERNS

def _check(kind:str,aid:str,passed:bool,semantics:str)->dict[str,Any]:
    return {
        "kind":kind,"id":f"{aid}:{kind}","pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        "failure_semantics":semantics,
    }

def _row(i:int,domain:str,*,reads:list[str],writes:list[str],depends_on:list[str],
         failed_kind:str|None=None,semantics:str="DIRECT_CONTRACT")->dict[str,Any]:
    aid=f"A{i}"
    checks=[_check("INVARIANT",aid,True,"DIRECT_CONTRACT")]
    if failed_kind is not None:
        checks.append(_check(failed_kind,aid,False,semantics))
    return {
        "step":i,"action_id":aid,"domain":domain,"reads":reads,"writes":writes,
        "depends_on":depends_on,"dependency_composition":"SEQUENTIAL","checks":checks,
    }

def generate_nested_case(seed:int,*,domain:str,kind:str)->dict[str,Any]:
    kind2=KINDS[(KINDS.index(kind)+1)%len(KINDS)]
    p=f"{domain.lower()}:"
    rows=[
      _row(0,domain,reads=[],writes=[p+"seed"],depends_on=[]),
      _row(1,domain,reads=[p+"seed"],writes=[p+"mid1"],depends_on=["A0"],
           failed_kind=kind,semantics="DIRECT_CONTRACT"),
      _row(2,domain,reads=[p+"mid1"],writes=[p+"mid2"],depends_on=["A1"],
           failed_kind=kind2,semantics="DIRECT_CONTRACT"),
      _row(3,domain,reads=[p+"mid2"],writes=[p+"terminal"],depends_on=["A2"]),
    ]
    return {
      "schema":SCHEMA,"behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
      "seed":seed,"pattern":"NESTED_COMPETING_DIRECT","task":{
        "domain":domain,"trajectory":rows,"terminal_failed_resources":[p+"terminal"],
        "goal":"ABSTAIN_WHEN_NESTED_DIRECT_FAILURES_HAVE_NO_VISIBLE_CAUSAL_DISCRIMINATOR",
      },
      "_oracle":{
        "status":"AMBIGUOUS","roots":["A1","A2"],"critical":None,
        "mechanisms":{"A1":[kind],"A2":[kind2]},
      },
      "_worlds":[
        {"world_id":"UPSTREAM_CAUSAL","latent_fault":["A1",kind]},
        {"world_id":"DOWNSTREAM_CAUSAL","latent_fault":["A2",kind2]},
      ],
    }

def nested_cases()->list[dict[str,Any]]:
    out=[]; seed=30000
    for domain in DOMAINS:
        for kind in KINDS:
            out.append(generate_nested_case(seed,domain=domain,kind=kind)); seed+=1
    return out

def suite_cases()->list[dict[str,Any]]:
    return [copy.deepcopy(x) for x in v6.suite_cases()]+nested_cases()

def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:copy.deepcopy(v) for k,v in case.items() if not str(k).startswith("_")}

def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    # V6's exact scorer already enforces the output schema, hidden oracle root set,
    # rescue for identifiable/interaction cases, and no rescue for ambiguity.
    return v6.score_case(case,candidate)

def nested_world_rescue_vector(case:Mapping[str,Any],repairs:list[str])->tuple[bool,...]:
    parsed=set()
    for raw in repairs:
        if not isinstance(raw,str):
            continue
        parts=raw.split(":")
        if len(parts)==3 and parts[0]=="restore":
            parsed.add((parts[1],parts[2]))
    return tuple(tuple(w["latent_fault"]) in parsed for w in case["_worlds"])
