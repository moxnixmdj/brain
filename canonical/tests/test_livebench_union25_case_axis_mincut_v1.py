from canonical.runtime import livebench_union25_case_axis_mincut_v1 as c
from canonical.runtime import livebench_union25_archetypes_v1 as u


def test_case_section_exact_mincuts():
    out = c.verify()
    m = out["section_slot_matrix"]
    assert m[u.ENGLISH_CAPITAL]["SECTION"]["maximum_passes_of_two"] == 2
    assert m[u.ENGLISH_CAPITAL]["Section"]["maximum_passes_of_two"] == 1
    assert m[u.ENGLISH_LOWERCASE]["SECTION"]["maximum_passes_of_two"] == 1
    assert m[u.ENGLISH_LOWERCASE]["Section"]["maximum_passes_of_two"] == 1


def test_transform_carrier():
    assert c.transform_witness(u.ENGLISH_CAPITAL, "Ab c?") == "AB C?"
    assert c.transform_witness(u.ENGLISH_LOWERCASE, "Ab C?") == "ab c?"


def test_only_sections_removed_from_active15_preservation_set():
    assert c.CASE_TRANSFORM_PRESERVED_ACTIVE15 == frozenset(u.ACTIVE15 - {u.SECTIONS})
