from canonical.runtime.cursorbench_two_region_complement_nonidentifiability_v1 import (
    covered,
    verify,
)

T = ["t1", "t2"]
F = ["f1", "f2"]

def test_union_covered_when_typed_region_true():
    v = {"t1": True, "t2": True, "f1": False, "f2": False}
    assert covered(v, T, F) is True

def test_union_covered_when_finite_region_true():
    v = {"t1": False, "t2": False, "f1": True, "f2": True}
    assert covered(v, T, F) is True

def test_complement_when_each_region_has_a_false_atom():
    v = {"t1": False, "t2": True, "f1": False, "f2": True}
    assert covered(v, T, F) is False

def test_bound_current_evidence_does_not_identify_complement_emptiness():
    out = verify()
    assert out["pass"] is True, out
    assert out["typed_atom_count"] == 5
    assert out["finite_atom_count"] == 6
    assert out["world_cover_union_membership"] is True
    assert out["world_escape_union_membership"] is False
    assert out["current_evidence_identifies_complement_emptiness"] is False
    assert out["actual_complement_empty_claimed"] is False
    assert out["actual_complement_nonempty_claimed"] is False
    assert out["terminal_credit_delta"] == 0
