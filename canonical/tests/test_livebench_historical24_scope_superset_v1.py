from canonical.runtime import livebench_historical24_scope_superset_v1 as scope


def test_static_superset_theorem_closes_documentation_dependency():
    out = scope.verify_static_theorem()
    assert out["status"] == "PASS__CONSERVATIVE_HISTORICAL24_SCOPE_TARGET_DEFINED"
    assert out["paper_visible_livebench_id_count"] == 15
    assert out["paper_declared_livebench_id_count"] == 16
    assert out["paper_cardinality_consistent"] is False
    assert out["historical_generator_pool_count"] == 24
    assert out["pinned_registry_count"] == 25
    assert out["uncovered_generator_family_count"] == 9
    assert set(out["uncovered_generator_families"]) == {
        "keywords:frequency",
        "keywords:letter_frequency",
        "detectable_content:number_placeholders",
        "detectable_format:constrained_response",
        "detectable_format:number_highlighted_sections",
        "change_case:capital_word_frequency",
        "change_case:english_capital",
        "change_case:english_lowercase",
        "punctuation:no_comma",
    }


def test_generator_parser_recovers_pool_and_sampling_without_execution():
    source = """
def add_instructions_to_registry(no_of_instructions_to_add, max_instructions=5):
    a=["x:a", "x:b"]
    b=["x:c"]
    all_constraints = a + b
    samples_to_draw = np.random.randint(2, max_instructions+1, no_of_instructions_to_add)
    instruction_id_list_of_lists = []
    for draw in samples_to_draw:
        instruction_id_list_of_lists.append(
            np.random.choice(all_constraints, draw, replace=False).tolist()
        )
    return instruction_id_list_of_lists

def check_for_conflitcs(instruction_lists):
    deconflicted_instructions = []
    for instruction_set in instruction_lists:
        deconflicting_instruction_ = instruction_set.copy()
        deconflicting_instruction_.remove("x:a")
        deconflicted_instructions.append(list(set(deconflicting_instruction_)))
    return deconflicted_instructions
"""
    assert scope.parse_generator_pool(source) == ("x:a", "x:b", "x:c")
    assert scope.verify_sampling_shape(source) == {
        "draw_minimum": 2,
        "draw_maximum_default": 5,
        "without_replacement": True,
    }
    assert scope.verify_deconfliction_is_removal_only(source) is True


def test_deconfliction_addition_fails_closed():
    source = """
def check_for_conflitcs(instruction_lists):
    for instruction_set in instruction_lists:
        deconflicting_instruction_ = instruction_set.copy()
        deconflicting_instruction_.append("invented:id")
        deconflicting_instruction_.remove("x:a")
"""
    try:
        scope.verify_deconfliction_is_removal_only(source)
    except scope.ScopeProofError as exc:
        assert str(exc).startswith("DECONFLICT_CAN_ADD_IDS:")
    else:
        raise AssertionError("expected fail-closed mutation rejection")


def test_paper_visible15_is_exact_current_active15_runtime_surface():
    assert tuple(scope.PAPER_VISIBLE15) == tuple(scope.active15.ACTIVE_IDS)
    assert set(scope.PAPER_VISIBLE15) < set(scope.HISTORICAL24)
    assert set(scope.HISTORICAL24) < set(scope.REGISTRY25)
