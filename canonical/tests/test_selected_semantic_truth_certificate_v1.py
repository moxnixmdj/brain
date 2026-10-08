from __future__ import annotations
import hashlib
import json

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof
from canonical.runtime.selected_semantic_truth_certificate_v1 import evaluate

POLICY = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)
ALIAS = "EXPOSURE_EXCEPTION_APPLIES"

def facts(value: str) -> str:
    return json.dumps({
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exposure_amount": {"type": "DECIMAL_STRING", "value": value}},
    }, separators=(",", ":"))

def checked_predicate_id(policy: str = POLICY) -> str:
    proof = verify_proof(
        policy, source_id="policy",
        claims=[{
            "claim_id": "selected",
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            "condition_holds": True,
        }],
        fact_source=facts("130.00"), fact_source_id="case-facts",
    )
    assert proof["status"] == "PROOF_CHECKED"
    row = proof["accepted_claims"][0]
    descriptor = {
        "source_id": "policy",
        "source_sha256": hashlib.sha256(policy.encode("utf-8")).hexdigest(),
        "kind": row["kind"],
        "defined_term": row["defined_term"],
        "field_name": row["field_name"],
        "field_type": row["field_type"],
        "operator": row["operator"],
        "literal": row["literal"],
    }
    raw = json.dumps(descriptor, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return "source-condition-sha256:" + hashlib.sha256(raw).hexdigest()

SOURCE_PREDICATE_ID = checked_predicate_id()

def payload(value: str, claimed: bool = True, *, alias: str = ALIAS, policy: str = POLICY):
    return {
        "predicate_id": alias,
        "target_claim_id": "selected",
        "source_text": policy,
        "source_id": "policy",
        "claims": [{
            "claim_id": "selected",
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            "condition_holds": claimed,
        }],
        "fact_source": facts(value),
        "fact_source_id": "case-facts",
    }

def test_true_mints_source_bound_predicate_identity():
    out = evaluate(payload("130.00", True))
    assert out["pass"] is True
    assert out["predicate_truth"] == "TRUE"
    assert out["predicate_id"] == SOURCE_PREDICATE_ID
    assert out["requested_predicate_id"] == ALIAS
    assert out["requested_predicate_id_authority"] is False
    assert isinstance(out["verified_condition_atom_id"], str)
    assert out["truthful_precommitment_observation"] is True
    assert out["policy_adequacy_authority"] is False
    assert out["terminal_authority"] is False

def test_false_uses_same_source_predicate_identity():
    out = evaluate(payload("100.00", False))
    assert out["pass"] is True
    assert out["predicate_truth"] == "FALSE"
    assert out["predicate_id"] == SOURCE_PREDICATE_ID
    assert out["requested_predicate_id"] == ALIAS
    assert out["truthful_precommitment_observation"] is True

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

def test_caller_relabel_cannot_become_authoritative_predicate_id():
    p = payload("130.00", True, alias="OTHER_DECISION_SHOULD_BE_TRUE")
    out = evaluate(p)
    assert out["pass"] is True
    assert out["predicate_truth"] == "TRUE"
    assert out["predicate_id"] == SOURCE_PREDICATE_ID
    assert out["requested_predicate_id"] == "OTHER_DECISION_SHOULD_BE_TRUE"
    assert out["requested_predicate_id_authority"] is False
    assert out["predicate_id"] != out["requested_predicate_id"]

def test_changed_source_condition_mints_different_predicate_identity():
    changed = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Total exposure is at least 120.00."
    )
    out = evaluate(payload("130.00", True, policy=changed))
    assert out["pass"] is True
    assert out["predicate_id"] == checked_predicate_id(changed)
    assert out["predicate_id"] != SOURCE_PREDICATE_ID
    assert out["requested_predicate_id"] == ALIAS

def test_predicate_identity_stable_across_true_false_facts_but_atoms_change():
    positive = evaluate(payload("130.00", True))
    negative = evaluate(payload("100.00", False))
    assert positive["pass"] is True and negative["pass"] is True
    assert positive["predicate_id"] == negative["predicate_id"] == SOURCE_PREDICATE_ID
    assert positive["verified_condition_atom_id"] != negative["verified_condition_atom_id"]
    assert positive["predicate_truth"] == "TRUE"
    assert negative["predicate_truth"] == "FALSE"

def test_canonical_looking_forged_alias_cannot_override_verified_identity():
    forged = "source-condition-sha256:" + "0" * 64
    out = evaluate(payload("130.00", True, alias=forged))
    assert out["pass"] is True
    assert out["requested_predicate_id"] == forged
    assert out["predicate_id"] == SOURCE_PREDICATE_ID
    assert out["predicate_id"] != forged
    assert out["db_admission_authority"] is False

def test_v5_typed_receipt_stable_identity_and_optional_source_guard():
    from canonical.runtime.selected_semantic_truth_certificate_v1 import _checked_predicate_id
    trusted = verify_proof(
        POLICY, source_id="policy",
        claims=[{"claim_id": "selected", "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
                 "condition_holds": True}],
        fact_source=facts("130.00"), fact_source_id="case-facts",
    )["accepted_claims"][0]
    v5_shape = {**trusted, "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION"}
    v5_shape.pop("policy_source_id", None)
    assert _checked_predicate_id(
        v5_shape, "policy", hashlib.sha256(POLICY.encode("utf-8")).hexdigest()
    ) is not None
    v5_shape["policy_source_id"] = "forged-other-source"
    assert _checked_predicate_id(
        v5_shape, "policy", hashlib.sha256(POLICY.encode("utf-8")).hexdigest()
    ) is None
