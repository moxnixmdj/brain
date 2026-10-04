from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_union25_case_section_interaction_v1 as c


def test_case_section_truth_table():
    assert c.forced_case_failure(u.ENGLISH_LOWERCASE,"Section")
    assert c.forced_case_failure(u.ENGLISH_LOWERCASE,"SECTION")
    assert c.forced_case_failure(u.ENGLISH_CAPITAL,"Section")
    assert not c.forced_case_failure(u.ENGLISH_CAPITAL,"SECTION")


def test_case_section_structural_exposure():
    out=c.verify()
    s=out["structural_exposure"]
    assert s["lowercase_plus_sections_sets"]==444
    assert s["capital_plus_sections_sets"]==444
    assert s["affected_hard_signatures_each"]==4


def test_active15_minimum_cut_needs_union25_extension():
    out=c.verify()
    q=out["slot_quotient"]["forced_case_checker_failure_if_section_checker_passes"]
    assert q[u.ENGLISH_LOWERCASE]=={"Section":True,"SECTION":True}
    assert q[u.ENGLISH_CAPITAL]=={"Section":True,"SECTION":False}
