"""Positive adaptive policy cover over a sound finite overapproximation.

V1 required an exact complete finite policy-relevant world set. For a positive
proof that is stronger than necessary. If every true world is contained in a
declared finite overapproximation M, and the V1 adaptive cover succeeds for
*every* member of M, then it succeeds for every true world as a subset.

Failure on M is only unresolved: the failing member may be spurious. This V2
therefore never authorizes negative impossibility from an overapproximation.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any, Mapping
from canonical.runtime.observable_policy_cover_totality_gate_v1 import evaluate as evaluate_exact

SCHEMA="PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_OVERAPPROXIMATION_GATE_V2"

def _receipt(r: Any, state_id: str) -> bool:
    return (
        isinstance(r, Mapping)
        and r.get("independent_verified") is True
        and r.get("exact_byte_bound") is True
        and r.get("conclusion") == "success"
        and r.get("state_id") == state_id
        and r.get("true_worlds_subset_of_declared_overapproximation") is True
    )

def _fail(reason: str, **detail: Any) -> dict[str,Any]:
    out={
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "sound_overapproximation_cover_proved":False,
      "exact_true_world_set_completeness_required_for_positive_proof":False,
      "negative_impossibility_authorized":False,
      "u_empty_authorized":False,"terminal_authority":False,"terminal_credit_delta":0
    }
    if detail: out["detail"]=detail
    return out

def evaluate(problem: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(problem,Mapping): return _fail("PROBLEM_MAPPING_REQUIRED")
    state_id=problem.get("state_id")
    if not isinstance(state_id,str) or not state_id: return _fail("STATE_ID_REQUIRED")
    if not _receipt(problem.get("sound_overapproximation_receipt"),state_id):
        return _fail("SOUND_OVERAPPROXIMATION_RECEIPT_INVALID")

    inner=deepcopy(dict(problem))
    inner.pop("sound_overapproximation_receipt",None)
    inner["world_set_completeness_receipt"]={
      "independent_verified":True,
      "exact_byte_bound":True,
      "conclusion":"success",
      "policy_relevant_world_set_complete":True,
      "state_id":state_id,
    }
    structural=evaluate_exact(inner)
    if not structural.get("pass"):
        if structural.get("status") != "UNRESOLVED__NO_ADAPTIVE_COMMON_POLICY_COVER_FROM_DECLARED_DISCRIMINATORS":
            return _fail("INNER_STRUCTURAL_VALIDATION_FAILED",
                         v1_reason=structural.get("reason"),
                         v1_status=structural.get("status"))
        return {
          "schema":SCHEMA,"pass":False,
          "status":"UNRESOLVED__NO_POSITIVE_COVER_OVER_SOUND_OVERAPPROXIMATION",
          "state_id":state_id,
          "v1_structural_status":structural.get("status"),
          "v1_reason":structural.get("reason"),
          "unresolved_observational_classes":structural.get("unresolved_observational_classes",[]),
          "sound_overapproximation_cover_proved":False,
          "exact_true_world_set_completeness_required_for_positive_proof":False,
          "negative_impossibility_authorized":False,
          "failure_semantics":"FAILURE_OVER_AN_OVERAPPROXIMATION_CANNOT_PROVE_FAILURE_ON_TRUE_WORLD_SUPPORT__REFINE_OR_REMOVE_ONLY_SPURIOUS_REGIONS_WITH_SOUND_EVIDENCE",
          "u_empty_authorized":False,"terminal_authority":False,"terminal_credit_delta":0
        }
    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__SOUND_OVERAPPROXIMATION_ADAPTIVE_POLICY_COVER",
      "state_id":state_id,
      "decision_tree":structural["decision_tree"],
      "minimum_worst_case_resource_bound_units":structural["minimum_worst_case_resource_bound_units"],
      "sound_overapproximation_cover_proved":True,
      "true_world_cover_follows_by_subset_monotonicity":True,
      "exact_true_world_set_completeness_required_for_positive_proof":False,
      "complete_discriminator_library_required_for_positive_proof":False,
      "negative_impossibility_authorized":False,
      "u_empty_authorized":False,"terminal_authority":False,"terminal_credit_delta":0,
      "proof_rule":"W_TRUE_SUBSET_M_OVER__V1_TREE_COVERS_EVERY_M_OVER_MEMBER__THEREFORE_THE_SAME_TREE_COVERS_EVERY_TRUE_WORLD"
    }
