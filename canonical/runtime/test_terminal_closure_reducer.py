from copy import deepcopy

from canonical.runtime.terminal_closure_reducer import evaluate_manifest


def passing_manifest():
    families = [
        {"id": f"FAMILY_{i:02d}", "closure_state": "PASS"}
        for i in range(19)
    ]
    counters = {
        "uncontracted_required_behaviors": 0,
        "unproved_required_behaviors": 0,
        "donor_dependent_required_behaviors": 0,
        "unresolved_verifier_mutations": 0,
        "unresolved_composition_failures": 0,
        "contaminated_promotion_evidence": 0,
        "resource_or_authority_violations": 0,
    }
    predicates = {
        "exact_target_family_count_19": True,
        "every_required_behavior_contracted": True,
        "every_required_behavior_has_admissible_proof": True,
        "donor_dependent_required_behaviors_zero": True,
        "unexplained_required_behaviors_zero": True,
        "unresolved_verifier_mutations_zero": True,
        "unresolved_composition_failures_zero": True,
        "contaminated_evidence_used_for_promotion_zero": True,
        "resource_or_authority_violations_zero": True,
        "all_frozen_opus_acceptance_predicates_pass": True,
        "final_donor_deletion_cleanroom_pass": True,
        "proof_bundle_frozen": True,
    }
    return {
        "expected_family_count": 19,
        "actual_family_count": 19,
        "families": families,
        "counters": counters,
        "terminal_predicates": predicates,
    }


def test_exact_complete_manifest_passes():
    out = evaluate_manifest(passing_manifest())
    assert out["achieved"] is True
    assert out["failed_predicates"] == []


def test_open_family_fails_closed():
    m = passing_manifest()
    m["families"][7]["closure_state"] = "OPEN"
    out = evaluate_manifest(m)
    assert out["achieved"] is False
    assert "FAMILY_OPEN:FAMILY_07" in out["failed_predicates"]


def test_missing_family_fails_closed():
    m = passing_manifest()
    m["families"].pop()
    m["actual_family_count"] = 18
    out = evaluate_manifest(m)
    assert out["achieved"] is False
    assert "ACTUAL_FAMILY_COUNT:18" in out["failed_predicates"]


def test_unknown_counter_fails_closed():
    m = passing_manifest()
    m["counters"]["unproved_required_behaviors"] = None
    out = evaluate_manifest(m)
    assert out["achieved"] is False
    assert "COUNTER_UNKNOWN_OR_NONINTEGER:unproved_required_behaviors" in out["failed_predicates"]


def test_contaminated_promotion_evidence_fails():
    m = passing_manifest()
    m["counters"]["contaminated_promotion_evidence"] = 1
    m["terminal_predicates"]["contaminated_evidence_used_for_promotion_zero"] = False
    out = evaluate_manifest(m)
    assert out["achieved"] is False
    assert "COUNTER_NONZERO:contaminated_promotion_evidence:1" in out["failed_predicates"]


def test_handwritten_true_cannot_hide_nonzero_counter():
    m = passing_manifest()
    m["counters"]["donor_dependent_required_behaviors"] = 2
    # Deliberately leave predicate true to simulate dishonest/stale state.
    out = evaluate_manifest(m)
    assert out["achieved"] is False
    assert any(
        x.startswith("COUNTER_PREDICATE_CONTRADICTION:donor_dependent_required_behaviors")
        for x in out["failed_predicates"]
    )


def test_duplicate_family_id_fails():
    m = passing_manifest()
    m["families"][18]["id"] = m["families"][0]["id"]
    out = evaluate_manifest(m)
    assert out["achieved"] is False
    assert "DUPLICATE_FAMILY_ID" in out["failed_predicates"]
