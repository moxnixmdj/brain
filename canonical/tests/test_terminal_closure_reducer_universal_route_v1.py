from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "runtime" / "terminal_closure_reducer.py"
SPEC = importlib.util.spec_from_file_location("terminal_closure_reducer_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def _manifest(*, proof_bundle_frozen: bool = True) -> dict:
    families = [
        {
            "id": f"FAMILY_{i:02d}",
            "closure_state": "OPEN",
            "opus55_acceptance_state": "OPEN",
            "opus55_acceptance_calibrated": False,
            "ownership_status": "OPEN",
            "unresolved": ["OPEN"],
        }
        for i in range(19)
    ]
    return {
        "expected_family_count": 19,
        "actual_family_count": 19,
        "families": families,
        "counters": {
            "uncontracted_required_behaviors": 0,
            "unproved_required_behaviors": 0,
            "donor_dependent_required_behaviors": 0,
            "unresolved_verifier_mutations": 0,
            "unresolved_composition_failures": 0,
            "contaminated_promotion_evidence": 0,
            "resource_or_authority_violations": 0,
        },
        "terminal_predicates": {
            "exact_target_family_count_19": True,
            "every_required_behavior_contracted": True,
            "every_required_behavior_has_admissible_proof": True,
            "donor_dependent_required_behaviors_zero": True,
            "unexplained_required_behaviors_zero": True,
            "unresolved_verifier_mutations_zero": True,
            "unresolved_composition_failures_zero": True,
            "contaminated_evidence_used_for_promotion_zero": True,
            "resource_or_authority_violations_zero": True,
            "all_frozen_opus_acceptance_predicates_pass": False,
            "final_donor_deletion_cleanroom_pass": True,
            "proof_bundle_frozen": proof_bundle_frozen,
        },
    }


def _universal_proof() -> dict:
    return {
        "proof_kind": "SELECTED_COVER_COMPLEMENT_UNSAT",
        "scope_id": "S_TRACE_V1",
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "ABC_CLOSED_BY_SCOPE_COMPLETE_SELECTED_COVER",
        "observable_trace_scope_complete": True,
        "all_useful_target_behaviors_in_scope": True,
        "every_admission_sound": True,
        "residual_complement_unsat": True,
        "selected_cover_complete": True,
        "u_empty": True,
        "abc_closed": True,
        "all_credited_routes_brain_owned": True,
        "donor_independence_closed": True,
        "clean_room_replay_pass": True,
        "proof_artifact": {
            "path": "canonical/verification/UNIVERSAL_PROOF.json",
            "git_blob_sha": "1" * 40,
        },
        "verifier_receipt_artifact": {
            "path": "canonical/verification/UNIVERSAL_PROOF_INDEPENDENT.json",
            "git_blob_sha": "2" * 40,
        },
    }


def test_valid_universal_route_discharge_redundant_family_acceptance():
    verdict = mod.evaluate_manifest(_manifest(), _universal_proof())
    assert verdict["achieved"] is True
    assert verdict["acceptance_route"] == "UNIVERSAL_SCOPE_COMPLETE_PROOF"
    assert verdict["failed_predicates"] == []


def test_universal_route_cannot_bypass_common_proof_freeze():
    verdict = mod.evaluate_manifest(
        _manifest(proof_bundle_frozen=False),
        _universal_proof(),
    )
    assert verdict["achieved"] is False
    assert "PREDICATE_NOT_TRUE:proof_bundle_frozen" in verdict["failed_predicates"]


def test_invalid_universal_proof_does_not_bypass_open_families():
    proof = _universal_proof()
    proof["residual_complement_unsat"] = False
    verdict = mod.evaluate_manifest(_manifest(), proof)
    assert verdict["achieved"] is False
    assert any(x.startswith("FAMILY_OPEN:") for x in verdict["failed_predicates"])
    assert verdict["universal_proof"]["valid"] is False
