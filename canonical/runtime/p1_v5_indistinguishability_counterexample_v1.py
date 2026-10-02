"""Information-theoretic falsifier for the P1 V5 one-shot scope-superset claim.

The frozen P1 absolute population includes multiple visible deviations with only
one terminal rescuer, while unearned intervention outcomes are hidden from the
candidate. Therefore two worlds may have byte-identical candidate-visible input
but different unique intervention-established causes. A deterministic one-shot
candidate cannot be correct on both worlds.

This module constructs that pair using the exact V5 IR and scorer. It consumes no
terminal result and grants no capability credit.
"""
from __future__ import annotations
import copy, json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as proof

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V5_INDISTINGUISHABILITY_COUNTEREXAMPLE_V1"
ABSOLUTE="canonical/governance/P1_TRAJECTORY_ABSOLUTE_TERMINAL_BINDING_V1.json"
MULTIPLEX="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
SCOPE_GATE="canonical/governance/P1_V5_DIRECT_SURFACE_SCOPE_SUPERSET_V1.json"
DECLARED_CLASS="MULTIPLE_VISIBLE_DEVIATIONS_WITH_ONLY_ONE_TERMINAL_RESCUER"

def _load(rel:str)->dict[str,Any]:
    v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return v

def _unique_world(base:Mapping[str,Any], root:str, mechanism:str)->dict[str,Any]:
    case=copy.deepcopy(base)
    oracle={
        "status":"IDENTIFIED",
        "roots":[root],
        "critical":root,
        "mechanisms":{root:[mechanism]},
    }
    case["_oracle"]=oracle
    case["_intervention_model"]=proof._hidden_intervention_model(case["task"]["trajectory"],oracle)
    return case

def _identified_answer(root:str, mechanism:str)->dict[str,Any]:
    return {
        "status":"IDENTIFIED",
        "cause_action_id":root,
        "cause_action_ids":[root],
        "critical_action_id":root,
        "mechanism_classes":[mechanism],
        "supporting_receipts":[f"check:{root}:{mechanism}",f"receipt:{root}"],
        "repair_targets":[f"restore:{root}:{mechanism}"],
        "reason":"COUNTEREXAMPLE_WITNESS",
    }

def construct_pair()->tuple[dict[str,Any],dict[str,Any]]:
    # V5's AMBIGUOUS template exposes two independent failed roots A1/A2.
    # We hold every public byte fixed and vary only the hidden intervention truth:
    # exactly one repair rescues in each world, but it is a different repair.
    base=proof.generate_case(83001,pattern="AMBIGUOUS",domain="RESEARCH",kind="SCOPE")
    left=_unique_world(base,"A1","SCOPE")
    # AMBIGUOUS uses the next mechanism kind for A2; after SCOPE that is SCHEMA.
    right=_unique_world(base,"A2","SCHEMA")
    return left,right

def evaluate(
    absolute:Mapping[str,Any]|None=None,
    multiplex:Mapping[str,Any]|None=None,
    scope_gate:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    absolute=dict(absolute or _load(ABSOLUTE))
    multiplex=dict(multiplex or _load(MULTIPLEX))
    scope_gate=dict(scope_gate or _load(SCOPE_GATE))
    errors:list[str]=[]

    population=((absolute.get("population") or {}).get("classes") or [])
    if DECLARED_CLASS not in population:
        errors.append("DECLARED_UNIQUE_RESCUER_CLASS_MISSING")

    hidden=set(multiplex.get("hidden_evaluator_information") or [])
    forbidden=set(multiplex.get("candidate_must_not_receive") or [])
    visible=set(multiplex.get("candidate_visible_information") or [])
    if "HIDDEN_INTERVENTION_OUTCOMES_NOT_YET_EARNED" not in hidden:
        errors.append("UNEARNED_INTERVENTION_OUTCOME_NOT_HIDDEN")
    if "HIDDEN_INTERVENTION_OR_RESCUE_RESULT" not in forbidden:
        errors.append("HIDDEN_INTERVENTION_RESULT_NOT_FORBIDDEN")
    if "EARNED_TOOL_OUTPUTS_AND_EXECUTION_RECEIPTS" not in visible:
        errors.append("EARNED_EVIDENCE_CHANNEL_MISSING")

    if "SUPERSET" not in str(scope_gate.get("claimed_relation") or ""):
        errors.append("SCOPE_SUPERSET_CLAIM_NOT_PRESENT")

    left,right=construct_pair()
    pl=proof.public_task(left)
    pr=proof.public_task(right)
    public_identical=(pl==pr)
    if not public_identical:
        errors.append("PUBLIC_PAYLOAD_PAIR_NOT_IDENTICAL")

    left_gold=_identified_answer("A1","SCOPE")
    right_gold=_identified_answer("A2","SCHEMA")
    left_gold_on_left=proof.score_case(left,left_gold).get("pass") is True
    left_gold_on_right=proof.score_case(right,left_gold).get("pass") is True
    right_gold_on_right=proof.score_case(right,right_gold).get("pass") is True
    right_gold_on_left=proof.score_case(left,right_gold).get("pass") is True

    correct_outputs_differ=(
        left_gold_on_left and right_gold_on_right
        and not left_gold_on_right and not right_gold_on_left
    )
    if not correct_outputs_differ:
        errors.append("DIFFERENT_CORRECT_OUTPUTS_NOT_ESTABLISHED")

    out_left=candidate.solve(pl)
    out_right=candidate.solve(pr)
    deterministic_same_output=(out_left==out_right)
    if not deterministic_same_output:
        errors.append("DETERMINISTIC_SAME_INPUT_OUTPUT_PROPERTY_BROKEN")

    score_left=proof.score_case(left,out_left)
    score_right=proof.score_case(right,out_right)
    v5_passes_both=(score_left.get("pass") is True and score_right.get("pass") is True)

    # This is a finite indistinguishability proof, not a sampling inference:
    # identical candidate input + different required outputs => a one-shot
    # deterministic candidate cannot satisfy both worlds.
    information_theoretic_block=(
        public_identical and correct_outputs_differ and deterministic_same_output
        and not v5_passes_both
    )
    if not information_theoretic_block:
        errors.append("INDISTINGUISHABILITY_COUNTEREXAMPLE_DID_NOT_HOLD")

    valid=not errors
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__V5_ONE_SHOT_SCOPE_SUPERSET_FALSIFIED_BY_PUBLICLY_INDISTINGUISHABLE_UNIQUE_RESCUER_WORLDS__INTERVENTION_MUST_BECOME_EARNED_EVIDENCE"
            if valid else "FAIL_CLOSED__COUNTEREXAMPLE_SOURCE_OR_CONSTRUCTION_DRIFT"
        ),
        "audit_valid":valid,
        "errors":sorted(set(errors)),
        "declared_population_class":DECLARED_CLASS,
        "public_payloads_identical":public_identical,
        "hidden_worlds":{
            "left_unique_rescuer":"restore:A1:SCOPE",
            "right_unique_rescuer":"restore:A2:SCHEMA",
            "candidate_visible_difference":False,
        },
        "correct_outputs_provably_different":correct_outputs_differ,
        "v5_deterministic_output_identical":deterministic_same_output,
        "v5_output":out_left,
        "v5_world_scores":{"left":score_left,"right":score_right},
        "v5_passes_both_worlds":v5_passes_both,
        "one_shot_unique_identification_possible_under_current_information_boundary":False if information_theoretic_block else None,
        "scope_superset_claim_falsified":information_theoretic_block,
        "implication":[
            "THE_192_CASE_V5_MATRIX_DOES_NOT_COVER_A_DECLARED_P1_POPULATION_CLASS",
            "A_HIDDEN_UNIQUE_RESCUER_CANNOT_BE_IDENTIFIED_FROM_IDENTICAL_PRE_INTERVENTION_PUBLIC_INPUTS",
            "RETROACTIVE_COMPOSITION_WITH_AGGREGATE_T0_T2_RECEIPTS_CANNOT_REPAIR_THIS_INFORMATION_DEFICIT",
            "DO_NOT_PROMOTE_P1_V5_DIRECT_SURFACE_SCOPE_SUPERSET_V1_AS_TERMINAL_SCOPE_AUTHORITY",
        ],
        "minimal_repair":[
            "ADD_A_TWO_STAGE_EARNED_INTERVENTION_PROTOCOL_OR_AN_EQUIVALENT_VISIBLE_CAUSAL_DISCRIMINATOR",
            "PHASE_1_MAY_REQUEST_INTERVENTIONS_WITHOUT_CLAIMING_A_UNIQUE_CAUSE",
            "ONLY_OBSERVED_RESULTS_OF_REQUESTED_INTERVENTIONS_MAY_ENTER_PHASE_2_AS_EARNED_EVIDENCE",
            "REVERIFY_THE_DECLARED_MULTIPLE_VISIBLE_DEVIATIONS_WITH_ONE_RESCUER_CLASS_AND_ALL_EXISTING_V5_CLASSES",
            "THEN_RECOMPUTE_THE_THREE_TERMINAL_SCOPE_RELATIONS",
        ],
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
