from canonical.runtime.terminal_reality_gate_v1 import (
    MANDATORY_ROOT,
    MANDATORY_SEMANTICS,
    evaluate,
)


FAMILIES = [f"F{i:02d}" for i in range(19)]


def pointer(*, terminal=False, semantics=MANDATORY_SEMANTICS, universal_required=False):
    return {
        "live_truth": {
            "terminal_root_semantics": semantics,
            "universal_trace_not_x_required_for_terminal": universal_required,
            "primary_terminal_scheduler_object": MANDATORY_ROOT,
            "terminal": terminal,
            "current_U_empty_proved": False,
            "router_registry_real_selected_cover_complete": False,
            "complete_selected_context_ABC_closed": False,
            "D_finality_closed": False,
            "frozen_terminal_family_pass_count": 19,
            "frozen_terminal_family_open_count": 0,
        }
    }


def manifest(*, open_family=None):
    rows = []
    for fid in FAMILIES:
        if fid == open_family:
            rows.append(
                {
                    "id": fid,
                    "closure_state": "OPUS55_ACCEPTANCE_OPEN",
                    "opus55_acceptance_state": "OPEN",
                    "opus55_acceptance_calibrated": False,
                    "ownership_status": "OPEN",
                    "unresolved": ["OPUS55_ACCEPTANCE_PROTOCOL_RESULT_OPEN"],
                }
            )
        else:
            rows.append(
                {
                    "id": fid,
                    "closure_state": "PASS",
                    "opus55_acceptance_state": "PASS",
                    "opus55_acceptance_calibrated": True,
                    "ownership_status": "VERIFIED_OWNED_EQUAL_OR_BETTER",
                    "unresolved": [],
                }
            )
    all_closed = open_family is None
    return {
        "expected_family_count": 19,
        "actual_family_count": 19,
        "families": rows,
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
            "all_frozen_opus_acceptance_predicates_pass": all_closed,
            "final_donor_deletion_cleanroom_pass": True,
            "proof_bundle_frozen": all_closed,
        },
    }


def test_full_frozen_protocol_and_ownership_manifest_is_terminal_even_when_optional_u_is_open():
    out = evaluate(pointer(terminal=True), manifest())
    assert out["terminal_real"] is True
    assert out["blockers"] == []
    assert out["accepted_family_count"] == 19
    assert out["verified_owned_family_count"] == 19
    assert out["optional_stronger_trace_route"]["current_U_empty_proved"] is False


def test_one_open_family_reduces_to_one_mandatory_aggregate_root():
    out = evaluate(pointer(), manifest(open_family="F07"))
    assert out["terminal_real"] is False
    assert out["blockers"] == [MANDATORY_ROOT]
    assert out["live_research_blockers"] == [MANDATORY_ROOT]
    assert "FAMILY_OPEN:F07" in out["closure_failed_predicates"]


def test_universal_trace_route_cannot_be_repromoted_to_mandatory():
    out = evaluate(pointer(universal_required=True), manifest())
    assert out["terminal_real"] is False
    assert "OPTIONAL_UNIVERSAL_TRACE_ROUTE_REPROMOTED_TO_MANDATORY" in out["blockers"]


def test_terminal_semantics_drift_fails_closed():
    out = evaluate(pointer(semantics="UNIVERSAL_TRACE_NOT_X"), manifest())
    assert out["terminal_real"] is False
    assert "MANDATORY_TERMINAL_ROOT_SEMANTICS_DRIFT" in out["blockers"]


def test_false_positive_manual_terminal_declaration_fails_closed():
    out = evaluate(pointer(terminal=True), manifest(open_family="F03"))
    assert out["terminal_real"] is False
    assert (
        "DECLARED_TERMINAL_INCONSISTENT_WITH_FROZEN_PROTOCOL_AND_OWNERSHIP_GATE"
        in out["blockers"]
    )


def test_false_manual_terminal_flag_is_only_metadata_when_exact_gate_is_true():
    out = evaluate(pointer(terminal=False), manifest())
    assert out["terminal_real"] is True
    assert out["blockers"] == []
    assert any("METADATA_OUT_OF_SYNC" in x for x in out["declaration_warnings"])
