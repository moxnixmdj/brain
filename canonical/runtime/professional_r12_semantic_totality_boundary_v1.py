"""R12 semantic material-totality boundary.

This module proves a negative and a constructive cut.

Negative:
  A finite known-challenge catalog, even together with all eight R12
  root-contract clauses, cannot by itself prove that no materially distinct
  false-certification mechanism exists outside the catalog.

Constructive:
  The stronger R12 semantic totality obligation may close only through one of
  three complete routes:
    1. a complete materiality decider;
    2. a proved finite characteristic partition;
    3. complete mediation of every positive certification through a
       claim-scoped local totality certificate whose own basis is complete.

Route 3 allows unknown/open-world inputs to fail closed rather than requiring
global enumeration. Nonvacuity remains separately required.

This module grants zero property, quality, acceptance, promotion, or terminal
authority by itself.
"""
from __future__ import annotations
from typing import Any

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_TOTALITY_BOUNDARY_V1"


class TotalityBoundaryError(ValueError):
    pass


def finite_catalog_countermodel(
    *,
    observed_challenge_ids:list[str],
    all_eight_root_contract_clauses_verified:bool,
    latent_material_mechanism_id:str,
)->dict[str,Any]:
    if not isinstance(observed_challenge_ids,list) or any(
        not isinstance(x,str) or not x for x in observed_challenge_ids
    ):
        raise TotalityBoundaryError("OBSERVED_CHALLENGE_IDS_INVALID")
    if len(observed_challenge_ids)!=len(set(observed_challenge_ids)):
        raise TotalityBoundaryError("OBSERVED_CHALLENGE_IDS_DUPLICATE")
    if not isinstance(all_eight_root_contract_clauses_verified,bool):
        raise TotalityBoundaryError("EIGHT_CLAUSE_FLAG_INVALID")
    if not isinstance(latent_material_mechanism_id,str) or not latent_material_mechanism_id:
        raise TotalityBoundaryError("LATENT_MECHANISM_ID_INVALID")
    if latent_material_mechanism_id in observed_challenge_ids:
        raise TotalityBoundaryError("LATENT_MECHANISM_ALREADY_OBSERVED")

    return {
        "schema":SCHEMA,
        "observed_catalog_equal_in_two_worlds":True,
        "eight_clause_evidence_equal_in_two_worlds":all_eight_root_contract_clauses_verified,
        "world_without_latent_mechanism_false_certification_from_latent":False,
        "world_with_latent_mechanism_false_certification_from_latent":True,
        "latent_material_mechanism_id":latent_material_mechanism_id,
        "finite_catalog_plus_eight_clauses_insufficient_for_open_world_totality":
            all_eight_root_contract_clauses_verified,
        "reason":(
            "THE_OBSERVED_FINITE_EVIDENCE_IS_IDENTICAL_WHILE_THE_EXISTENCE_OF_AN_"
            "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_MECHANISM_DIFFERS"
        ),
    }


def evaluate_closure_routes(
    *,
    complete_materiality_decider:bool,
    finite_characteristic_partition_proved:bool,
    positive_certification_gate_complete_mediation:bool,
    every_positive_certificate_has_claim_scoped_complete_local_totality_basis:bool,
    unknown_or_unproved_local_totality_blocks_positive_certification:bool,
    nonvacuous_positive_route_proved:bool,
)->dict[str,Any]:
    values={
        "complete_materiality_decider":complete_materiality_decider,
        "finite_characteristic_partition_proved":finite_characteristic_partition_proved,
        "positive_certification_gate_complete_mediation":positive_certification_gate_complete_mediation,
        "every_positive_certificate_has_claim_scoped_complete_local_totality_basis":
            every_positive_certificate_has_claim_scoped_complete_local_totality_basis,
        "unknown_or_unproved_local_totality_blocks_positive_certification":
            unknown_or_unproved_local_totality_blocks_positive_certification,
        "nonvacuous_positive_route_proved":nonvacuous_positive_route_proved,
    }
    for name,value in values.items():
        if not isinstance(value,bool):
            raise TotalityBoundaryError(name.upper()+"_FLAG_INVALID")

    direct_decider=complete_materiality_decider
    characteristic=finite_characteristic_partition_proved
    proof_carrying_positive=(
        positive_certification_gate_complete_mediation
        and every_positive_certificate_has_claim_scoped_complete_local_totality_basis
        and unknown_or_unproved_local_totality_blocks_positive_certification
        and nonvacuous_positive_route_proved
    )
    totality=direct_decider or characteristic or proof_carrying_positive

    if direct_decider:
        basis="COMPLETE_MATERIALITY_DECIDER"
    elif characteristic:
        basis="PROVED_FINITE_CHARACTERISTIC_PARTITION"
    elif proof_carrying_positive:
        basis="COMPLETE_PROOF_CARRYING_POSITIVE_CERTIFICATION_MEDIATION"
    else:
        basis=None

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":(
            "PASS__STRONGER_MATERIAL_TOTALITY_ROUTE_ESTABLISHED"
            if totality else
            "OPEN__NO_COMPLETE_MATERIAL_TOTALITY_ROUTE"
        ),
        "stronger_material_defeater_totality_proved":totality,
        "closure_basis":basis,
        "complete_materiality_decider":direct_decider,
        "finite_characteristic_partition_proved":characteristic,
        "proof_carrying_positive_certification_route_proved":proof_carrying_positive,
        "always_abstain_vacuity_forbidden":True,
        "nonvacuity_required_for_proof_carrying_route":True,
        "finite_known_catalog_is_totality_authority":False,
        "eight_root_contract_clauses_are_totality_authority":False,
        "cc_r3_terminal_closure_proved":False,
        "semantic_property_truth_authority":False,
        "r4_proof_realization_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def current_boundary()->dict[str,Any]:
    out=evaluate_closure_routes(
        complete_materiality_decider=False,
        finite_characteristic_partition_proved=False,
        positive_certification_gate_complete_mediation=False,
        every_positive_certificate_has_claim_scoped_complete_local_totality_basis=False,
        unknown_or_unproved_local_totality_blocks_positive_certification=False,
        nonvacuous_positive_route_proved=True,
    )
    out["current_r12_clause_state"]="8_OF_8_VERIFIED"
    out["current_c8_nonvacuity_proved"]=True
    out["current_exact_residual"]=(
        "PROVE_COMPLETE_MATERIALITY_DECIDER_OR_FINITE_CHARACTERISTIC_PARTITION_OR_"
        "COMPLETE_PROOF_CARRYING_POSITIVE_CERTIFICATION_MEDIATION"
    )
    return out
