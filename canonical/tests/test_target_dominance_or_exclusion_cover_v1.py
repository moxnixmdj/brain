from canonical.runtime.target_dominance_or_exclusion_cover_v1 import (
    CoverError, certify, exclusion_needed_for_fixed_d, cover_suffices_without_exact_target_identity
)

def test_complete_mixed_cover_certifies():
    out=certify(target={"a","c"},superdomain={"a","b","c"},dominated={"a","c"},excluded={"b"})
    assert out.certified
    assert out.unresolved==()

def test_target_in_excluded_cell_fails():
    out=certify(target={"a","b"},superdomain={"a","b"},dominated={"a"},excluded={"b"})
    assert not out.certified
    assert not out.target_excluded_from_x

def test_unresolved_region_fails_closed():
    out=certify(target={"a"},superdomain={"a","b","c"},dominated={"a"},excluded={"b"})
    assert not out.certified
    assert out.unresolved==("c",)

def test_fixed_d_escape_is_exact_complement():
    assert exclusion_needed_for_fixed_d(superdomain={"a","b","c"},dominated={"a","c"})=={"b"}

def test_exact_target_identity_not_needed_for_cover_shape():
    assert cover_suffices_without_exact_target_identity(
        superdomain={"a","b","c"},dominated={"a","c"},excluded_from_target={"b"}
    )

def test_bad_superdomain_fails_closed():
    try:
        certify(target={"z"},superdomain={"a"},dominated={"a"},excluded=set())
    except CoverError as e:
        assert str(e)=="TARGET_NOT_SUBSET_OF_SUPERDOMAIN"
    else:
        raise AssertionError("expected failure")
