from canonical.runtime import livebench_historical24_composition_space_v1 as space
from canonical.runtime import livebench_historical24_special_pointwise_v1 as special


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots, "parameter_complete": True}


def build(ids, *, comma_repeat=False):
    out = []
    for iid in ids:
        if iid == "keywords:existence":
            out.append(c(iid, keywords=["alpha", "beta"]))
        elif iid == "keywords:forbidden_words":
            out.append(c(iid, forbidden_words=["gamma", "delta"]))
        elif iid == "combination:repeat_prompt":
            prefix = "Write a compact note, please." if comma_repeat else "Write a compact note."
            out.append(c(iid, prompt_to_repeat=prefix))
        else:
            out.append(c(iid))
    return out


def test_every_special_structural_set_constructs():
    sets = [
        ids
        for ids in space.enumerate_compatible_sets()
        if space.route(ids) != "GENERAL"
    ]
    assert len(sets) == 29
    for ids in sets:
        out = special.solve_special(build(ids, comma_repeat=False))
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_ROUTE", (
            ids,
            out,
        )
        assert out["theoretical_max_pass_count"] == len(ids)
        assert out["sacrificed_instruction_ids"] == []


def test_repeat_no_comma_collision_has_exact_one_checker_loss():
    repeat_sets = [
        ids
        for ids in space.enumerate_compatible_sets()
        if space.route(ids) == "REPEAT_PROMPT"
        and "punctuation:no_comma" in ids
    ]
    assert len(repeat_sets) == 4
    for ids in repeat_sets:
        out = special.solve_special(build(ids, comma_repeat=True))
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_ROUTE"
        assert out["sacrificed_instruction_ids"] == [
            "combination:repeat_prompt"
        ]
        assert out["theoretical_max_pass_count"] == len(ids) - 1
        assert "," not in out["response"]
        if "detectable_format:title" in ids:
            assert "<<safe>>" in out["response"]
        if "keywords:existence" in ids:
            assert "alpha" in out["response"]
            assert "beta" in out["response"]


def test_two_response_no_comma_extension_is_constructively_full_score():
    ids = (
        "keywords:existence",
        "keywords:forbidden_words",
        "detectable_format:title",
        "combination:two_responses",
        "punctuation:no_comma",
    )
    assert space.compatible(ids)
    out = special.solve_special(build(ids))
    assert out["theoretical_max_pass_count"] == 5
    assert "******" in out["response"]
    assert "," not in out["response"]


def test_general_route_fails_closed():
    out = special.solve_special([c("punctuation:no_comma")])
    assert out["status"] == "FAIL_CLOSED"
    assert "GENERAL_ROUTE_NOT_IN_SPECIAL_SOLVER" in out["error"]
