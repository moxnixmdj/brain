from canonical.runtime.benchmark_capability_dominance_scheduler_v1 import (
    branded_score_can_close,
    capability_projection_can_grant_credit,
    family_incidence,
    plan,
    summarize,
)

FRONTIER = {
    "benchmark_rows": [
        {
            "id": "A",
            "scheduler_state": "WAKE_GATED",
            "capability_projection": {
                "relation": "SCHEDULING_HEURISTIC_ONLY",
                "families": ["F1", "F2"],
            },
        },
        {
            "id": "B",
            "scheduler_state": "PARKED",
            "capability_projection": {
                "relation": "SCHEDULING_HEURISTIC_ONLY",
                "families": ["F1"],
            },
        },
    ]
}


def test_heuristic_projection_never_grants_capability_credit():
    assert capability_projection_can_grant_credit(FRONTIER["benchmark_rows"][0]) is False


def test_typed_strong_relation_can_participate_in_capability_credit():
    row = {
        "capability_projection": {
            "relation": "CONSERVATIVE_DOMINANCE",
            "families": ["F1"],
        }
    }
    assert capability_projection_can_grant_credit(row) is True


def test_capability_proof_does_not_invent_branded_score():
    assert branded_score_can_close() is False
    assert branded_score_can_close(exact_owner_receipt_bound=True) is True
    assert branded_score_can_close(explicit_score_entailment_bound=True) is True


def test_family_incidence_is_scheduling_only():
    rows = family_incidence(FRONTIER)
    assert rows[0]["family"] == "F1"
    assert rows[0]["projected_row_count"] == 2
    assert rows[0]["credit_authority_from_projection"] is False


def test_summary_preserves_wake_and_parked_states():
    out = summarize(FRONTIER)
    assert out["runnable_benchmark_row_count"] == 0
    assert out["wake_gated_benchmark_row_count"] == 1
    assert out["parked_benchmark_row_count"] == 1
    assert out["branded_score_credit_delta"] == 0


def test_same_information_benchmark_retry_rejected():
    out = plan(
        FRONTIER,
        [{
            "id": "retry-a",
            "type": "BENCHMARK_SPECIFIC",
            "benchmark_row_id": "A",
            "new_policy_changing_evidence": False,
            "incremental_spend_usd": 0,
            "external_runtime_cognition": 0,
        }],
    )
    assert out["selected"] is None
    assert out["rejected"][0]["reason"] == "BENCHMARK_ROW_NOT_RUNNABLE"


def test_graph_centrality_does_not_create_capability_work():
    out = plan(
        FRONTIER,
        [{
            "id": "popular-family",
            "type": "CAPABILITY",
            "reusable_family_count": 99,
            "projected_benchmark_row_count": 99,
            "proved_live_defect": False,
            "verified_counterexample": False,
            "authorized_discriminating_experiment": False,
            "incremental_spend_usd": 0,
            "external_runtime_cognition": 0,
        }],
    )
    assert out["selected"] is None
    assert out["rejected"][0]["reason"] == "NO_LIVE_CAPABILITY_DEFECT_OR_DISCRIMINATOR"


def test_live_reusable_capability_defect_beats_resource_only_work():
    out = plan(
        FRONTIER,
        [
            {
                "id": "resource",
                "type": "RESOURCE_PARETO",
                "proof_preserving": True,
                "wall_clock_rank": 1,
                "incremental_spend_usd": 0,
                "external_runtime_cognition": 0,
            },
            {
                "id": "live-defect",
                "type": "CAPABILITY",
                "proved_live_defect": True,
                "reusable_family_count": 3,
                "projected_benchmark_row_count": 5,
                "wall_clock_rank": 5,
                "incremental_spend_usd": 0,
                "external_runtime_cognition": 0,
            },
        ],
    )
    assert out["selected"]["id"] == "live-defect"


def test_resource_pareto_is_admitted_when_no_live_capability_defect_exists():
    out = plan(
        FRONTIER,
        [{
            "id": "resource",
            "type": "RESOURCE_PARETO",
            "proof_preserving": True,
            "wall_clock_rank": 1,
            "incremental_spend_usd": 0,
            "external_runtime_cognition": 0,
        }],
    )
    assert out["selected"]["id"] == "resource"


def test_external_runtime_cognition_and_paid_work_fail_closed():
    out = plan(
        FRONTIER,
        [
            {
                "id": "outsourced",
                "type": "CAPABILITY",
                "proved_live_defect": True,
                "external_runtime_cognition": 1,
                "incremental_spend_usd": 0,
            },
            {
                "id": "paid",
                "type": "RESOURCE_PARETO",
                "proof_preserving": True,
                "external_runtime_cognition": 0,
                "incremental_spend_usd": 0.01,
            },
        ],
    )
    assert out["selected"] is None
    assert {x["reason"] for x in out["rejected"]} == {
        "EXTERNAL_RUNTIME_COGNITION_FORBIDDEN",
        "HARD_ZERO_INCREMENTAL_SPEND",
    }
