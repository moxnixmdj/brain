#!/usr/bin/env python3
from canonical.runtime import root1_livebench_if_scorer_aligned_adapter_v3 as adapter


def _req(prompt: str) -> dict:
    return {
        "task_id": "synthetic",
        "benchmark_id": adapter.BENCHMARK_ID,
        "allowed_tools": [],
        "task_payload": {"prompt": prompt},
    }


def test_word_count_constraint_no_semantic_seed_required(monkeypatch):
    def forbidden_fallback(_request):
        raise AssertionError("fallback must not run")
    monkeypatch.setattr(adapter.fallback_v2, "infer", forbidden_fallback)

    out = adapter.infer(_req(
        "<instructions>Answer with between 5 and 7 words.</instructions>"
        "Explain the history of an arbitrary topic."
    ))
    assert out["status"].startswith("PASS__MODEL_INDEPENDENT")
    assert out["semantic_seed_required_for_local_scored_constraints"] is False
    assert 5 <= len(out["answer"].split()) <= 7


def test_exact_number_constraint_no_semantic_seed_required(monkeypatch):
    def forbidden_fallback(_request):
        raise AssertionError("fallback must not run")
    monkeypatch.setattr(adapter.fallback_v2, "infer", forbidden_fallback)

    out = adapter.infer(_req(
        "<instructions>Answer with exactly 3 numbers.</instructions>"
        "Discuss something semantic."
    ))
    assert out["status"].startswith("PASS__MODEL_INDEPENDENT")
    import re
    assert len(re.findall(r"\b\d+\b", out["answer"])) == 3


def test_no_explicit_instruction_envelope_falls_back(monkeypatch):
    sentinel = {"status": "FALLBACK"}
    monkeypatch.setattr(adapter.fallback_v2, "infer", lambda _request: sentinel)
    assert adapter.infer(_req("Answer with at least 5 words.")) is sentinel


def test_ambiguous_multiple_instruction_envelopes_falls_back(monkeypatch):
    sentinel = {"status": "FALLBACK"}
    monkeypatch.setattr(adapter.fallback_v2, "infer", lambda _request: sentinel)
    prompt = (
        "<instructions>Answer with at least 5 words.</instructions>"
        "<instructions>Answer with exactly 2 numbers.</instructions>"
    )
    assert adapter.infer(_req(prompt)) is sentinel


def test_unrecognized_constraint_falls_back(monkeypatch):
    sentinel = {"status": "FALLBACK"}
    monkeypatch.setattr(adapter.fallback_v2, "infer", lambda _request: sentinel)
    prompt = "<instructions>Write a beautiful sonnet.</instructions>"
    assert adapter.infer(_req(prompt)) is sentinel
