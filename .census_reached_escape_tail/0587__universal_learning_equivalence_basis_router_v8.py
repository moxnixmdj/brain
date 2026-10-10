"""Universal Learning V8 equivalence/basis/residual router.

V8 strictly extends the verified V7 learner. It adds planning compression only:
- proof-gated equivalence classes,
- exact finite novelty-basis discovery,
- residual-driven learning priority.

V8 never overrides the V7 route, next action, trust result, or execution gates.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import equivalence_compression_v8 as eq
from canonical.runtime import novelty_basis_v8 as nb
from canonical.runtime import residual_priority_v8 as rp
from canonical.runtime import universal_learning_proof_program_router_v7 as v7

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_EQUIVALENCE_BASIS_ROUTER_V8"


def route(
    *,
    v7_args: Mapping[str, Any],
    equivalence_objects: Sequence[Mapping[str, Any]]=(),
    equivalence_mappings: Sequence[Mapping[str, Any]]=(),
    basis_primitives: Sequence[Mapping[str, Any]]=(),
    basis_targets: Sequence[Mapping[str, Any]]=(),
    residuals: Sequence[Mapping[str, Any]]=(),
)->dict[str, Any]:
    base=v7.route(**dict(v7_args))

    equivalence=None
    equivalence_status="NOT_REQUESTED"
    if equivalence_objects or equivalence_mappings:
        equivalence=eq.compress(objects=equivalence_objects,mappings=equivalence_mappings)
        equivalence_status=equivalence["status"]

    basis=None
    basis_status="NOT_REQUESTED"
    if basis_primitives or basis_targets:
        basis=nb.exact_basis(primitives=basis_primitives,targets=basis_targets)
        basis_status=basis["status"]

    residual_priority=None
    residual_status="NOT_REQUESTED"
    if residuals:
        residual_priority=rp.rank(residuals)
        residual_status=residual_priority["status"]

    return {
        "schema":SCHEMA,
        "status":"V8_PLANNING_COMPRESSION_APPLIED",
        "v7_result":base,
        "route":base.get("route"),
        "reason":"V8_MAY_COMPRESS_LEARNING_WORK_BUT_V7_REMAINS_LOAD_BEARING_DECISION_AND_TRUST_AUTHORITY",
        "next_action":base.get("next_action"),
        "trusted_execution_authorized":base.get("trusted_execution_authorized",False),
        "empirical_information_action_authorized":base.get("empirical_information_action_authorized",False),
        "equivalence_compression":equivalence,
        "equivalence_status":equivalence_status,
        "novelty_basis":basis,
        "novelty_basis_status":basis_status,
        "residual_priority":residual_priority,
        "residual_priority_status":residual_status,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }


def prove_v8_invariants()->dict[str,Any]:
    errors=[]

    def object_record(oid,sig):
        digest=eq.object_digest(object_id=oid,behavior_signature=sig,goal_scope="g")
        return {
            "object_id":oid,"goal_scope":"g","behavior_signature":sig,
            "verification_receipt":{
                "receipt_id":"obj-"+oid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","object_id":oid,"goal_scope":"g","object_sha256":digest,
            },
        }
    a=object_record("a",["x","y"])
    b=object_record("b",["x","y"])
    asha=eq.object_digest(object_id="a",behavior_signature=["x","y"],goal_scope="g")
    bsha=eq.object_digest(object_id="b",behavior_signature=["x","y"],goal_scope="g")
    md=eq.mapping_digest(
        source_sha256=bsha,representative_sha256=asha,goal_scope="g",
        basis="FORMAL_ISOMORPHISM",relation="EXACT",
    )
    comp=eq.compress(objects=[a,b],mappings=[{
        "source_id":"b","representative_id":"a","basis":"FORMAL_ISOMORPHISM","relation":"EXACT",
        "verification_receipt":{
            "receipt_id":"eq1","independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
            "behavior_equivalent_on_claimed_scope":True,
            "source_id":"b","representative_id":"a","goal_scope":"g",
            "basis":"FORMAL_ISOMORPHISM","relation":"EXACT","mapping_sha256":md,
        },
    }])
    if comp["representative_count_after"]!=1 or comp["compression_savings"]!=1:
        errors.append("EQUIVALENCE_COMPRESSION_BROKEN")

    def prim(pid,atoms,cost):
        digest=nb.primitive_digest(primitive_id=pid,covers_atoms=atoms,description_cost=cost)
        return {
            "primitive_id":pid,"covers_atoms":atoms,"description_cost":cost,
            "verification_receipt":{
                "receipt_id":"p-"+pid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","primitive_id":pid,"primitive_sha256":digest,
            },
        }
    def target(tid,atoms):
        digest=nb.target_digest(target_id=tid,required_atoms=atoms)
        return {
            "target_id":tid,"required_atoms":atoms,
            "verification_receipt":{
                "receipt_id":"t-"+tid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","required_atom_set_complete":True,
                "target_id":tid,"target_sha256":digest,
            },
        }
    bas=nb.exact_basis(
        primitives=[prim("wide",["a","b"],3),prim("a",["a"],1),prim("b",["b"],1)],
        targets=[target("task",["a","b"])],
    )
    if bas["selected_primitive_ids"]!=["a","b"] or bas["total_description_cost"]!="2":
        errors.append("EXACT_FINITE_BASIS_BROKEN")

    def resid(rid,critical,mass,fals,transfer,cost):
        digest=rp.residual_digest(
            residual_id=rid,decision_critical=critical,residual_mass_ub=mass,
            falsification_value_lcb=fals,future_transfer_lcb=transfer,acquisition_cost_ub=cost,
        )
        return {
            "residual_id":rid,"decision_critical":critical,"residual_mass_ub":mass,
            "falsification_value_lcb":fals,"future_transfer_lcb":transfer,"acquisition_cost_ub":cost,
            "verification_receipt":{
                "receipt_id":"r-"+rid,"independent_verified":True,"exact_byte_bound":True,
                "conclusion":"success","residual_id":rid,"residual_sha256":digest,
            },
        }
    ranked=rp.rank([
        resid("flashy",False,100,100,100,1),
        resid("critical",True,1,1,0,10),
    ])
    if ranked["ranked"][0]["residual_id"]!="critical":
        errors.append("DECISION_CRITICAL_PRIORITY_BROKEN")

    base=v7.prove_v7_invariants()
    if base.get("pass") is not True:
        errors.append("V7_BASE_INVARIANTS_NOT_PRESERVED")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"UNIVERSAL_LEARNING_V8_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "v7_base_preserved":base.get("pass") is True,
        "proof_gated_equivalence_compression":passed,
        "exact_finite_basis_optimality":passed,
        "decision_critical_residual_priority":passed,
        "semantic_success_rate_proved":False,
        "unknown_domain_acceptance_proved":False,
        "universal_novelty_basis_proved":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "incremental_spend_usd":0,
    }
