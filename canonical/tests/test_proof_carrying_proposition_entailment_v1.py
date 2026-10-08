import hashlib
from pathlib import Path

from canonical.runtime.proof_carrying_proposition_entailment_v1 import verify_entailment


ROOT = Path(__file__).resolve().parents[2]


def git_blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


REL = "canonical/tests/fixtures/semantic_relations/test_release_launch_relation_v1.json"
VER = "canonical/tests/fixtures/semantic_relations/test_release_launch_relation_verify_v1.json"


def test_exact_identity_needs_zero_steps():
    out = verify_entailment({
        "evidence_text": "The product launched in June.",
        "claim_text": "The product launched in June.",
        "steps": [],
    })
    assert out["pass"] is True
    assert out["step_count"] == 0


def test_mechanical_numeric_paraphrase():
    out = verify_entailment({
        "evidence_text": "Revenue growth is no less than 12.",
        "claim_text": "Revenue growth is at least 12.",
        "steps": [{
            "kind": "MECHANICAL_NUMERIC_EQUIVALENCE",
            "to_text": "Revenue growth is at least 12.",
        }],
    })
    assert out["pass"] is True
    assert out["step_audit"][0]["relation"] == "EQUIVALENT"


def test_numeric_mismatch_fails_closed():
    out = verify_entailment({
        "evidence_text": "Revenue growth is no less than 12.",
        "claim_text": "Revenue growth is at least 13.",
        "steps": [{
            "kind": "MECHANICAL_NUMERIC_EQUIVALENCE",
            "to_text": "Revenue growth is at least 13.",
        }],
    })
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"


def test_content_addressed_relation_fixture_passes_only_in_test_mode():
    payload = {
        "evidence_text": "The product's commercial release occurred in June.",
        "claim_text": "The product launched in June.",
        "steps": [{
            "kind": "CERTIFIED_PROPOSITION_RELATION",
            "to_text": "The product launched in June.",
            "relation_receipt": {"path": REL, "git_blob_sha": git_blob_sha(REL)},
            "verification_receipt": {"path": VER, "git_blob_sha": git_blob_sha(VER)},
        }],
    }
    blocked = verify_entailment(payload)
    assert blocked["pass"] is False
    assert "AUTHORIZED_PREFIX" in blocked["reason"]

    out = verify_entailment(payload, allow_test_fixtures=True)
    assert out["pass"] is True
    assert out["step_audit"][0]["relation"] == "ENTAILS"


def test_blob_mismatch_rejected():
    out = verify_entailment({
        "evidence_text": "The product's commercial release occurred in June.",
        "claim_text": "The product launched in June.",
        "steps": [{
            "kind": "CERTIFIED_PROPOSITION_RELATION",
            "to_text": "The product launched in June.",
            "relation_receipt": {"path": REL, "git_blob_sha": "0" * 40},
            "verification_receipt": {"path": VER, "git_blob_sha": git_blob_sha(VER)},
        }],
    }, allow_test_fixtures=True)
    assert out["pass"] is False
    assert "BLOB_MISMATCH" in out["reason"]


def test_receipt_cannot_be_reused_for_different_target():
    out = verify_entailment({
        "evidence_text": "The product's commercial release occurred in June.",
        "claim_text": "The product launched in July.",
        "steps": [{
            "kind": "CERTIFIED_PROPOSITION_RELATION",
            "to_text": "The product launched in July.",
            "relation_receipt": {"path": REL, "git_blob_sha": git_blob_sha(REL)},
            "verification_receipt": {"path": VER, "git_blob_sha": git_blob_sha(VER)},
        }],
    }, allow_test_fixtures=True)
    assert out["pass"] is False
    assert "HYPOTHESIS_MISMATCH" in out["reason"]


def test_chain_must_end_at_claim():
    out = verify_entailment({
        "evidence_text": "Revenue growth is no less than 12.",
        "claim_text": "Revenue growth is at most 12.",
        "steps": [{
            "kind": "MECHANICAL_NUMERIC_EQUIVALENCE",
            "to_text": "Revenue growth is at least 12.",
        }],
    })
    assert out["pass"] is False
    assert out["status"] == "UNKNOWN__PROOF_CHAIN_DOES_NOT_END_AT_CLAIM"


def test_unknown_step_kind_rejected():
    out = verify_entailment({
        "evidence_text": "A.",
        "claim_text": "B.",
        "steps": [{"kind": "TRUST_ME", "to_text": "B."}],
    })
    assert out["pass"] is False
    assert "STEP_KIND_UNSUPPORTED" in out["reason"]


def test_never_grants_policy_or_terminal_authority():
    out = verify_entailment({
        "evidence_text": "Revenue growth is no less than 12.",
        "claim_text": "Revenue growth is at least 12.",
        "steps": [{
            "kind": "MECHANICAL_NUMERIC_EQUIVALENCE",
            "to_text": "Revenue growth is at least 12.",
        }],
    })
    assert out["pass"] is True
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
