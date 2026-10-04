from canonical.runtime import livebench_union25_easy_extension_v1 as e
from canonical.runtime import livebench_union25_archetypes_v1 as u


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_exact_easy_layer_reduction_counts():
    out = e.verify()
    assert out["easy_extra_signature_count"] == 8
    assert out["easy_extra_structure_count"] == 2058
    assert out["zero_new_mandatory_loss_structure_count"] == 2054
    assert out["repeat_prompt_no_comma_structure_count"] == 4


def test_constrained_singleton_direct_witness():
    out = e.extend_post_sacrifice_contracts([c(u.CONSTRAINED)])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"] == "My answer is yes."


def test_placeholder_and_highlight_are_inserted_without_comma():
    out = e.extend_post_sacrifice_contracts([
        c(u.PLACEHOLDERS, num_placeholders=4),
        c(u.HIGHLIGHTS, num_highlights=4),
        c(u.NO_COMMA),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"].count("[0]") == 4
    assert out["response"].count("*0*") == 4
    assert "," not in out["response"]


def test_repeat_no_comma_visible_conflict_is_exactly_one_loss():
    out = e.extend_post_sacrifice_contracts([
        c(u.REPEAT, prompt_to_repeat="Please explain this, exactly."),
        c(u.NO_COMMA),
    ])
    assert out["status"] == "PROVED_ONE_NEW_MANDATORY_LOSS"
    loss = out["new_mandatory_losses"]
    assert len(loss) == 1
    assert set(loss[0]["conflicting_ids"]) == {u.REPEAT, u.NO_COMMA}


def test_repeat_without_comma_keeps_both_checkers_satisfiable():
    out = e.extend_post_sacrifice_contracts([
        c(u.REPEAT, prompt_to_repeat="Please explain this exactly."),
        c(u.NO_COMMA),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"].lower().startswith("please explain this exactly.")
    assert "," not in out["response"]
