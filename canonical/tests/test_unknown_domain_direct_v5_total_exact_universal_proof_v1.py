from canonical.runtime import unknown_domain_direct_v5_total_exact_universal_proof_v1 as proof


def test_v5_total_exact_universal_composition():
    out = proof.prove()
    assert out["status"] == "PASS__V5_TOTAL_STRING_STRUCTURAL_IDS_EXACT_FLOAT_UNIVERSAL_COMPOSITION"
    assert out["string_interface_totality"]["surrogate_codepoints_exhausted"] == 2048
    assert out["string_interface_totality"]["beacon_canonicalization_total"] is True
    assert out["string_interface_totality"]["beacon_canonicalization_injective"] is True
    assert out["composition_proof"]["all_six_transfer_families_universal"] is True
    assert out["composition_proof"]["add2_exact_float_order_repaired"] is True
    assert out["composition_proof"]["all_three_abstention_classes_universal"] is True
    assert out["scope"]["terminal_or_production_cases_generated"] == 0
    assert out["accounting"]["acceptance_credit_delta"] == 0


def test_v5_composition_discharge_set_is_exactly_the_three_known_holes():
    out = proof.prove()
    assert set(out["discharges_known_revocation_holes"]) == {
        "ADD2_EXACT_IEEE754_ROLE_ORDER",
        "EVALUATOR_VISIBLE_IDENTIFIER_COLLISIONS",
        "ACCEPTED_PYTHON_STRING_STRICT_UTF8_PARTIALITY",
    }
