from canonical.runtime.livebench_legacy_visible_constraint_compiler_v2 import (
    compile_visible_constraints,
    source_surface,
)


REPEAT = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)


def by_id(out, iid):
    xs = [x for x in out["constraints"] if x["instruction_id"] == iid]
    assert len(xs) == 1, (iid, out)
    return xs[0]


def test_source_surface_closes_all_25_parameter_types_under_generator_contract():
    s = source_surface()
    assert s["recognized_public_type_count"] == 25
    assert s["registered_legacy_type_count"] == 25
    assert s["all_registered_types_covered_by_recognizers"] is True
    assert s["fully_visible_parameter_type_count_under_historical_generator"] == 25
    assert s["parameter_incomplete_type_count_under_historical_generator"] == 0


def test_repeat_prompt_is_exactly_visible_prefix_as_historical_generator_sets_it():
    prefix = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\narticle text\n-------\n"
        "Please summarize based on the sentences provided. "
        "Include keywords ['alpha', 'beta'] in the response."
    )
    prompt = prefix + " " + REPEAT + " Wrap your entire response with double quotation marks."
    out = compile_visible_constraints(prompt)
    repeat = by_id(out, "combination:repeat_prompt")
    assert repeat["parameter_complete"] is True
    assert repeat["unresolved_parameters"] == []
    assert repeat["slots"]["prompt_to_repeat"] == prefix
    assert out["all_recognized_parameters_complete"] is True


def test_postscript_marker_does_not_swallow_following_constraint():
    prompt = (
        "At the end of your response, please explicitly add a postscript starting with P.P.S "
        "Include keywords ['alpha', 'beta'] in the response."
    )
    out = compile_visible_constraints(prompt)
    post = by_id(out, "detectable_content:postscript")
    assert post["slots"] == {"postscript_marker": "P.P.S"}
    kw = by_id(out, "keywords:existence")
    assert kw["slots"]["keywords"] == ["alpha", "beta"]


def test_postscript_ps_period_variant():
    prompt = (
        "At the end of your response, please explicitly add a postscript starting with P.S. "
        "Wrap your entire response with double quotation marks."
    )
    out = compile_visible_constraints(prompt)
    post = by_id(out, "detectable_content:postscript")
    assert post["slots"]["postscript_marker"] == "P.S."


def test_no_hidden_or_terminal_inputs_are_claimed():
    out = compile_visible_constraints(
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    )
    assert out["hidden_instruction_ids_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["terminal_case_metadata_used"] is False
    assert out["terminal_case_content_used"] is False
    assert out["model_dependency_count"] == 0
