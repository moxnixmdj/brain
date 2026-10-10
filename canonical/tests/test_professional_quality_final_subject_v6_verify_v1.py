from canonical.runtime.professional_quality_final_subject_v6_verify_v1 import verify


def test_final_p1_v6_subject_is_transitively_dependency_closed():
    out = verify()
    assert out["pass"] is True, out
    assert out["status"] == "PASS__FINAL_P1_V6_SUBJECT_TRANSITIVE_DEPENDENCY_CLOSED"
    assert out["subject_component_count"] == 20
    assert out["missing_runtime_components"] == []
    assert out["missing_governance_components"] == []
    assert out["canonical_v2_missing_components_added"] is True
    assert out["p1_v6_minimal_binding_kernel_added"] is True
    assert out["broad_general_r2_controller_in_subject"] is False
    assert out["root_subject_binding_authority"] is False
    assert out["quality_authority"] is False
    assert out["terminal_authority"] is False
