from canonical.runtime.livebench_ratio_overlap_public_prompt_solver_v1 import (
    construct_public_ratio_overlap_response,
    parse_public_ratio_overlap_prompt,
)


def test_parse_right_edge_plain_overlap():
    prompt = (
        "Explain orbital mechanics simply. "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    )
    out = parse_public_ratio_overlap_prompt(prompt)
    assert out["reference_normalized"] == "Explain orbital mechanics simply."
    assert out["target_percent"] == 50
    assert out["constraint_block_side"] == "RIGHT"


def test_parse_left_edge_keyword_conjunction():
    prompt = (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence. "
        "Write a believable sci-fi history about a parallel Earth."
    )
    out = parse_public_ratio_overlap_prompt(prompt)
    assert out["reference_normalized"].startswith("Write a believable")
    assert out["keyword"] == "horary"
    assert out["keyword_sentence"] == 30
    assert out["target_percent"] == 23


def test_zero_width_space_before_overlap_is_ignored():
    prompt = (
        "Reference request here. \u200bMaintain a trigram overlap of 74% (±2%) "
        "with the provided reference text."
    )
    out = parse_public_ratio_overlap_prompt(prompt)
    assert out["reference_normalized"] == "Reference request here."
    assert out["target_percent"] == 74


def test_keyword_conjunction_witness_is_whitespace_free_and_hits_target():
    prompt = (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. "
        "The response must include keyword horary in the 30-th sentence. "
        "Write a believable sci-fi history about a parallel Earth where archival "
        "records reveal a hidden sequence of technological revolutions."
    )
    out = construct_public_ratio_overlap_response(prompt)
    assert out["status"] == "PASS"
    assert out["candidate_whitespace_free"] is True
    assert out["keyword_constraint_pass"] is True
    assert abs(out["predicted_overlap_percent"] - 23) <= 2


def test_consonant_conjunction_witness_hits_target():
    prompt = (
        "Ensure each word in your response has at least one consonant cluster "
        "(two or more consonants together). "
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
        "Describe a long river valley and its geological history."
    )
    out = construct_public_ratio_overlap_response(prompt)
    assert out["status"] == "PASS"
    assert out["consonant_cluster_constraint_pass"] is True
    assert abs(out["predicted_overlap_percent"] - 50) <= 2


def test_unsupported_extra_constraint_fails_closed():
    prompt = (
        "Maintain a trigram overlap of 50% (±2%) with the provided reference text. "
        "Use exactly seven bananas. Explain orbital mechanics."
    )
    try:
        parse_public_ratio_overlap_prompt(prompt)
    except Exception as exc:
        assert "AMBIGUOUS_OR_UNSUPPORTED" in str(exc)
    else:
        raise AssertionError("unsupported conjunction must fail closed")
