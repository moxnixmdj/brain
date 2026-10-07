from copy import deepcopy
from unittest.mock import patch

from canonical.runtime import gdpval_rubric_acceptance_replay_v1 as replay
from canonical.runtime.gdpval_rubric_acceptance_evidence_verifier_v1 import verify


def rows():
    return [
        {
            "row_idx": 0,
            "row": {
                "task_id": "t0",
                "rubric_json": [
                    {"rubric_item_id": "r0", "criterion": "A", "score": 1,
                     "required": True, "author_type": "human"},
                    {"rubric_item_id": "r1", "criterion": "B", "score": 2,
                     "required": False, "author_type": "human"},
                ],
            },
        },
        {
            "row_idx": 1,
            "row": {
                "task_id": "t1",
                "rubric_json": [
                    {"rubric_item_id": "r2", "criterion": "C", "score": None,
                     "required": None, "author_type": "human"},
                ],
            },
        },
    ]


def metadata(revision=replay.EXPECTED_REVISION):
    return {"sha": revision}


def test_revision_drift_fails_before_rows_are_consumed():
    called = {"rows": False}

    def loader():
        called["rows"] = True
        return rows()

    out = replay.execute(
        metadata_fetcher=lambda: metadata("deadbeef"),
        rows_loader=loader,
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "DATASET_REVISION_DRIFT"
    assert called["rows"] is False


def test_complete_bound_replay_and_independent_verifier_pass():
    with patch.object(replay, "EXPECTED_TASKS", 2), patch.object(
        replay, "EXPECTED_CRITERIA", 3
    ), patch(
        "canonical.runtime.gdpval_rubric_acceptance_evidence_verifier_v1.EXPECTED_TASKS", 2
    ), patch(
        "canonical.runtime.gdpval_rubric_acceptance_evidence_verifier_v1.EXPECTED_CRITERIA", 3
    ):
        out = replay.execute(
            metadata_fetcher=lambda: metadata(),
            rows_loader=rows,
        )
        assert out["pass"] is True
        assert out["index"]["aggregate"]["task_count"] == 2
        assert out["index"]["aggregate"]["criterion_count"] == 3
        verdict = verify(out)
        assert verdict["pass"] is True, verdict


def test_tampered_criterion_text_is_rejected_independently():
    with patch.object(replay, "EXPECTED_TASKS", 2), patch.object(
        replay, "EXPECTED_CRITERIA", 3
    ), patch(
        "canonical.runtime.gdpval_rubric_acceptance_evidence_verifier_v1.EXPECTED_TASKS", 2
    ), patch(
        "canonical.runtime.gdpval_rubric_acceptance_evidence_verifier_v1.EXPECTED_CRITERIA", 3
    ):
        out = replay.execute(
            metadata_fetcher=lambda: metadata(),
            rows_loader=rows,
        )
        damaged = deepcopy(out)
        damaged["index"]["tasks"][0]["criteria"][0]["criterion"] = "TAMPERED"
        verdict = verify(damaged)
        assert verdict["pass"] is False
        assert any("CRITERION_TEXT_HASH_MISMATCH" in e for e in verdict["errors"])


def test_population_count_drift_fails_closed():
    with patch.object(replay, "EXPECTED_TASKS", 3), patch.object(
        replay, "EXPECTED_CRITERIA", 3
    ):
        out = replay.execute(
            metadata_fetcher=lambda: metadata(),
            rows_loader=rows,
        )
        assert out["pass"] is False
        assert out["reason"] == "TASK_COUNT_DRIFT"
