from canonical.runtime import livebench_union25_interaction_topology_v1 as t


def test_exact_union25_structural_quotient():
    out=t.verify()
    s=out["structural"]
    assert s["families"]==25
    assert s["conflict_pairs"]==97
    assert s["sets"]==14559
    assert s["by_size"]=={1:25,2:203,3:1055,4:3750,5:9526}
    assert s["active15_only"]==928
    assert s["with_extra"]==13631
    assert s["extra_subsets"]==156


def test_special_branches_do_not_expand_blindly():
    out=t.verify()["structural"]
    assert out["constrained_sets"]==1
    assert out["json_sets"]==4
    assert out["repeat_sets"]==8
    assert out["repeat_no_comma_sets"]==4


def test_repeat_prompt_arbitrary_text_collapses_to_comma_bit():
    assert not t.repeat_comma_forces_loss("copy this exactly")
    assert t.repeat_comma_forces_loss("copy this, exactly")
    assert t.repeat_comma_forces_loss(",")


def test_case_section_splitter_loss_truth_table():
    assert t.case_section_forces_case_loss(t.LOWER,"Section")
    assert t.case_section_forces_case_loss(t.LOWER,"SECTION")
    assert t.case_section_forces_case_loss(t.CAPITAL,"Section")
    assert not t.case_section_forces_case_loss(t.CAPITAL,"SECTION")


def test_case_section_interactions_are_registry_compatible_and_load_bearing():
    rows=t.structural_sets()
    assert sum(t.LOWER in r and t.SECTIONS in r for r in rows)==444
    assert sum(t.CAPITAL in r and t.SECTIONS in r for r in rows)==444
