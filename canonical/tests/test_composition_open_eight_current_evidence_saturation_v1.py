from canonical.runtime.composition_open_eight_current_evidence_saturation_v1 import evaluate

def test_current_authoritative_surface_has_zero_new_composition_receipts():
    out=evaluate()
    assert out["pass"] is True, out
    assert out["current_scoped_proved"] == 4
    assert out["current_open"] == 8
    assert out["newly_admissible_receipts"] == []
    assert out["newly_closed_components"] == []
    assert out["slicer_rerun_useful"] is False
    assert out["bounded_surface_only"] is True
    assert out["global_nonexistence_claim"] is False
    assert out["new_reality_units_consumed"] == 0
    assert out["acceptance_credit_delta"] == 0

def test_all_eight_open_components_get_exact_next_missing_condition():
    out=evaluate()
    expected={
      "research",
      "tool use",
      "artifact creation",
      "browser/computer action",
      "coding",
      "debugging",
      "evidence synthesis",
      "artifact production",
    }
    assert set(out["open_components_after_audit"]) == expected
    assert set(out["minimum_missing_conditions"]) == expected
    assert all(out["minimum_missing_conditions"][x] for x in expected)
