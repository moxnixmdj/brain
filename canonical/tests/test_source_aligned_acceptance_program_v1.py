from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program
from canonical.runtime.typed_acceptance_program_v1 import verify


SCHEMA = {
    "score": {"type": "number", "dimension": "score"},
    "safe": {"type": "boolean", "dimension": "dimensionless"},
    "status": {"type": "enum", "dimension": "dimensionless"},
}


def test_multiple_controlled_requirements_compile_to_one_acceptance_program():
    text = 'score must be at least 10. safe must be true. status must equal "approved".'
    out = compile_program(text, source_id="task", field_schema=SCHEMA)
    assert out["status"] == "COMPILED", out
    verdict = verify(
        out["acceptance_program"],
        trusted_values={},
        candidate_values={"score": 12.0, "safe": True, "status": "approved"},
    )
    assert verdict["pass"] is True


def test_compiled_program_rejects_bad_candidate():
    text = "score must be at most 20. safe must be true."
    out = compile_program(text, source_id="task", field_schema=SCHEMA)
    verdict = verify(
        out["acceptance_program"],
        trusted_values={},
        candidate_values={"score": 25.0, "safe": True, "status": "anything"},
    )
    assert verdict["status"] == "FAIL_CLOSED" or verdict["pass"] is False


def test_unparsed_normative_sentence_blocks_compilation():
    text = "score must be at least 10. report must explain the strategic implications."
    out = compile_program(text, source_id="task", field_schema=SCHEMA)
    assert out["status"] == "UNRESOLVED"
    assert len(out["unresolved_normative_requirements"]) == 1


def test_non_normative_narrative_may_be_ignored():
    text = "This task concerns the quarterly review. score must be at least 10."
    out = compile_program(text, source_id="task", field_schema=SCHEMA)
    assert out["status"] == "COMPILED", out


def test_unknown_field_blocks_instead_of_guessing():
    out = compile_program(
        "quality must be at least 10.",
        source_id="task",
        field_schema=SCHEMA,
    )
    assert out["status"] == "UNRESOLVED"


def test_boolean_type_mismatch_blocks():
    out = compile_program(
        "score must be true.",
        source_id="task",
        field_schema=SCHEMA,
    )
    assert out["status"] == "UNRESOLVED"
