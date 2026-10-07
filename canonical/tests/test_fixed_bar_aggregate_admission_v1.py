from canonical.runtime.fixed_bar_aggregate_admission_v1 import (
    FROZEN_BARS,
    RECEIPT_SCHEMA,
    evaluate_atom,
    evaluate_receipt,
)


def _receipt(metric, unit, point, conservative, atoms):
    return {
        "schema": RECEIPT_SCHEMA,
        "measurement_id": "measurement-1",
        "metric": metric,
        "unit": unit,
        "brain_point_value": point,
        "brain_conservative_value": conservative,
        "gates": {
            "frozen_scope_bound": True,
            "scope_complete": True,
            "comparable_harness": True,
            "brain_owned_route": True,
            "contamination_safe": True,
            "predeclared_statistics": True,
            "independent_or_objective": True,
            "content_addressed_result": True,
        },
        "scope_bindings": {
            atom: {
                "verified": True,
                "independent_or_objective": True,
                "scope_relation": "EXACT",
                "source_path": "canonical/verification/scope.json",
                "source_sha": "abcdef123456",
            }
            for atom in atoms
        },
        "result_source_path": "canonical/verification/result.json",
        "result_source_sha": "123456abcdef",
    }


def test_exact_frozen_bar_passes():
    r = _receipt(
        "TERMINAL_BENCH_4_0_PERCENT",
        "percent",
        66.4,
        66.4,
        ["CODING_TB4_GE_66_4"],
    )
    assert evaluate_atom(r, "CODING_TB4_GE_66_4")["pass"] is True


def test_conservative_statistic_controls_admission():
    r = _receipt(
        "TERMINAL_BENCH_4_0_PERCENT",
        "percent",
        70.0,
        66.3,
        ["CODING_TB4_GE_66_4"],
    )
    out = evaluate_atom(r, "CODING_TB4_GE_66_4")
    assert out["pass"] is False
    assert "CONSERVATIVE_BAR_NOT_MET" in out["errors"]


def test_contamination_gate_fails_closed():
    r = _receipt(
        "HLE_WITH_TOOLS_PERCENT",
        "percent",
        80.0,
        75.0,
        ["HLE_TOOLS_GE_67_7"],
    )
    r["gates"]["contamination_safe"] = False
    out = evaluate_atom(r, "HLE_TOOLS_GE_67_7")
    assert out["pass"] is False
    assert "GATE_NOT_PROVED:contamination_safe" in out["errors"]


def test_shared_aa_briefcase_measurement_can_prove_two_atoms():
    atoms = ["PROWORK_AA_BRIEFCASE_GE_1822", "ARTIFACT_AA_BRIEFCASE_GE_1822"]
    r = _receipt("AA_BRIEFCASE_V1_1_ELO", "Elo", 1900.0, 1830.0, atoms)
    out = evaluate_receipt(r)
    assert out["pass"] is True
    assert set(out["proved_atoms"]) == set(atoms)


def test_scope_binding_is_required_per_atom():
    r = _receipt(
        "MYSTERYMECHANISM_PERCENT",
        "percent",
        60.0,
        55.0,
        ["MYSTERYMECHANISM_GE_49_55"],
    )
    r["scope_bindings"] = {}
    out = evaluate_atom(r, "MYSTERYMECHANISM_GE_49_55")
    assert out["pass"] is False
    assert "ATOM_SCOPE_BINDING_MISSING" in out["errors"]


def test_unknown_atom_fails_closed():
    out = evaluate_atom({}, "NOT_A_FROZEN_ATOM")
    assert out["pass"] is False
    assert out["errors"] == ["UNKNOWN_FIXED_BAR_ATOM"]


def test_frozen_map_has_exactly_fourteen_atoms():
    assert len(FROZEN_BARS) == 14
