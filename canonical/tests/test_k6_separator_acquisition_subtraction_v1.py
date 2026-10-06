from canonical.runtime.k6_separator_acquisition_subtraction_v1 import (
    separator_selection_subtraction_contract,
    verify,
)

def test_separator_selection_is_suffix_only_under_explicit_model():
    out = separator_selection_subtraction_contract()
    assert out["explicit_model_complete"] is True
    assert out["separator_selection_owned_given_explicit_model"] is True
    assert out["successor_residual"] == "K6S_TASK_SUFFICIENT_SEMANTIC_HYPOTHESIS_AND_MODEL_FORMATION"

def test_claim_does_not_smuggle_semantic_generation():
    out = separator_selection_subtraction_contract()
    assert out["hypothesis_generation_owned_by_this_claim"] is False
    assert out["outcome_model_generation_owned_by_this_claim"] is False
    assert out["semantic_authority_owned_by_this_claim"] is False
    assert out["terminal_credit"] is False

def test_verify():
    assert verify().startswith("PASS__")
