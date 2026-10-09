from canonical.runtime.benchmark_proof_evidence_adapter_v1 import adapt

SHA = "1" * 40
RECEIPT = {"path": "canonical/verification/proof.json", "git_blob_sha": SHA}

def registry():
    return {
        "schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2",
        "predicates": [{
            "id": "CODING_CURSORBENCH_GE_57_8",
            "family": "ADVANCED_AGENTIC_CODING",
        }],
    }

def verdict(status="PROVEN"):
    return {
        "schema": "PROJECT_BRAIN_BENCHMARK_CLAIM_KERNEL_V4",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "status": status,
        "locks": {"scope": "PASS"},
        "promotion_authority": False,
        "terminal_credit": 0,
    }

def test_proven_registered_predicate_yields_candidate_only():
    out = adapt(verdict(), RECEIPT, registry())
    assert out["pass"] is True, out
    assert out["candidate_claim"]["predicate_id"] == "CODING_CURSORBENCH_GE_57_8"
    assert out["candidate_claim"]["family"] == "ADVANCED_AGENTIC_CODING"
    assert out["candidate_claim"]["state"] == "PROVED"
    assert out["candidate_claim"]["promotion_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0

def test_unknown_kernel_result_cannot_be_adapted():
    out = adapt(verdict("UNKNOWN"), RECEIPT, registry())
    assert out["pass"] is False
    assert out["candidate_claim"] is None

def test_unregistered_predicate_cannot_be_injected():
    v = verdict()
    v["predicate_id"] = "MADE_UP"
    out = adapt(v, RECEIPT, registry())
    assert out["pass"] is False
    assert "PREDICATE_NOT_IN_FROZEN_REGISTRY" in out["errors"]

def test_adapter_rejects_kernel_with_promotion_authority():
    v = verdict()
    v["promotion_authority"] = True
    out = adapt(v, RECEIPT, registry())
    assert out["pass"] is False

def test_receipt_must_be_content_addressed():
    out = adapt(verdict(), {"path": "x", "git_blob_sha": "bad"}, registry())
    assert out["pass"] is False
