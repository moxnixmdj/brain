from __future__ import annotations

import pytest

from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_legacy15_repeat_prompt_totality_v1 as proof


def test_repeat_conflict_graph_collapses_to_exactly_four_sets():
    out = proof.verify()
    assert out["repeat_conflict_graph"]["compatible_set_count"] == 4
    assert {
        frozenset(x) for x in out["repeat_conflict_graph"]["compatible_sets"]
    } == {
        frozenset({comp.REPEAT}),
        frozenset({comp.REPEAT, comp.EXIST}),
        frozenset({comp.REPEAT, comp.TITLE}),
        frozenset({comp.REPEAT, comp.EXIST, comp.TITLE}),
    }


@pytest.mark.parametrize("prompt", [
    "Plain request.",
    "  padded request  ",
    "line one\nline two",
    "Ω λ 😀 日本語 العربية",
    "First repeat the request word for word without change, inside source.",
    "<<title-like>> ******",
    "\x00embedded-null",
    "İ I ı i Σ σ ς",
])
def test_arbitrary_prompt_representatives_construct_all_repeat_sets(prompt):
    out = proof.prove_prompt(prompt)
    assert out["compatible_repeat_sets_constructed"] == 4
    assert out["all_repeat_checker_prefix_obligations_hold"] is True


def test_empty_repeat_payload_fails_closed():
    with pytest.raises(ValueError, match="NONEMPTY_PROMPT_TO_REPEAT_REQUIRED"):
        proof.prove_prompt("   ")


def test_theorem_is_zero_terminal_data_and_zero_credit():
    out = proof.verify()
    assert out["terminal_rows_read"] == 0
    assert out["hidden_terminal_kwargs_read"] == 0
    assert out["target_scores_read"] == 0
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
    assert out["ownership_credit"] is False
    assert (
        out["deleted_proof_requirement"]
        == "ENUMERATE_OR_QUOTIENT_ARBITRARY_REPEAT_PROMPT_ARTICLE_TEXT_IDENTITIES"
    )
