"""Universal refinement theorem from the frozen terminal P1 generator to V6.

This is not a replay of historical terminal cases. The frozen contract-native P1
generator has a finite structural quotient:
  difficulty d in 1..5 => n=6+d trajectory steps,
  causal step c in 1..n-3,
  all repair-list orderings differ only by permutation.
That yields 4+5+6+7+8 = 30 structural classes. We exhaust every class across
all six V6 normalized domains and prove:
  * old candidate accepts the abstract old-generator case;
  * V6 identifies the same causal step after a public-only normalization;
  * V6's proposed root repair actually rescues the terminal causal slice;
  * a downstream symptom-only repair does not rescue;
  * lowering the V6 result recovers the exact old candidate output.
The theorem is pinned to exact source blobs for the old generator/candidate,
terminal parent runner/binding, and exact independently verified V6 bytes.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_brain_candidate as old_candidate
from canonical.runtime import contract_native_proof_suites as old_suite
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as v6_candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as v6_proof

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V6_UNIVERSAL_TERMINAL_GENERATOR_REFINEMENT_V1"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
DOMAINS=tuple(v6_proof.DOMAINS)

EXACT_BLOBS={
 "canonical/runtime/contract_native_proof_suites.py":"0210790c7dd705ef328e1b55d529a30c5c6c3337",
 "canonical/runtime/contract_native_brain_candidate.py":"afc18af1d1da6f25166c6cc57dcbc0cd3070bb85",
 "canonical/runtime/terminal_parent_portfolio_runner_v1.py":"431b62e503a6a179f19339ae5e0ab6948424a650",
 "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json":"a1630299d29ea9c07e55b4314c07ddb3228c3287",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py":"18d4de68ee8352410e986c318868642333ec085a",
 "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py":"0f41a36e6ad16722ce05b180e036fb921a2ef886",
 "canonical/verification/P1_TYPED_CAUSAL_INTERVENTION_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"1e722621db8f0f1cb3b9689e48d4bfe356dcb36e",
}
V6_RECEIPT="canonical/verification/P1_TYPED_CAUSAL_INTERVENTION_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
PARENT_BINDING="canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"


def _blob(rel:str)->str:
    b=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def _source_guard()->list[str]:
    errors=[]
    for rel,expected in EXACT_BLOBS.items():
        try:
            got=_blob(rel)
        except Exception as exc:
            errors.append(f"UNREADABLE:{rel}:{type(exc).__name__}")
            continue
        if got!=expected:
            errors.append(f"BLOB_DRIFT:{rel}:{got}")
    try:
        binding=json.loads((ROOT/PARENT_BINDING).read_text(encoding="utf-8"))
        row=binding["schedules"][BEHAVIOR]
        if row.get("mode")!="CONTRACT_NATIVE":
            errors.append("P1_PARENT_MODE_DRIFT")
        if row.get("case_count")!=30:
            errors.append("P1_PARENT_CASE_COUNT_DRIFT")
        if row.get("difficulty_cycle")!=[1,2,3,4,5]:
            errors.append("P1_DIFFICULTY_CYCLE_DRIFT")
        exact=binding.get("exact_brain_blobs") or {}
        if exact.get("canonical/runtime/contract_native_proof_suites.py")!=EXACT_BLOBS["canonical/runtime/contract_native_proof_suites.py"]:
            errors.append("PARENT_BINDING_OLD_SUITE_PIN_DRIFT")
        if exact.get("canonical/runtime/contract_native_brain_candidate.py")!=EXACT_BLOBS["canonical/runtime/contract_native_brain_candidate.py"]:
            errors.append("PARENT_BINDING_OLD_CANDIDATE_PIN_DRIFT")
    except Exception as exc:
        errors.append("PARENT_BINDING_INVALID:"+type(exc).__name__)
    try:
        receipt=json.loads((ROOT/V6_RECEIPT).read_text(encoding="utf-8"))
        if not str(receipt.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
            errors.append("V6_NOT_INDEPENDENTLY_VERIFIED")
        exact=receipt.get("exact_brain_blobs") or {}
        for rel in (
            "canonical/runtime/trajectory_failure_typed_ir_candidate_v6.py",
            "canonical/runtime/trajectory_failure_typed_ir_proof_v6.py",
        ):
            if exact.get(rel)!=EXACT_BLOBS[rel]:
                errors.append("V6_RECEIPT_PIN_DRIFT:"+rel)
    except Exception as exc:
        errors.append("V6_RECEIPT_INVALID:"+type(exc).__name__)
    return sorted(set(errors))


def structural_classes()->list[tuple[int,int,int]]:
    """All (difficulty,n,cause) classes admitted by exact _trajectory_case."""
    out=[]
    for difficulty in range(1,6):
        n=max(5,min(14,6+difficulty))
        for cause in range(1,n-2):
            out.append((difficulty,n,cause))
    return out


def abstract_old_case(difficulty:int,cause:int,*,repair_order:str="canonical")->dict[str,Any]:
    if difficulty not in range(1,6):
        raise ValueError("DIFFICULTY")
    n=max(5,min(14,6+difficulty))
    if cause not in range(1,n-2):
        raise ValueError("CAUSE")
    steps=[]
    for i in range(n):
        if i<cause:
            state="OK"; invariant=True; symptom=False
        elif i==cause:
            state="FAULT_INJECTED"; invariant=False; symptom=False
        else:
            state="DOWNSTREAM_DEGRADED"; invariant=False; symptom=True
        steps.append({
            "step":i,"action":f"A{i}","state":state,
            "invariant_pass":invariant,"terminal_symptom":symptom,
        })
    repairs=[{"id":f"repair_{i}","targets_step":i} for i in range(cause,n-1)]
    if repair_order=="reverse":
        repairs=list(reversed(repairs))
    elif repair_order=="rotate" and repairs:
        repairs=repairs[1:]+repairs[:1]
    elif repair_order!="canonical":
        raise ValueError("REPAIR_ORDER")
    return {
        "schema":old_suite.SCHEMA,
        "contract":BEHAVIOR,
        "seed":-1,
        "task":{"trajectory":steps,"repair_candidates":repairs},
        "_oracle":{"cause_step":cause,"repair_id":f"repair_{cause}"},
    }


def lift_public(old_public:Mapping[str,Any],domain:str)->dict[str,Any]:
    """Normalize only candidate-visible old fields into V6 typed IR."""
    if domain not in DOMAINS:
        raise ValueError("DOMAIN")
    if old_public.get("contract")!=BEHAVIOR:
        raise ValueError("CONTRACT")
    task=old_public.get("task")
    if not isinstance(task,Mapping):
        raise ValueError("TASK")
    trajectory=task.get("trajectory")
    repairs=task.get("repair_candidates")
    if not isinstance(trajectory,list) or not trajectory or not isinstance(repairs,list):
        raise ValueError("OLD_TRAJECTORY")

    # Validate the repair relation as a set, deliberately erasing permutation.
    repair_targets={}
    for row in repairs:
        if not isinstance(row,Mapping):
            raise ValueError("REPAIR_ROW")
        rid=row.get("id"); target=row.get("targets_step")
        if not isinstance(rid,str) or not isinstance(target,int) or isinstance(target,bool):
            raise ValueError("REPAIR_FIELDS")
        if target in repair_targets:
            raise ValueError("DUPLICATE_REPAIR_TARGET")
        repair_targets[target]=rid

    failed_steps=[]
    for idx,row in enumerate(trajectory):
        if not isinstance(row,Mapping) or row.get("step")!=idx:
            raise ValueError("STEP_SEQUENCE")
        passed=row.get("invariant_pass")
        if type(passed) is not bool:
            raise ValueError("INVARIANT_FLAG")
        if not passed:
            failed_steps.append(idx)
    if not failed_steps:
        raise ValueError("NO_FAILURE")
    root=min(failed_steps)
    if set(repair_targets)!=(set(range(root,len(trajectory)-1))):
        raise ValueError("FROZEN_REPAIR_SET_GRAMMAR_MISMATCH")

    p=f"legacy:{domain.lower()}:"
    rows=[]
    for idx,row in enumerate(trajectory):
        passed=bool(row["invariant_pass"])
        check={
            "kind":"INVARIANT",
            "id":f"A{idx}:INVARIANT",
            "pass":passed,
            "evidence":[] if passed else [f"legacy-visible-invariant:A{idx}"],
        }
        if not passed:
            check["failure_semantics"]="DIRECT_CONTRACT" if idx==root else "DERIVED_UPSTREAM"
        rows.append({
            "step":idx,
            "action_id":f"A{idx}",
            "domain":domain,
            "reads":[] if idx==0 else [p+f"state:{idx-1}"],
            "writes":[p+f"state:{idx}"],
            "depends_on":[] if idx==0 else [f"A{idx-1}"],
            "dependency_composition":"SEQUENTIAL",
            "checks":[check],
        })
    return {
        "schema":"PROJECT_BRAIN_P1_V6_LEGACY_CONTRACT_NATIVE_NORMALIZATION_V1",
        "behavior_id":BEHAVIOR,
        "task":{
            "domain":domain,
            "trajectory":rows,
            "terminal_failed_resources":[p+f"state:{len(rows)-1}"],
            "goal":"PRESERVE_FROZEN_P1_CAUSAL_LOCALIZATION_AND_FORWARD_RESCUE",
        },
    }


def lower_to_old(old_public:Mapping[str,Any],v6_out:Mapping[str,Any])->dict[str,Any]:
    if v6_out.get("status")!="IDENTIFIED":
        raise ValueError("V6_NOT_IDENTIFIED")
    aid=v6_out.get("cause_action_id")
    if not isinstance(aid,str) or not aid.startswith("A") or not aid[1:].isdigit():
        raise ValueError("V6_CAUSE_ID")
    cause=int(aid[1:])
    repairs=((old_public.get("task") or {}).get("repair_candidates") or [])
    matches=[
        row for row in repairs
        if isinstance(row,Mapping)
        and row.get("targets_step")==cause
        and isinstance(row.get("id"),str)
    ]
    if len(matches)!=1:
        raise ValueError("OLD_REPAIR_NOT_UNIQUE")
    return {"cause_step":cause,"repair_id":matches[0]["id"],"evidence_steps":[cause]}


def evaluate()->dict[str,Any]:
    errors=_source_guard()
    classes=structural_classes()
    if len(classes)!=30:
        errors.append("STRUCTURAL_CLASS_COUNT_NOT_30")

    checked=0
    rescue_count=0
    symptom_negative_count=0
    permutation_checks=0
    failures=[]
    for difficulty,n,cause in classes:
        for repair_order in ("canonical","reverse","rotate"):
            old_case=abstract_old_case(difficulty,cause,repair_order=repair_order)
            old_public=old_suite.public_task(old_case)
            try:
                old_out=old_candidate.solve(old_public)
                old_verdict=old_suite.score_case(old_case,old_out)
            except Exception as exc:
                failures.append(f"OLD_FAIL:d{difficulty}:c{cause}:{repair_order}:{type(exc).__name__}")
                continue
            if old_verdict.get("pass") is not True:
                failures.append(f"OLD_SCORE_FAIL:d{difficulty}:c{cause}:{repair_order}")
                continue

            baseline_v6=None
            for domain in DOMAINS:
                try:
                    lifted=lift_public(old_public,domain)
                    v6_out=v6_candidate.solve(lifted)
                    lowered=lower_to_old(old_public,v6_out)
                    iv=v6_proof.execute_intervention(lifted,v6_out)
                except Exception as exc:
                    failures.append(f"V6_EXCEPTION:d{difficulty}:c{cause}:{repair_order}:{domain}:{type(exc).__name__}")
                    continue
                checked+=1
                if lowered!=old_out:
                    failures.append(f"REFINEMENT_MISMATCH:d{difficulty}:c{cause}:{repair_order}:{domain}")
                if v6_out.get("mechanism_classes")!=["INVARIANT"]:
                    failures.append(f"MECHANISM_MISMATCH:d{difficulty}:c{cause}:{repair_order}:{domain}")
                if iv.get("terminal_rescued") is not True:
                    failures.append(f"ROOT_REPAIR_NO_RESCUE:d{difficulty}:c{cause}:{repair_order}:{domain}")
                else:
                    rescue_count+=1
                symptom=dict(v6_out)
                symptom["repair_targets"]=[f"restore:A{cause+1}:INVARIANT"]
                neg=v6_proof.execute_intervention(lifted,symptom)
                if neg.get("terminal_rescued") is not False:
                    failures.append(f"SYMPTOM_REPAIR_FALSE_RESCUE:d{difficulty}:c{cause}:{repair_order}:{domain}")
                else:
                    symptom_negative_count+=1
                projection=(v6_out.get("cause_action_id"),tuple(v6_out.get("repair_targets") or []))
                if baseline_v6 is None:
                    baseline_v6=projection
                elif projection!=baseline_v6:
                    failures.append(f"DOMAIN_PROJECTION_DRIFT:d{difficulty}:c{cause}:{repair_order}:{domain}")
            permutation_checks+=1

    expected=len(classes)*3*len(DOMAINS)
    if checked!=expected:
        errors.append(f"CHECK_COUNT:{checked}!={expected}")
    if rescue_count!=expected:
        errors.append(f"RESCUE_COUNT:{rescue_count}!={expected}")
    if symptom_negative_count!=expected:
        errors.append(f"SYMPTOM_NEGATIVE_COUNT:{symptom_negative_count}!={expected}")
    errors.extend(failures[:100])
    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__UNIVERSAL_REFINEMENT_OF_FROZEN_TERMINAL_P1_GENERATOR_CLASS_INTO_V6__ZERO_TERMINAL_REPLAY__ZERO_CREDIT" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "structural_equivalence_class_count":len(classes),
        "difficulty_count":5,
        "cause_position_class_count_by_difficulty":{str(d):sum(1 for x in classes if x[0]==d) for d in range(1,6)},
        "repair_order_normalizations_tested":3,
        "normalized_domain_count":len(DOMAINS),
        "refinement_checks":checked,
        "forward_rescue_checks":rescue_count,
        "symptom_only_negative_checks":symptom_negative_count,
        "relation":"V6_STRICTLY_REFINES_THE_EXACT_FROZEN_CONTRACT_NATIVE_P1_GENERATOR_BEHAVIORAL_CLASS_AFTER_PUBLIC_ONLY_NORMALIZATION",
        "scope_limit":"THIS_PROVES_THE_EXECUTED_OLD_P1_GENERATOR_CLASS_IS_CONTAINED_IN_V6__IT_DOES_NOT_BY_ITSELF_PROVE_PRIVATE_BENCHMARK_POPULATION_EQUIVALENCE_FOR_FRONTIERCODE_CURSORBENCH_OR_RECOVERY",
        "terminal_results_replayed":0,
        "historical_terminal_case_ids_read":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
