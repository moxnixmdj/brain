from copy import deepcopy

from canonical.runtime.current_escape_oq_frontier_reduction_v1 import (
    O,
    Q,
    reduce_frontier,
    reduce_repo,
)


def test_current_repo_reduces_exact_13_to_o11_q2():
    out = reduce_repo()
    assert out["pass"] is True, out
    assert out["current_frontier_scope_complete"] is True
    assert out["current_frontier_row_count"] == 13
    assert out["objective_acceptance_count"] == 11
    assert out["qualitative_relative_order_count"] == 2
    assert out["mixed_count"] == 0
    assert out["unclassified_count"] == 0
    assert set(out["qualitative_obligation_ids"]) == {
        "PROWORK_GDPVAL_GE_1846",
        "PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT",
    }
    assert out["acceptance_closed"] is False
    assert out["escape_progress_totality_proved"] is False
    assert out["u_empty"] is False
    assert out["terminal_authority"] is False


def _docs():
    manifest = {
        "rows": [
            {"obligation_id": f"o{i}", "route_group": "A"}
            for i in range(13)
        ]
    }
    classification = {
        "exhaustive_rows": [
            {
                "obligation": f"o{i}",
                "regime": Q if i in {0, 1} else O,
                "basis": "bound",
            }
            for i in range(13)
        ]
    }
    return manifest, classification


def test_missing_current_row_fails_closed():
    manifest, classification = _docs()
    classification["exhaustive_rows"] = classification["exhaustive_rows"][:-1]
    out = reduce_frontier(manifest, classification)
    assert out["pass"] is False
    assert out["reason"] == "CURRENT_FRONTIER_UNCLASSIFIED"
    assert out["current_frontier_scope_complete"] is False


def test_regime_count_drift_fails_closed():
    manifest, classification = _docs()
    changed = deepcopy(classification)
    changed["exhaustive_rows"][2]["regime"] = Q
    out = reduce_frontier(manifest, changed)
    assert out["pass"] is False
    assert out["reason"] == "CURRENT_FRONTIER_OQ_COUNT_DRIFT"


def test_unknown_regime_fails_closed():
    manifest, classification = _docs()
    classification["exhaustive_rows"][3]["regime"] = "MYSTERY"
    out = reduce_frontier(manifest, classification)
    assert out["pass"] is False
    assert out["reason"] == "CLASSIFICATION_REGIME_INVALID"


def test_duplicate_classification_row_fails_closed():
    manifest, classification = _docs()
    classification["exhaustive_rows"].append(
        {
            "obligation": "o0",
            "regime": Q,
            "basis": "duplicate",
        }
    )
    out = reduce_frontier(manifest, classification)
    assert out["pass"] is False
    assert out["reason"] == "CLASSIFICATION_DUPLICATE_OBLIGATIONS"
