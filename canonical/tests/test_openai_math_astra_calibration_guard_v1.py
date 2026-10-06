from canonical.runtime.openai_math_astra_calibration_guard_v1 import (
    WITNESS_SCHEMA,
    evaluate,
    evaluate_live,
)

def witness():
    return {
        "schema": WITNESS_SCHEMA,
        "official_cross_page_linkage": {
            "oct6_internal_frontier_anchor_targets_sep8_navier_page": True,
            "sep8_astra_superiority_statement_present": True,
        },
        "semantic_boundaries": {
            "exact_checkpoint_identity_proved": False,
            "per_context_distributional_dominance_proved": False,
            "target_opus_relation_proved": False,
            "external_page_immutability_proved": False,
        },
        "qualitative_calibration_use": "ASTRA_SUPERIOR_INTERNAL_MODEL_LINEAGE_EVIDENCE_ONLY",
    }

def test_valid_relation_is_zero_credit_only():
    out=evaluate(witness())
    assert out["status"].startswith("PASS__")
    assert out["may_rank_corpus_as_frontier_beyond_astra_signal"] is True
    assert out["may_use_as_matched_astra_dominance_certificate"] is False
    assert out["may_use_for_terminal_transitivity"] is False
    assert out["terminal_credit_delta"] == 0

def test_checkpoint_identity_laundering_rejected():
    w=witness()
    w["semantic_boundaries"]["exact_checkpoint_identity_proved"]=True
    assert evaluate(w)["status"]=="FAIL_CLOSED"

def test_distributional_dominance_laundering_rejected():
    w=witness()
    w["semantic_boundaries"]["per_context_distributional_dominance_proved"]=True
    assert evaluate(w)["status"]=="FAIL_CLOSED"

def test_opus_transitivity_laundering_rejected():
    w=witness()
    w["semantic_boundaries"]["target_opus_relation_proved"]=True
    assert evaluate(w)["status"]=="FAIL_CLOSED"

def test_live_witness_passes_zero_credit():
    out=evaluate_live()
    assert out["status"]=="PASS__QUALITATIVE_ASTRA_SUPERIOR_LINEAGE_EVIDENCE_ONLY__ZERO_CREDIT"
    assert out["terminal_credit_delta"]==0
