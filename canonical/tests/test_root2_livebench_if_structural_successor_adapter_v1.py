from __future__ import annotations

import pytest

from canonical.runtime import root2_livebench_if_structural_successor_adapter_v1 as mod


def _request(text: str) -> dict:
    return {
        "benchmark_id": mod.BENCHMARK_ID,
        "task_id": "t",
        "task_payload": text,
        "allowed_tools": [],
    }


def test_exact_literal_uses_zero_model_zero_tool_direct_route(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("general runtime must not be called")

    monkeypatch.setattr(mod.astra_runtime, "run_goal", forbidden)
    out = mod.infer(_request('Reply with exactly "ALPHA".'))
    assert out["answer"] == "ALPHA"
    assert out["status"] == "PASS__PRECOMPILED_STRUCTURAL_SUCCESSOR_RESPONSE"
    assert out["cognition_dependency_class"] == "MODEL_INDEPENDENT"
    assert out["model_dependency_count"] == 0
    assert out["tool_trace"][0]["post_prompt_acquisition"] is False
    assert out["tool_trace"][0]["external_tools_used"] is False


def test_structural_seed_required_for_general_use_is_still_direct_for_if_scorer(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("general runtime must not be called")

    monkeypatch.setattr(mod.astra_runtime, "run_goal", forbidden)
    out = mod.infer(_request("Use exactly 5 words and include exactly 2 numbers."))
    words = out["answer"].split()
    assert len(words) == 5
    assert sum(token.isdigit() for token in words) == 2
    assert out["status"] == "PASS__PRECOMPILED_STRUCTURAL_SUCCESSOR_RESPONSE"
    assert out["tool_trace"][0]["semantic_seed_required_by_general_use"] is True


def test_unrecognized_prompt_falls_back_without_optional_model(monkeypatch):
    seen = {}

    def fake_run_goal(step, mission):
        seen["step"] = step
        seen["mission"] = mission
        return {
            "stdout": "local answer",
            "trace": [{"adapter": "owned"}],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }

    monkeypatch.setattr(mod.astra_runtime, "run_goal", fake_run_goal)
    out = mod.infer(_request("Explain photosynthesis."))
    assert out["answer"] == "local answer"
    assert out["status"] == "PASS__MODEL_INDEPENDENT_BRAIN_FALLBACK_RESPONSE"
    assert seen["step"]["allow_optional_model_planner"] is False


def test_external_tools_fail_closed():
    req = _request('Reply with exactly "ALPHA".')
    req["allowed_tools"] = ["web"]
    with pytest.raises(mod.LiveBenchStructuralSuccessorBlocked, match="EXTERNAL_TOOLS_FORBIDDEN"):
        mod.infer(req)


def test_benchmark_identity_fail_closed():
    req = _request('Reply with exactly "ALPHA".')
    req["benchmark_id"] = "other"
    with pytest.raises(mod.LiveBenchStructuralSuccessorBlocked, match="BENCHMARK_ID_MISMATCH"):
        mod.infer(req)
