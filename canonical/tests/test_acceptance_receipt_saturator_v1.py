from canonical.runtime.acceptance_receipt_saturator_v1 import compile_saturation


def _registry():
    return {
        "predicates": [
            {"id": "P1", "family": "F1", "kind": "INVARIANT"},
            {"id": "P2", "family": "F2", "kind": "PUBLIC_FIXED_BAR", "surface": "B"},
        ]
    }


def test_incomplete_until_every_predicate_searched():
    out = compile_saturation(
        _registry(),
        {
            "source_snapshot_sha": "abc1234",
            "predicate_dispositions": [
                {"predicate_id": "P1", "search_state": "SEARCHED_EXHAUSTIVELY_NO_MATCH"}
            ],
        },
    )
    assert out["pass"] is False
    assert out["searched_predicate_count"] == 1


def test_narrow_receipt_is_exclusion_not_credit():
    out = compile_saturation(
        _registry(),
        {
            "source_snapshot_sha": "abc1234",
            "predicate_dispositions": [
                {
                    "predicate_id": "P1",
                    "search_state": "SEARCHED_EXHAUSTIVELY_ONLY_INSUFFICIENT_MATCHES",
                    "insufficient_receipts": [{
                        "source_path": "receipt.json",
                        "source_sha": "deadbeef",
                        "reason": "SCOPE_NARROWER_THAN_PREDICATE",
                    }],
                },
                {"predicate_id": "P2", "search_state": "SEARCHED_EXHAUSTIVELY_NO_MATCH"},
            ],
        },
    )
    assert out["pass"] is True
    assert out["proved_claim_count"] == 0
    assert out["insufficient_receipt_count"] == 1


def test_valid_direct_receipt_binds():
    out = compile_saturation(
        _registry(),
        {
            "source_snapshot_sha": "abc1234",
            "predicate_dispositions": [
                {
                    "predicate_id": "P1",
                    "search_state": "SEARCHED_EXHAUSTIVELY_MATCH_BOUND",
                    "bound_claim": {
                        "proof_kind": "DIRECT_ORACLE",
                        "source_path": "receipt.json",
                        "source_sha": "deadbeef",
                        "independent_or_objective": True,
                        "scope_complete": True,
                    },
                },
                {"predicate_id": "P2", "search_state": "SEARCHED_EXHAUSTIVELY_NO_MATCH"},
            ],
        },
    )
    assert out["pass"] is True
    assert out["proved_claim_count"] == 1
    assert out["claims"][0]["predicate_id"] == "P1"


def test_public_predicate_rejects_plain_receipt():
    out = compile_saturation(
        _registry(),
        {
            "source_snapshot_sha": "abc1234",
            "predicate_dispositions": [
                {"predicate_id": "P1", "search_state": "SEARCHED_EXHAUSTIVELY_NO_MATCH"},
                {
                    "predicate_id": "P2",
                    "search_state": "SEARCHED_EXHAUSTIVELY_MATCH_BOUND",
                    "bound_claim": {
                        "proof_kind": "RECEIPT",
                        "source_path": "receipt.json",
                        "source_sha": "deadbeef",
                        "independent_or_objective": True,
                        "scope_complete": True,
                    },
                },
            ],
        },
    )
    assert out["pass"] is False
    assert any(e.startswith("INADMISSIBLE_PROOF_KIND:P2") for e in out["errors"])
