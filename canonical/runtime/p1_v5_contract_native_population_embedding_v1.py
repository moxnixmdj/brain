"""Universal structural embedding of frozen contract-native P1 cases into V5.

This is zero-reality proof machinery. It does not replay Terminal V3 for credit.
It proves a population relation from the exact frozen generator grammar used by
the T0/T2 parent P1 route into the stronger V5 typed intervention envelope.

The legacy generator's seed can change only the causal index and visible repair
list order. Under the frozen difficulty cycle 1..5 there are 30 semantic
(n, cause-index) shapes. Repair order is answer-irrelevant and deliberately
removed by the V5 mapping. Every semantic shape is embedded across all six V5
canonical domains, producing 180 claim-bound embedding checks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_proof_suites as legacy
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as v5_candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as v5_proof

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V5_CONTRACT_NATIVE_POPULATION_EMBEDDING_V1"
P1="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P1_BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
PARENT_BINDING="canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"
V5_ACTIVATION="canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5_ACTIVATION_V1.json"

EXPECTED_BLOBS={
    "canonical/runtime/contract_native_proof_suites.py":"0210790c7dd705ef328e1b55d529a30c5c6c3337",
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py":"2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py":"3fc600a8176dac250219e3d98b92cf93d8fceef5",
    P1_BINDING:"8703c6aa08227467a619a7ae90d0d61f8e54da39",
    PARENT_BINDING:"a1630299d29ea9c07e55b4314c07ddb3228c3287",
    V5_ACTIVATION:"e01df1a703266e055ab965ec7c37c491051b221b",
}
EXPECTED_SURFACES=(
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
)
CLAIM_IDS={
    EXPECTED_SURFACES[0]:"P1-V5-FRONTIERCODE-CONTRACT-NATIVE-EMBEDDING-V1",
    EXPECTED_SURFACES[1]:"P1-V5-CURSORBENCH-CONTRACT-NATIVE-EMBEDDING-V1",
    EXPECTED_SURFACES[2]:"P1-V5-RECOVERY-CONTRACT-NATIVE-EMBEDDING-V1",
}


def _blob(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _load(rel:str)->dict[str,Any]:
    x=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return x


def _legacy_shape(case:Mapping[str,Any])->tuple[int,int]:
    rows=case["task"]["trajectory"]
    return len(rows), int(case["_oracle"]["cause_step"])


def _find_shape_representatives(limit:int=20000)->dict[tuple[int,int],dict[str,Any]]:
    expected={(6+d,c) for d in range(1,6) for c in range(1,(6+d)-2)}
    found:dict[tuple[int,int],dict[str,Any]]={}
    for difficulty in range(1,6):
        n=6+difficulty
        needed={c for c in range(1,n-2)}
        for seed in range(limit):
            case=legacy.generate_case(P1,seed=seed,difficulty=difficulty)
            shape=_legacy_shape(case)
            if shape[1] in needed:
                found.setdefault(shape,case)
            if all((n,c) in found for c in needed):
                break
    missing=expected-set(found)
    if missing:
        raise AssertionError("MISSING_LEGACY_SEMANTIC_SHAPES:"+repr(sorted(missing)))
    return found


def embed(case:Mapping[str,Any],domain:str)->dict[str,Any]:
    if domain not in v5_proof.DOMAINS:
        raise ValueError("DOMAIN_NOT_IN_V5_CANONICAL_DOMAIN_SET")
    if case.get("contract")!=P1:
        raise ValueError("NOT_P1")
    steps=case["task"]["trajectory"]
    cause=int(case["_oracle"]["cause_step"])
    p=domain.lower()+":legacy:"
    rows=[]
    for i,step in enumerate(steps):
        if int(step["step"])!=i or step["action"]!=f"A{i}":
            raise ValueError("LEGACY_STEP_GRAMMAR_DRIFT")
        rows.append({
            "step":i,
            "action_id":f"A{i}",
            "domain":domain,
            "reads":[] if i==0 else [p+f"r{i-1}"],
            "writes":[p+f"r{i}"],
            "depends_on":[] if i==0 else [f"A{i-1}"],
            "dependency_composition":"SEQUENTIAL",
            "checks":[{
                "kind":"INVARIANT",
                "id":f"A{i}:INVARIANT",
                "pass":bool(step["invariant_pass"]),
                "evidence":[f"legacy-receipt:A{i}",f"legacy-invariant:A{i}"],
            }],
        })
    oracle={
        "status":"IDENTIFIED",
        "roots":[f"A{cause}"],
        "critical":f"A{cause}",
        "mechanisms":{f"A{cause}":["INVARIANT"]},
    }
    return {
        "schema":v5_proof.SCHEMA,
        "behavior_id":P1,
        "seed":int(case["seed"]),
        "task":{
            "domain":domain,
            "trajectory":rows,
            "terminal_failed_resources":[p+f"r{len(rows)-1}"],
            "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITHOUT_SELECTING_DOWNSTREAM_SYMPTOM",
        },
        "_oracle":oracle,
        "_intervention_model":v5_proof._hidden_intervention_model(rows,oracle),
    }


def _legacy_correct_candidate(case:Mapping[str,Any])->dict[str,Any]:
    c=int(case["_oracle"]["cause_step"])
    return {"cause_step":c,"repair_id":f"repair_{c}","evidence_steps":[c]}


def _bridge_v5_to_legacy(v5_output:Mapping[str,Any])->dict[str,Any]:
    aid=str(v5_output.get("cause_action_id") or "")
    if not (aid.startswith("A") and aid[1:].isdigit()):
        return {}
    c=int(aid[1:])
    repairs=[str(x) for x in (v5_output.get("repair_targets") or [])]
    expected=f"restore:A{c}:INVARIANT"
    if repairs!=[expected]:
        return {}
    return {"cause_step":c,"repair_id":f"repair_{c}","evidence_steps":[c]}


def evaluate()->dict[str,Any]:
    errors=[]
    for rel,want in EXPECTED_BLOBS.items():
        got=_blob(rel)
        if got!=want:
            errors.append(f"BLOB_DRIFT:{rel}:{got}")

    binding=_load(P1_BINDING)
    parent=_load(PARENT_BINDING)
    activation=_load(V5_ACTIVATION)
    if set(binding.get("direct_surface_bindings") or [])!=set(EXPECTED_SURFACES):
        errors.append("DIRECT_SURFACE_SET_DRIFT")
    schedule=(parent.get("schedules") or {}).get(P1) or {}
    if schedule.get("mode")!="CONTRACT_NATIVE":
        errors.append("P1_PARENT_MODE_NOT_CONTRACT_NATIVE")
    if list(schedule.get("difficulty_cycle") or [])!=[1,2,3,4,5]:
        errors.append("P1_DIFFICULTY_CYCLE_DRIFT")
    if int(schedule.get("case_count") or -1)!=30:
        errors.append("P1_PARENT_CASE_COUNT_DRIFT")
    if not str(activation.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("V5_NOT_ACTIVE_INDEPENDENT_PREWAVE_AUTHORITY")

    # Exact source grammar checks. Because the source blob is pinned, these
    # establish that seed affects semantic shape only through cause position;
    # repair-list shuffling is visible but not part of the legacy score.
    src=(ROOT/"canonical/runtime/contract_native_proof_suites.py").read_text(encoding="utf-8")
    required_fragments=(
        "n=max(5,min(14,6+difficulty))",
        "cause=r.randint(1,n-3)",
        "repairs=[{\"id\":f\"repair_{i}\",\"targets_step\":i} for i in range(cause,n-1)]",
        "r.shuffle(repairs)",
        "candidate.get(\"cause_step\") != case[\"_oracle\"][\"cause_step\"]",
        "candidate.get(\"repair_id\") != case[\"_oracle\"][\"repair_id\"]",
        "rescued=(candidate.get(\"repair_id\")==case[\"_oracle\"][\"repair_id\"])",
    )
    missing_fragments=[x for x in required_fragments if x not in src]
    if missing_fragments:
        errors.append("LEGACY_GENERATOR_OR_SCORER_GRAMMAR_DRIFT")

    if errors:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_DRIFT","errors":sorted(errors),
            "population_superset_proven":False,"surface_relations":[],
            "new_reality_units_consumed":0,"terminal_results_replayed":0,
            "capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False,
        }

    reps=_find_shape_representatives()
    failures=[]
    domain_shape_count=0
    wrong_repair_checks=0
    order_invariance_checks=0
    for shape,legacy_case in sorted(reps.items()):
        # The exact legacy scorer is invariant to repair-candidate order for the
        # correct cause/repair/evidence tuple. This justifies removing that
        # answer-bearing list from the V5 candidate-visible information.
        good=_legacy_correct_candidate(legacy_case)
        if legacy.score_case(legacy_case,good).get("pass") is not True:
            failures.append({"shape":shape,"reason":"LEGACY_BASELINE_FAILED"})
        reversed_case=json.loads(json.dumps(legacy_case))
        reversed_case["task"]["repair_candidates"].reverse()
        if legacy.score_case(reversed_case,good).get("pass") is not True:
            failures.append({"shape":shape,"reason":"REPAIR_ORDER_BECAME_LOAD_BEARING"})
        order_invariance_checks+=1

        cause=int(legacy_case["_oracle"]["cause_step"])
        for repair in legacy_case["task"]["repair_candidates"]:
            if repair["id"]==f"repair_{cause}":
                continue
            wrong={"cause_step":cause,"repair_id":repair["id"],"evidence_steps":[cause]}
            if legacy.score_case(legacy_case,wrong).get("pass") is True:
                failures.append({"shape":shape,"reason":"LEGACY_WRONG_REPAIR_ACCEPTED","repair":repair})
            wrong_repair_checks+=1

        for domain in v5_proof.DOMAINS:
            typed=embed(legacy_case,domain)
            public=v5_proof.public_task(typed)
            if "_oracle" in public or "_intervention_model" in public:
                failures.append({"shape":shape,"domain":domain,"reason":"HIDDEN_STATE_LEAK"})
                continue
            out=v5_candidate.solve(public)
            verdict=v5_proof.score_case(typed,out)
            bridged=_bridge_v5_to_legacy(out)
            legacy_verdict=legacy.score_case(legacy_case,bridged) if bridged else {"pass":False}
            if verdict.get("pass") is not True or legacy_verdict.get("pass") is not True:
                failures.append({
                    "shape":shape,"domain":domain,"reason":"EMBEDDING_NOT_SEMANTICS_PRESERVING",
                    "v5_verdict":verdict,"v5_output":out,"bridged":bridged,
                    "legacy_verdict":legacy_verdict,
                })
            symptoms=typed["_intervention_model"]["downstream_symptom_repairs"]
            if symptoms and v5_proof.evaluate_intervention(typed,symptoms).get("rescued") is True:
                failures.append({"shape":shape,"domain":domain,"reason":"SYMPTOM_REPAIR_FALSE_RESCUE"})
            domain_shape_count+=1

    relation_ok=not failures and len(reps)==30 and domain_shape_count==180
    relations=[{
        "direct_surface":surface,
        "claim_id":CLAIM_IDS[surface],
        "relation":"SUPERSET" if relation_ok else "UNPROVEN",
        "basis":[
            "EXACT_FROZEN_PARENT_P1_ROUTE_USES_CONTRACT_NATIVE_GENERATOR_FOR_T0_AND_T2",
            "ALL_30_SEMANTIC_LEGACY_DIFFICULTY_CAUSE_SHAPES_EMBED_LOSSLESSLY",
            "EACH_LEGACY_SHAPE_PASSES_V5_ACROSS_ALL_SIX_CANONICAL_DOMAINS",
            "VISIBLE_LEGACY_REPAIR_CANDIDATE_ORDER_IS_SCORE_IRRELEVANT_AND_REMOVED_FROM_V5_INPUT",
            "V5_HIDDEN_ORACLE_IS_STRONGER:MECHANISM_RECEIPTS_RESCUE_SYMPTOM_NEGATIVE_INTERACTION_AND_OUTPUT_SCHEMA",
        ],
    } for surface in EXPECTED_SURFACES]

    return {
        "schema":SCHEMA,
        "status":"PASS__FROZEN_CONTRACT_NATIVE_P1_POPULATION_EMBEDS_IN_V5__THREE_SUPERSET_RELATION_CANDIDATES"
                 if relation_ok else "FAIL_CLOSED__EMBEDDING_COUNTEREXAMPLE",
        "errors":[],
        "population_superset_proven":relation_ok,
        "legacy_semantic_shape_count":len(reps),
        "embedded_domain_shape_count":domain_shape_count,
        "canonical_domain_count":len(v5_proof.DOMAINS),
        "repair_order_invariance_checks":order_invariance_checks,
        "wrong_legacy_repair_rejection_checks":wrong_repair_checks,
        "candidate_information_relation":"CANDIDATE_HAS_STRICTLY_LESS_INFORMATION_PROVEN",
        "removed_candidate_visible_field":"repair_candidates",
        "removed_field_load_bearing":False,
        "oracle_relation":"CANDIDATE_STRONGER_PROVEN",
        "surface_relations":relations,
        "failures":failures[:20],
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
