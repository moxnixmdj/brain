#!/usr/bin/env python3
import pytest

from canonical.runtime.livebench_if_score_only_semantic_elision_v1 import (
    SemanticElisionError,
    bridge,
)

def _structural():
    return {
        "status": "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED",
        "response": "structural witness",
        "semantic_seed_required": True,
    }

def test_semantic_seed_deleted_only_after_both_stronger_gates():
    out = bridge(
        _structural(),
        all_score_relevant_constraints_recognized=True,
        exact_checker_postvalidation_pass=True,
    )
    assert out["status"] == "PASS__SCORE_ONLY_STRUCTURAL_WITNESS"
    assert out["response"] == "structural witness"
    assert out["semantic_seed_required"] is False
    assert out["semantic_quality_claimed"] is False

def test_incomplete_constraint_coverage_fails_closed():
    with pytest.raises(SemanticElisionError, match="COVERAGE_NOT_PROVED"):
        bridge(
            _structural(),
            all_score_relevant_constraints_recognized=False,
            exact_checker_postvalidation_pass=True,
        )

def test_exact_checker_failure_fails_closed():
    with pytest.raises(SemanticElisionError, match="POSTVALIDATION_NOT_PROVED"):
        bridge(
            _structural(),
            all_score_relevant_constraints_recognized=True,
            exact_checker_postvalidation_pass=False,
        )

def test_blocked_compiler_cannot_be_promoted():
    with pytest.raises(SemanticElisionError, match="STATUS_NOT_STRUCTURALLY_ADMISSIBLE"):
        bridge(
            {"status": "BLOCKED", "response": "x"},
            all_score_relevant_constraints_recognized=True,
            exact_checker_postvalidation_pass=True,
        )
