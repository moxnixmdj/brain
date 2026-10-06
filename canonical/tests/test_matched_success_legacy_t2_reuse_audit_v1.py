from canonical.runtime.matched_success_legacy_t2_reuse_audit_v1 import evaluate


def test_current_legacy_t2_reuse_partition():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["normalized_dimension_count"] == 16
    assert out["reusable_substrate_dimension_count"] == 6
    assert out["integrated_extension_dimension_count"] == 10
    assert out["legacy_t2_unchanged_is_scope_superset"] is False
    assert out["fresh_reality_authority"] is False
