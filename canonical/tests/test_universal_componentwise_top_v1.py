from __future__ import annotations

from canonical.runtime.universal_componentwise_top_v1 import evaluate


def payload(dimensions, actions):
    return {
        "schema": "PROJECT_BRAIN_UNIVERSAL_COMPONENTWISE_TOP_INPUT_V1",
        "dimensions": dimensions,
        "actions": actions,
    }


def test_common_top_erases_monotone_weight_preference():
    out = evaluate(payload(
        [
            {"id": "quality", "direction": "MAX"},
            {"id": "latency", "direction": "MIN"},
            {"id": "risk", "direction": "MIN"},
        ],
        [
            {"id": "brain", "values": {"quality": "10", "latency": "2", "risk": "0"}},
            {"id": "a", "values": {"quality": "9", "latency": "2", "risk": "0"}},
            {"id": "b", "values": {"quality": "10", "latency": "3", "risk": "1"}},
        ],
    ))
    assert out["pass"] is True
    assert out["common_top_exists"] is True
    assert out["common_top_action_ids"] == ["brain"]
    assert out["componentwise_dominance"]["brain"] == ["a", "b", "brain"]
    assert out["target_preference_erasure_candidate"] is True
    assert out["terminal_authority"] is False


def test_tradeoff_fails_to_erase_hidden_preference():
    out = evaluate(payload(
        [
            {"id": "quality", "direction": "MAX"},
            {"id": "latency", "direction": "MIN"},
        ],
        [
            {"id": "high_quality", "values": {"quality": "10", "latency": "5"}},
            {"id": "fast", "values": {"quality": "8", "latency": "1"}},
        ],
    ))
    assert out["pass"] is True
    assert out["common_top_exists"] is False
    assert out["target_preference_erasure_candidate"] is False


def test_multiple_common_tops_are_allowed_when_vectors_tie():
    out = evaluate(payload(
        [{"id": "q", "direction": "MAX"}],
        [
            {"id": "a", "values": {"q": "7/3"}},
            {"id": "b", "values": {"q": "7/3"}},
            {"id": "c", "values": {"q": "2"}},
        ],
    ))
    assert out["common_top_action_ids"] == ["a", "b"]


def test_missing_dimension_value_fails_closed():
    out = evaluate(payload(
        [{"id": "q", "direction": "MAX"}, {"id": "r", "direction": "MIN"}],
        [{"id": "a", "values": {"q": "1"}}],
    ))
    assert out["pass"] is False
    assert out["reason"] == "ACTION_DIMENSION_SET_MISMATCH"


def test_float_values_rejected_to_avoid_ordering_drift():
    out = evaluate(payload(
        [{"id": "q", "direction": "MAX"}],
        [{"id": "a", "values": {"q": 0.1}}],
    ))
    assert out["pass"] is False
    assert out["reason"] == "ACTION_VALUE_INVALID"
