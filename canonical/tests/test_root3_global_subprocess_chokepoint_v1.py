from __future__ import annotations

from canonical.runtime.root3_global_subprocess_chokepoint_v1 import audit


def test_current_direct_process_mediation_cut_is_two_global_attributes():
    out = audit()
    assert out["direct_process_call_site_count"] == 29
    assert out["api_counts"] == {
        "subprocess.run": 27,
        "subprocess.Popen": 2,
    }
    assert out["aliased_or_from_import_count"] == 0
    assert out["local_or_dynamic_rebinding_count"] == 0
    assert out["registry_enumeration_exact_match"] is True
    assert out["minimum_direct_python_mediation_chokepoints"] == [
        "subprocess.run",
        "subprocess.Popen",
    ]


def test_audit_does_not_overclaim_child_internal_effect_control():
    out = audit()
    assert any(
        "INSIDE AN ALREADY STARTED CHILD" in x
        for x in out["hard_nonclaims"]
    )
    assert "PROVE_CHILD_PROGRAM_INTERNAL_EFFECTS_ARE_SANDBOXED_OR_SEPARATELY_MEDIATED" in out["remaining_after_two_chokepoints"]
