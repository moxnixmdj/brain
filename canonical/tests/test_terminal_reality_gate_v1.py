from canonical.runtime.terminal_reality_gate_v1 import evaluate


def manifest(*, accepted=19, owned=19, unresolved_atoms=0, clean=True, frozen=True):
    pending = 19 - accepted
    families = []
    for i in range(19):
        closed = i < owned and i < accepted
        families.append({
            "id": f"F{i}",
            "closure_state": "PASS" if closed else "OPEN",
        })
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
            "all_frozen_opus_acceptance_predicates_pass": pending == 0,
            "final_donor_deletion_cleanroom_pass": clean,
            "proof_bundle_frozen": frozen,
        },
        "opus55_acceptance_summary": {
            "calibrated_family_count": accepted,
            "pending_family_count": pending,
            "atomic_predicates": {
                "proved": 38 - unresolved_atoms,
                "unresolved": unresolved_atoms,
                "total": 38,
            },
        },
        "ownership_summary": {
            "verified_owned_families": owned,
            "total_families": 19,
        },
    }


def test_gate_passes_only_on_full_frozen_terminal_contract():
    out = evaluate(manifest())
    assert out["terminal_real"] is True
    assert out["phase"] == "TERMINAL"
    assert out["blockers"] == []


def test_acceptance_open_is_primary_phase():
    out = evaluate(manifest(accepted=6, owned=5, unresolved_atoms=22, frozen=False))
    assert out["terminal_real"] is False
    assert out["phase"] == "FROZEN_ACCEPTANCE_CLOSURE"
    assert "FROZEN_ACCEPTANCE_FAMILIES_OPEN:13" in out["blockers"]
    assert "FROZEN_ACCEPTANCE_ATOMS_OPEN:22" in out["blockers"]
    assert "VERIFIED_OWNERSHIP_FAMILIES_OPEN:14" in out["blockers"]
    assert "PROOF_BUNDLE_NOT_FROZEN" in out["blockers"]


def test_acceptance_closed_but_ownership_open_moves_to_ownership_finality():
    out = evaluate(manifest(accepted=19, owned=17, unresolved_atoms=0, frozen=False))
    assert out["terminal_real"] is False
    assert out["phase"] == "OWNERSHIP_FINALITY"
    assert out["blockers"] == [
        "VERIFIED_OWNERSHIP_FAMILIES_OPEN:2",
        "PROOF_BUNDLE_NOT_FROZEN",
    ]


def test_final_bundle_open_is_final_reduction_not_research_root():
    out = evaluate(manifest(accepted=19, owned=19, unresolved_atoms=0, frozen=False))
    assert out["terminal_real"] is False
    assert out["phase"] == "FINAL_TERMINAL_REDUCTION"
    assert out["blockers"] == ["PROOF_BUNDLE_NOT_FROZEN"]


def test_universal_trace_shortcut_is_not_a_mandatory_terminal_predicate():
    out = evaluate(manifest())
    assert out["anti_bureaucracy"][
        "universal_trace_not_x_is_optional_stronger_route_not_mandatory"
    ] is True
    assert all("U_" not in x for x in out["blockers"])


def test_false_family_closure_cannot_be_hidden_by_summary_counts():
    m = manifest()
    m["families"][0]["closure_state"] = "OPEN"
    out = evaluate(m)
    assert out["terminal_real"] is False
    assert any(x == "FAMILY_OPEN:F0" for x in out["failed_predicates"])
