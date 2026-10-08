import hashlib
from pathlib import Path

from canonical.runtime.selected_support_truth_certificate_v5 import evaluate

ROOT = Path(__file__).resolve().parents[2]
REL = "canonical/tests/fixtures/semantic_relations/test_release_launch_relation_v1.json"
VER = "canonical/tests/fixtures/semantic_relations/test_release_launch_relation_verify_v1.json"

def blob(path):
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def ev(eid,text):
    return {"evidence_id":eid,"text":text,"verified":True,
            "provenance":[{"source_id":eid,"locator":"p"}]}

def payload(claim,evidence,proofs=None):
    return {"predicate_id":"P3",
            "claim":{"claim_id":"C","text":claim,"required":True},
            "evidence":evidence,
            "semantic_proofs":proofs or {}}

def semantic_fixture_proof():
    return {"steps":[{
        "kind":"CERTIFIED_PROPOSITION_RELATION",
        "to_text":"The product launched in June.",
        "relation_receipt":{"path":REL,"git_blob_sha":blob(REL)},
        "verification_receipt":{"path":VER,"git_blob_sha":blob(VER)},
    }]}

def test_v5_closes_previous_unresolved_paraphrase_with_bound_proof():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E","The product's commercial release occurred in June.")],
        {"E":semantic_fixture_proof()},
    ),allow_test_fixtures=True)
    assert out["pass"] is True,out
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"]==[{
        "evidence_id":"E","relation":"SUPPORTS",
        "grammar":"PROOF_CARRYING_PROPOSITION_ENTAILMENT_V1"}]

def test_test_fixture_semantics_are_rejected_in_production_mode():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E","The product's commercial release occurred in June.")],
        {"E":semantic_fixture_proof()},
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"
    assert out["unresolved_evidence_ids"]==["E"]

def test_existing_numeric_semantics_cannot_be_overridden_by_bad_proof():
    out=evaluate(payload(
        "Revenue growth is at least 12.",
        [ev("E","Report states Revenue growth is 13.")],
        {"E":{"steps":[{"kind":"TRUST_ME","to_text":"Revenue growth is at least 12."}]}},
    ))
    assert out["pass"] is True,out
    assert out["predicate_truth"]=="TRUE"
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"
    assert out["semantic_proof_audit"]==[]

def test_existing_numeric_conflict_cannot_be_overridden_by_bad_proof():
    out=evaluate(payload(
        "Revenue growth is at least 12.",
        [ev("E","Report states Revenue growth is 11.")],
        {"E":{"steps":[{"kind":"TRUST_ME","to_text":"Revenue growth is at least 12."}]}},
    ))
    assert out["pass"] is True,out
    assert out["predicate_truth"]=="FALSE"
    assert out["relation_audit"][0]["relation"]=="CONFLICTS"
    assert out["semantic_proof_audit"]==[]

def test_unresolved_without_proof_stays_unknown():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E","A June product release took place.")],
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"
    assert out["unresolved_evidence_ids"]==["E"]

def test_forged_unknown_step_stays_unknown():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E","A June product release took place.")],
        {"E":{"steps":[{"kind":"TRUST_ME","to_text":"The product launched in June."}]}},
    ))
    assert out["pass"] is False
    assert out["predicate_truth"]=="UNKNOWN"
    assert out["semantic_proof_audit"][0]["pass"] is False

def test_extra_proof_for_nonexistent_evidence_fails_closed():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E","The product launched in June.")],
        {"X":{"steps":[]}},
    ))
    assert out["pass"] is False
    assert out["reason"]=="SEMANTIC_PROOF_FOR_UNKNOWN_EVIDENCE"

def test_v5_preserves_zero_authority_escalation():
    out=evaluate(payload(
        "The product launched in June.",
        [ev("E","The product's commercial release occurred in June.")],
        {"E":semantic_fixture_proof()},
    ),allow_test_fixtures=True)
    assert out["pass"] is True
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
