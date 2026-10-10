"""Bounded executable R10 Professional challenge verifier.

Exercises existing verified Brain mechanisms against exact R10 failure modes:
nondominated alternatives, semantic plurality, missing risk/normative/compensation
policy, and multiplicity escalation. This proves only fail-closed execution
behavior for those challenge classes; it does not invent or close the missing
policies themselves.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any

from canonical.runtime import one_shot_reality_closure_v2 as decision
from canonical.runtime import option_preserving_capability_optimizer_v1 as options

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_CHALLENGE_V1"
PROFILE_REL="canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
PROFILE_BLOB="f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
BINDING_REL="canonical/governance/PROFESSIONAL_QUALITY_R10_ROOT_SUBJECT_BINDING_20261010_V1.json"
BINDING_BLOB="6d8cc56e9273f15f199a624c4a11f1482c76e039"

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load(rel:str,sha:str)->dict[str,Any]:
    p=ROOT/rel
    if not p.is_file() or p.is_symlink() or _blob(p)!=sha:
        raise RuntimeError("BOUND_SOURCE_STALE:"+rel)
    value=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise RuntimeError("BOUND_SOURCE_NOT_OBJECT:"+rel)
    return value

def _cap(cid:str,*,semantic:str="r10-shared",capability:int=1,generalization:int=1,
         reliability:int=1,latency:int=10,compute:int=10,memory:int=10)->dict[str,Any]:
    return {
        "capability_id":cid,
        "semantic_contract_sha256":semantic,
        "implementation_family":"r10-"+cid,
        "representation_family":"r10",
        "substrate_family":"cpu",
        "reusable_capability":True,
        "independently_verified":True,
        "capability":capability,
        "generalization":generalization,
        "reliability":reliability,
        "latency":latency,
        "compute":compute,
        "memory":memory,
        "incremental_spend_usd":0,
    }

def evaluate()->dict[str,Any]:
    profile=_load(PROFILE_REL,PROFILE_BLOB)
    binding=_load(BINDING_REL,BINDING_BLOB)

    old=_cap("incumbent")
    a=_cap("quality-leaning",capability=2,latency=5)
    b=_cap("generalization-leaning",generalization=2,compute=5)
    nondominated=options.select_effective_for_scope(
        [old,a,b],default_capability_id="incumbent"
    )
    no_arbitrary_default=(
        nondominated.get("pass") is False
        and nondominated.get("status")=="OPEN__TASK_PREFERENCE_REQUIRED_ACROSS_NONDOMINATED_FRONTIER"
        and nondominated.get("global_preferred_default_capability_id") is None
        and set(nondominated.get("global_active_capability_ids") or [])
            == {"quality-leaning","generalization-leaning"}
    )

    semantic_plurality=options.select_active_frontier([
        _cap("policy-a",semantic="semantic:a",latency=100,compute=100),
        _cap("policy-b",semantic="semantic:b",latency=1,compute=1),
    ])
    semantic_noncollapse=set(semantic_plurality.get("active_capability_ids") or [])=={"policy-a","policy-b"}

    closure={
        "schema":"PROJECT_BRAIN_R10_CHALLENGE_SOURCE_V1",
        "status":"OPEN",
        "pass":False,
        "residual":{
            "internal_blockers":[],
            "evidence_blockers":[
                "COMPENSATION_RULE_UNSPECIFIED",
                "NORMATIVE_AGGREGATION_POLICY_UNSPECIFIED",
                "TAIL_RISK_POLICY_UNSPECIFIED",
                "NORMATIVE_AGGREGATION_POLICY_UNSPECIFIED",
            ],
            "pending_acquisition_or_experiment_required":True,
        },
    }
    gap=decision.compile_gap_contract(closure)
    sufficient=decision.compile_decision_sufficient_contract(gap)
    minimum=decision.compile_minimum_information_contract(gap,sufficient)
    blockers={row.get("blocker") for row in minimum.get("requests") or []}
    minimum_policy_info=(
        gap.get("gap_class")=="PENDING_ACQUISITION_OR_EXPERIMENT"
        and sufficient.get("pass") is True
        and sufficient.get("reduction_mode")=="LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION"
        and sufficient.get("omitted_evidence")==[]
        and blockers=={
            "COMPENSATION_RULE_UNSPECIFIED",
            "NORMATIVE_AGGREGATION_POLICY_UNSPECIFIED",
            "TAIL_RISK_POLICY_UNSPECIFIED",
        }
        and minimum.get("request_count")==3
        and all(
            row.get("broad_acquisition_forbidden_without_minimality_proof") is True
            and row.get("proof_or_existing_receipt_precedes_new_reality") is True
            for row in minimum.get("requests") or []
        )
        and (minimum.get("proof_precedence") or [])[-1]=="FULL_EMPIRICAL_EVALUATION_LAST"
        and minimum.get("verification_authority_mutation_allowed") is False
    )

    triggers=set(profile.get("escalation_triggers") or [])
    steps=set(profile.get("steps") or [])
    profile_guard=(
        "MODEL_OR_ANALYSIS_MULTIPLICITY_DECISION_SENSITIVE" in triggers
        and "HIGH_CONSEQUENCE_OR_VETO_DIMENSION" in triggers
        and "REFERENCE_AMBIGUITY_OR_PLURALITY" in triggers
        and "ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT" in steps
    )

    limitations=set((binding.get("binding_scope") or {}).get("limitations") or [])
    open_truths={
        "GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE":
            "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE" in limitations,
        "NORMATIVE_AGGREGATION_CLOSURE":
            "NO_NORMATIVE_AGGREGATION_CLOSURE" in limitations,
        "MODEL_MULTIPLICITY_DECISION_CLOSURE":
            "NO_MODEL_MULTIPLICITY_DECISION_CLOSURE" in limitations,
        "COMPENSATION_POLICY_CLOSURE":True,
    }
    checks={
        "NONDOMINATED_ALTERNATIVES_DO_NOT_GET_ARBITRARY_DEFAULT":no_arbitrary_default,
        "DIFFERENT_SEMANTIC_CONTRACTS_DO_NOT_DOMINATE_EACH_OTHER":semantic_noncollapse,
        "MISSING_POLICY_PARAMETERS_COMPILE_TO_MINIMUM_INFORMATION":minimum_policy_info,
        "MULTIPLICITY_AND_VETO_CONDITIONS_TRIGGER_ESCALATION_OR_ABSTENTION":profile_guard,
    }
    passed=all(checks.values())
    return {
        "schema":SCHEMA,
        "status":"PASS__BOUNDED_R10_FAIL_CLOSED_EXECUTION_CHALLENGES__GLOBAL_POLICY_TRUTH_OPEN"
            if passed else "FAIL_CLOSED",
        "pass":passed,
        "checks":checks,
        "observed":{
            "nondominated_status":nondominated.get("status"),
            "nondominated_active_ids":nondominated.get("global_active_capability_ids"),
            "minimum_information_blockers":sorted(blockers),
            "minimum_information_request_count":minimum.get("request_count"),
        },
        "bounded_execution_evidence":{
            "anti_posthoc_scalarization":no_arbitrary_default,
            "semantic_plurality_preserved":semantic_noncollapse,
            "missing_policy_not_fabricated":minimum_policy_info,
            "decision_sensitive_multiplicity_escalated":profile_guard,
        },
        "still_open_property_truth":open_truths,
        "r10_execution_leaf_closed":False,
        "r10_root_closed":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
