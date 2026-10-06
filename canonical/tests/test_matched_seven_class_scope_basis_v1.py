from canonical.runtime.matched_seven_class_scope_basis_v1 import verify_basis

def test_seven_class_basis_is_exact():
    out = verify_basis()
    assert out["pass"] is True, out
    assert out["class_count"] == 7
    assert out["scope_atom_count"] == 16
    assert out["v4_integrated_atom_count"] == 10
    assert out["legacy_extension_atom_count"] == 6
    assert out["separate_legacy_case_class_required"] is False

def test_only_two_classes_absorb_legacy_dimensions():
    out = verify_basis()
    assert set(out["legacy_extension_classes"]) == {
        "AGENCY_THREE_TOOL_LONG_HORIZON",
        "INSTRUCTION_CHANGE_CONTROL",
    }
