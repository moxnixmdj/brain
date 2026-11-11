from canonical.runtime.livebench_ratio_overlap_whitespace_invariant_v1 import (
    RatioOverlapBlocked,
    norm_ws,
    overlap_percent,
    parse_public_ratio_prompt,
    synthesize_public_ratio_overlap,
    whitespace_free_score_equivalence,
)


def test_whitespace_free_score_equivalence_is_exact():
    raw = "Alpha beta\nGamma\tDelta\r\nEpsilon."
    normalized = norm_ws(raw)
    responses = [
        "Alpha",
        "Gamma",
        "Delta",
        "AlphaBeta",
        "str\uE000\uE001\uE002",
        "x.y.z.",
    ]
    for response in responses:
        assert not any(ch.isspace() for ch in response)
        assert whitespace_free_score_equivalence(
            response,
            raw_reference=raw,
            normalized_reference=normalized,
        )
        assert overlap_percent(response, raw) == overlap_percent(response, normalized)


def test_equivalence_rejects_whitespace_response():
    assert not whitespace_free_score_equivalence(
        "Alpha Beta",
        raw_reference="Alpha\nBeta",
        normalized_reference="Alpha Beta",
    )


def test_parser_recovers_ratio_only_visible_reference():
    prompt = (
        "Use induction to prove a graph claim. "
        "Maintain a trigram overlap of 72% (±2%) with the provided reference text."
    )
    parsed = parse_public_ratio_prompt(prompt)
    assert parsed["percentage"] == 72.0
    assert parsed["normalized_reference"] == "Use induction to prove a graph claim."
    assert parsed["keyword"] is None
    assert parsed["consonant_cluster"] is False


def test_parser_drops_zero_width_format_artifact_at_constraint_boundary():
    prompt = (
        "Explain axisymmetric continuity step by step."
        "\u200bMaintain a trigram overlap of 74% (±2%) with the provided reference text."
    )
    parsed = parse_public_ratio_prompt(prompt)
    assert parsed["normalized_reference"] == "Explain axisymmetric continuity step by step."


def test_high_ratio_synthesis_needs_no_raw_whitespace_layout():
    prompt = (
        "Discuss Self-Determination and Transformational leadership. "
        "Maintain a trigram overlap of 93% (±2%) with the provided reference text."
    )
    out = synthesize_public_ratio_overlap(prompt)
    assert out["status"].startswith("PASS")
    assert out["response_has_whitespace"] is False
    assert 91.0 <= out["score_against_normalized_reference"] <= 95.0
    assert not any(ch.isspace() for ch in out["response"])


def test_keyword_companion_synthesis_30th_sentence():
    prompt = (
        "Write a believable sci fi history about a parasite that retains memories. "
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence."
    )
    out = synthesize_public_ratio_overlap(prompt)
    response = out["response"]
    sentences = [part for part in response.split(".") if part]
    assert len(sentences) >= 30
    assert "horary" in sentences[29].lower()
    assert 21.0 <= out["score_against_normalized_reference"] <= 25.0
    assert not any(ch.isspace() for ch in response)


def test_consonant_companion_synthesis():
    prompt = (
        "Analyze real-time rendering for animated movies. "
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 54% (±2%) with the provided reference text."
    )
    out = synthesize_public_ratio_overlap(prompt)
    response = out["response"].lower()
    assert "st" in response
    assert 52.0 <= out["score_against_normalized_reference"] <= 56.0
    assert not any(ch.isspace() for ch in response)


def test_keyword_and_consonant_unverified_combination_fails_closed():
    prompt = (
        "Base task. "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
        "The response must include keyword token in the 2-th sentence. "
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together)."
    )
    try:
        parse_public_ratio_prompt(prompt)
    except RatioOverlapBlocked as exc:
        assert "UNVERIFIED_RATIO_COMPANION_COMBINATION" in str(exc)
    else:
        raise AssertionError("expected fail-closed rejection")
