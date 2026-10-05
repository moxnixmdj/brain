#!/usr/bin/env python3
import pathlib
import tempfile

import pytest

from canonical.runtime import goal_compiler


def compile_exact(goal):
    with tempfile.TemporaryDirectory() as td:
        return goal_compiler.compile_goal(goal, {}, pathlib.Path(td))


def test_unquoted_exact_literal_routes_directly_to_finish():
    out=compile_exact("Reply with exactly SYNTHETIC_OK.")
    assert out["compiler_mode"]=="DETERMINISTIC_EXACT_LITERAL_RESPONSE"
    assert out["controller_actions"]==[
        {"type":"finish","args":{"summary":"SYNTHETIC_OK."}}
    ]
    assert out["clause_coverage_verified"] is True


def test_quoted_exact_literal_drops_instruction_punctuation_only():
    out=compile_exact('Respond exactly "alpha beta".')
    assert out["controller_actions"][0]["args"]["summary"]=="alpha beta"


@pytest.mark.parametrize("verb",["reply","respond","answer","output","write","say"])
def test_supported_general_exact_output_verbs(verb):
    out=compile_exact(f"{verb} exactly cedar")
    assert out["controller_actions"][0]["args"]["summary"]=="cedar"


def test_extra_semantic_clause_is_not_miscompiled_as_literal():
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(goal_compiler.GoalCompilationFailure) as exc:
            goal_compiler.compile_goal(
                "Explain cedar trees and reply with exactly OK.",
                {},
                pathlib.Path(td),
            )
    assert exc.value.code=="GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"


def test_empty_quoted_literal_is_not_accepted():
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(goal_compiler.GoalCompilationFailure):
            goal_compiler.compile_goal('Reply with exactly "".', {}, pathlib.Path(td))


def test_route_has_no_benchmark_specific_identifier():
    source=pathlib.Path(goal_compiler.__file__).read_text(encoding="utf-8")
    helper=source[source.index("def _compile_exact_literal_response_goal"):source.index("def _compile_verified_browser_interaction")]
    assert "LIVEBENCH" not in helper.upper()
    assert "SYNTHETIC_OK" not in helper
