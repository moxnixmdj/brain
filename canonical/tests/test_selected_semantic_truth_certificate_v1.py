from __future__ import annotations
import json

from canonical.runtime.selected_semantic_truth_certificate_v1 import evaluate

POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)

def facts(value: str) -> str:
    return json.dumps({
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exposure_amount": {"type": "DECIMAL_STRING", "value": value}},
    }, separators=(",", ":"))

def payload(value: str, claimed: bool = True):
    return {
        "predicate_id": "EXPOSURE_EXCEPTION_APPLIES",
        "target_claim_id": "selected",
        "source_text": POLICY,
        "source_id": "policy",
        "claims": [{
            "claim_id": "selected",
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            "condition_holds": claimed,
        }],
        "fact_source": facts(value),
        "fact_source_id": "case-facts",
    }

def test_selected_semantic_truth_certificate_true():
    out = evaluate(payload("130.00", True))
    assert out["pass"] is True
    assert out["predicate_truth"] == "TRUE"
    assert out["truthful_precommitment_observation"] is True
    assert out["policy_adequacy_authority"] is False
    assert out["terminal_authority"] is False

def test_selected_semantic_truth_certificate_false():
    out = evaluate(payload("100.00", False))
    assert out["pass"] is True
    assert out["predicate_truth"] == "FALSE"
    assert out["truthful_precommitment_observation"] is True
    assert out["policy_adequacy_authority"] is False

def test_wrong_claimed_truth_remains_unknown():
    out = evaluate(payload("130.00", False))
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"
    assert out["truthful_precommitment_observation"] is False
    assert out["terminal_authority"] is False

def test_unproved_paraphrase_remains_unknown():
    p = payload("130.00", True)
    p["source_text"] = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Aggregate exposure is at least 125.50."
    )
    out = evaluate(p)
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"
    assert out["truthful_precommitment_observation"] is False

def test_duplicate_claim_ids_fail_closed():
    p = payload("130.00", True)
    p["claims"] = p["claims"] + [dict(p["claims"][0])]
    out = evaluate(p)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert out["predicate_truth"] == "UNKNOWN"
    assert out["terminal_credit_delta"] == 0
