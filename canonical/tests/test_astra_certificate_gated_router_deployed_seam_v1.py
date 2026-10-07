import pytest

from canonical.runtime import astra_runtime


def _receipt(*, context="ctx", route="r1", cell="c1", admitted=True, a="1", q="2", r="3"):
    return {
        "context_digest": context,
        "cell_id": cell,
        "route_id": route,
        "route_blob_sha": r * 40,
        "adequacy_certificate_blob_sha": q * 40,
        "admission_certificate_blob_sha": a * 40,
        "admitted": admitted,
    }


def test_astra_deployed_action_selects_only_certified_context_bound_route():
    out = astra_runtime._goal_action({
        "type": "select_certified_route",
        "args": {
            "actual_context_digest": "ctx",
            "receipts": [
                _receipt(route="later", a="b"),
                _receipt(route="earlier", a="a"),
                _receipt(route="denied", a="0", admitted=False),
            ],
        },
    })
    assert out["output_verified"] is True
    assert out["route_id"] == "earlier"
    assert out["admitted"] is True
    assert out["semantic_adequacy_self_certified"] is False


def test_astra_deployed_action_fails_closed_for_uncovered_context():
    with pytest.raises(astra_runtime.Blocker, match="CERTIFICATE_GATED_ROUTE_FAIL_CLOSED"):
        astra_runtime._goal_action({
            "type": "select_certified_route",
            "args": {
                "actual_context_digest": "other",
                "receipts": [_receipt()],
            },
        })


def test_astra_deployed_action_rejects_non_boolean_admission():
    bad = _receipt()
    bad["admitted"] = 1
    with pytest.raises(astra_runtime.Blocker, match="CERTIFICATE_GATED_ROUTE_ADMISSION_NOT_BOOLEAN"):
        astra_runtime._goal_action({
            "type": "select_certified_route",
            "args": {
                "actual_context_digest": "ctx",
                "receipts": [bad],
            },
        })
