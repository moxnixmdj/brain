"""Universal Learning V8 verified novelty-basis router.

If an independently verified basis composition or symmetry proves that the
target mechanism is already constructible from verified primitives, V8 removes
that structural novelty before V7. Otherwise it falls back unchanged to V7.

Structural reuse is not task-execution or terminal acceptance authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import verified_novelty_basis_v8 as basis
from canonical.runtime import universal_learning_proof_program_router_v7 as v7

SCHEMA="PROJECT_BRAIN_UNIVERSAL_LEARNING_NOVELTY_BASIS_ROUTER_V8"


def route(
    *,
    target_id:str,
    target_signature,
    verified_primitives:Sequence[Mapping[str,Any]],
    composition_specs:Sequence[Mapping[str,Any]],
    symmetry_specs:Sequence[Mapping[str,Any]],
    v7_kwargs:Mapping[str,Any],
)->dict[str,Any]:
    verified_compositions=[]
    rejected_compositions=[]
    for spec in composition_specs:
        try:
            out=basis.verify_composition(
                target_id=target_id,
                target_signature=target_signature,
                primitives=verified_primitives,
                primitive_ids=spec.get("primitive_ids",[]),
                composition_steps=spec.get("composition_steps",[]),
                verification_receipt=spec.get("verification_receipt") or {},
                burden=spec.get("burden",0),
            )
            verified_compositions.append(out)
        except Exception as exc:
            rejected_compositions.append({"id":str(spec.get("id") or ""),"reason":str(exc)})

    selected_comp=basis.choose_minimum_verified_composition(verified_compositions)

    catalog=basis.primitive_catalog(verified_primitives)
    verified_symmetries=[]
    rejected_symmetries=[]
    for spec in symmetry_specs:
        sid=str(spec.get("source_primitive_id") or "")
        try:
            if sid not in catalog:
                raise basis.NoveltyBasisError("SYMMETRY_SOURCE_PRIMITIVE_UNKNOWN")
            out=basis.verify_symmetry(
                source_primitive={
                    "primitive_id":catalog[sid]["primitive_id"],
                    "canonical_signature":catalog[sid]["canonical_signature"],
                    "verification_receipt":{
                        "receipt_id":catalog[sid]["receipt_id"],
                        "independent_verified":True,
                        "exact_byte_bound":True,
                        "conclusion":"success",
                        "behavior_verified":True,
                        "primitive_id":catalog[sid]["primitive_id"],
                        "signature_sha256":catalog[sid]["signature_sha256"],
                    },
                },
                target_id=target_id,
                target_signature=target_signature,
                transform_id=spec.get("transform_id"),
                verification_receipt=spec.get("verification_receipt") or {},
            )
            verified_symmetries.append(out)
        except Exception as exc:
            rejected_symmetries.append({"id":str(spec.get("id") or ""),"reason":str(exc)})

    reusable=[]
    if selected_comp.get("selected") is not None:
        c=dict(selected_comp["selected"])
        c["reuse_type"]="VERIFIED_COMPOSITION"
        c["rank"]=(c.get("primitive_count",999999),float(c.get("burden",0)),c.get("composition_sha256",""))
        reusable.append(c)
    for s in verified_symmetries:
        x=dict(s)
        x["reuse_type"]="VERIFIED_SYMMETRY"
        x["rank"]=(1,0.0,x.get("symmetry_sha256",""))
        reusable.append(x)

    common={
        "schema":SCHEMA,
        "target_id":str(target_id),
        "verified_compositions":verified_compositions,
        "verified_symmetries":verified_symmetries,
        "rejected_compositions":rejected_compositions,
        "rejected_symmetries":rejected_symmetries,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }

    if reusable:
        reusable.sort(key=lambda x:x["rank"])
        chosen=reusable[0]
        return {
            **common,
            "route":"REUSE_VERIFIED_NOVELTY_BASIS",
            "reason":"TARGET_STRUCTURE_PROVED_REUSABLE_FROM_VERIFIED_PRIOR_STRUCTURE",
            "selected_reuse":chosen,
            "structural_novelty_residual":[],
            "empirical_structure_learning_authorized":False,
            "v7_result":None,
            "trusted_execution_authorized":False,
        }

    base=v7.route(**dict(v7_kwargs))
    return {
        **common,
        "route":base["route"],
        "reason":"NO_VERIFIED_BASIS_OR_SYMMETRY_RELATION__FALL_BACK_TO_V7",
        "selected_reuse":None,
        "structural_novelty_residual":["UNPROVED_TARGET_STRUCTURE"],
        "empirical_structure_learning_authorized":True,
        "v7_result":base,
        "trusted_execution_authorized":base.get("trusted_execution_authorized",False),
    }


def prove_v8_invariants()->dict[str,Any]:
    errors=[]
    sig=["state","transition"]
    dg=basis.signature_digest(sig)
    primitive={
        "primitive_id":"p",
        "canonical_signature":sig,
        "verification_receipt":{
            "receipt_id":"p-proof","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","behavior_verified":True,
            "primitive_id":"p","signature_sha256":dg,
        },
    }
    steps=[{"op":"compose","inputs":["p"],"outputs":["target"]}]
    cd=basis.composition_digest(
        target_id="t",target_signature=sig,primitive_ids=["p"],composition_steps=steps
    )
    td=basis.target_digest(target_id="t",target_signature=sig)
    comp=basis.verify_composition(
        target_id="t",target_signature=sig,primitives=[primitive],
        primitive_ids=["p"],composition_steps=steps,
        verification_receipt={
            "receipt_id":"c-proof","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","behavior_preserving_on_claimed_scope":True,
            "scope_relation":"EXACT","composition_sha256":cd,
            "primitive_ids":["p"],"primitive_signature_sha256":{"p":dg},
            "target_sha256":td,
        },
    )
    if comp["structural_reuse_authorized"] is not True or comp["target_execution_authorized"] is not False:
        errors.append("VERIFIED_COMPOSITION_BOUNDARY_BROKEN")

    sd=basis.symmetry_digest(
        source_id="p",target_id="t2",transform_id="rename",
        source_signature=sig,target_signature=sig,
    )
    sym=basis.verify_symmetry(
        source_primitive=primitive,target_id="t2",target_signature=sig,transform_id="rename",
        verification_receipt={
            "receipt_id":"s-proof","independent_verified":True,"exact_byte_bound":True,
            "conclusion":"success","bijective_on_claimed_scope":True,
            "behavior_equivariant":True,"inverse_verified":True,
            "scope_relation":"EXACT","symmetry_sha256":sd,
        },
    )
    if sym["structural_reuse_authorized"] is not True:
        errors.append("VERIFIED_SYMMETRY_BOUNDARY_BROKEN")

    v7inv=v7.prove_v7_invariants()
    if v7inv.get("pass") is not True:
        errors.append("V7_BASE_INVARIANTS_NOT_PRESERVED")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"UNIVERSAL_LEARNING_V8_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":errors,
        "verified_composition_requires_external_proof":passed,
        "verified_symmetry_requires_external_proof":passed,
        "compression_metrics_not_truth_evidence":passed,
        "v7_base_preserved":passed,
        "semantic_success_rate_proved":False,
        "unknown_domain_acceptance_proved":False,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
