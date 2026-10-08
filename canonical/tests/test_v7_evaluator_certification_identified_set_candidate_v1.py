from canonical.runtime.v7_evaluator_certification_identified_set_candidate_v1 import (
    V7IdentifiedSetRouteError,
    certify,
)


def _identified_task():
    return {
        "target_distribution": [
            {"id": "bad", "probability": "1/2"},
            {"id": "good", "probability": "1/2"},
        ],
        "brain_distribution": [
            {"id": "bad", "probability": "1/4"},
            {"id": "good", "probability": "3/4"},
        ],
        "evaluator_worlds": [
            {
                "world_id": "W1",
                "utility": {"bad": "0", "good": "1"},
                "facts": {"judge_class": "A"},
            },
            {
                "world_id": "W2",
                "utility": {"bad": "1/4", "good": "1"},
                "facts": {"judge_class": "B"},
            },
        ],
    }


def _receipt():
    return [{"path": "canonical/verification/example.json", "git_blob_sha": "a" * 40}]


def test_identified_route_passes_only_conditionally():
    out = certify({
        "mode": "R",
        "semantic_receipts": _receipt(),
        "identified_set_task": _identified_task(),
    })
    assert out["route"] == "R_PARTIALLY_IDENTIFIED_HIDDEN"
    assert out["conditional_noninferiority"] is True
    assert out["semantic_premise_verified_by_this_runtime"] is False
    assert out["terminal_authority"] is False


def test_identified_route_requires_external_semantic_receipt():
    try:
        certify({"mode": "R", "identified_set_task": _identified_task()})
    except V7IdentifiedSetRouteError as exc:
        assert "SEMANTIC_PROOF_RECEIPTS_REQUIRED" in str(exc)
    else:
        raise AssertionError("expected fail closed")


def test_bad_receipt_sha_fails_closed():
    try:
        certify({
            "mode": "R",
            "semantic_receipts": [{"path": "x", "git_blob_sha": "not-a-sha"}],
            "identified_set_task": _identified_task(),
        })
    except V7IdentifiedSetRouteError as exc:
        assert "SHA_INVALID" in str(exc)
    else:
        raise AssertionError("expected fail closed")
