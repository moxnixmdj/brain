from canonical.runtime import livebench_union25_residual_basis_v1 as r


def test_union25_residual_basis():
    out = r.verify()
    assert out["status"] == "PASS__SYMBOLIC_EXTRA10_RESIDUAL_BASIS"
    assert out["active_count"] == 15
    assert out["union_count"] == 25
    assert out["extra_count"] == 10
    assert out["detector_mask_primitives"] == 4
    assert out["acceptance_credit"] is False


def test_exact_small_collision_coordinates():
    assert r.section_case_collision(r.LOW, "Section")
    assert r.section_case_collision(r.LOW, "SECTION")
    assert r.section_case_collision(r.UP, "Section")
    assert not r.section_case_collision(r.UP, "SECTION")
    assert r.forced_letter_floor("p", postscript="P.P.S") == 2
    assert r.forced_letter_floor("s", postscript="P.S.") == 1
