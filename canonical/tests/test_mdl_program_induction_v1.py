from canonical.runtime.mdl_program_induction_v1 import (
    Primitive,
    compile_program,
    synthesize,
    verify,
)


def test_learns_integer_composition_without_learned_state():
    primitives = [
        Primitive("ADD_1", 1, lambda x: x + 1),
        Primitive("DOUBLE", 1, lambda x: x * 2),
        Primitive("NEGATE", 1, lambda x: -x),
    ]
    result = synthesize(
        examples=[(1, 3), (2, 5), (5, 11)],
        primitives=primitives,
        max_description_length=3,
    )
    assert result["status"] == "EXACT_PROGRAM_FOUND"
    assert result["program"] == ["DOUBLE", "ADD_1"]
    assert result["description_length"] == 2
    assert result["persistent_learned_state_bytes"] == 0
    assert result["frontier_or_external_model_required"] is False

    heldout = verify(
        program=result["program"],
        examples=[(7, 15), (10, 21)],
        primitives=primitives,
    )
    assert heldout["pass"] is True


def test_learns_string_transform_in_same_generic_kernel():
    primitives = [
        Primitive("REVERSE", 1, lambda x: x[::-1]),
        Primitive("UPPER", 1, lambda x: x.upper()),
        Primitive("DUPLICATE", 2, lambda x: x + x),
    ]
    result = synthesize(
        examples=[("ab", "BA"), ("cat", "TAC"), ("xy", "YX")],
        primitives=primitives,
        max_description_length=3,
    )
    assert result["status"] == "EXACT_PROGRAM_FOUND"
    assert result["program"] in (["REVERSE", "UPPER"], ["UPPER", "REVERSE"])
    assert result["description_length"] == 2

    heldout = verify(
        program=result["program"],
        examples=[("brain", "NIARB")],
        primitives=primitives,
    )
    assert heldout["pass"] is True


def test_returns_no_solution_when_declared_search_space_cannot_express_target():
    primitives = [
        Primitive("ADD_1", 1, lambda x: x + 1),
        Primitive("DOUBLE", 1, lambda x: x * 2),
    ]
    result = synthesize(
        examples=[(2, 4), (3, 9), (4, 16)],
        primitives=primitives,
        max_description_length=4,
    )
    assert result["status"] == "NO_EXACT_PROGRAM_WITHIN_DECLARED_SEARCH"
    assert result["program"] is None
    assert result["persistent_learned_state_bytes"] == 0


def test_compiled_solution_is_explicit_deterministic_program():
    primitives = [
        Primitive("ADD_1", 1, lambda x: x + 1),
        Primitive("DOUBLE", 1, lambda x: x * 2),
    ]
    compiled = compile_program(
        program=["DOUBLE", "ADD_1"],
        primitives=primitives,
    )
    assert compiled["description_length"] == 2
    assert compiled["persistent_learned_state_bytes"] == 0
    assert compiled["requires_retraining_for_reuse"] is False


def test_semantic_dedup_prunes_equivalent_paths():
    primitives = [
        Primitive("ADD_0", 1, lambda x: x),
        Primitive("ADD_1", 1, lambda x: x + 1),
        Primitive("DOUBLE", 1, lambda x: x * 2),
    ]
    result = synthesize(
        examples=[(1, 5), (2, 7)],
        primitives=primitives,
        max_description_length=4,
    )
    assert result["status"] == "EXACT_PROGRAM_FOUND"
    assert result["program"] == ["DOUBLE", "ADD_1", "ADD_1", "ADD_1"]
    assert result["semantic_states_pruned"] > 0
