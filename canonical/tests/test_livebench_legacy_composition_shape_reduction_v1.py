from canonical.runtime.livebench_legacy_composition_shape_reduction_v1 import (
    ACTIVE_IDS,
    EXPECTED_ACTIVE_ID_COMMITMENT,
    EXPECTED_BRANCH_COUNTS,
    EXPECTED_COUNTS_BY_SIZE,
    EXPECTED_TOTAL,
    active_commitment,
    branch,
    conflict_compatible,
    enumerate_shapes,
    verify_reduction,
)


def test_commitment_stays_bound_to_existing_terminal_set_digest():
    assert active_commitment() == EXPECTED_ACTIVE_ID_COMMITMENT
    assert len(ACTIVE_IDS) == 15


def test_exact_shape_counts():
    shapes = enumerate_shapes()
    assert len(shapes) == EXPECTED_TOTAL
    by_size = {k: sum(len(x) == k for x in shapes) for k in range(1, 6)}
    assert by_size == EXPECTED_COUNTS_BY_SIZE


def test_exact_branch_counts():
    shapes = enumerate_shapes()
    counts = {k: sum(branch(x) == k for x in shapes) for k in EXPECTED_BRANCH_COUNTS}
    assert counts == EXPECTED_BRANCH_COUNTS


def test_json_branch_is_tiny_and_only_keyword_compatible():
    shapes = [set(x) for x in enumerate_shapes() if "detectable_format:json_format" in x]
    assert len(shapes) == 4
    allowed = {
        "detectable_format:json_format",
        "keywords:existence",
        "keywords:forbidden_words",
    }
    assert all(s <= allowed for s in shapes)


def test_two_responses_branch_is_tiny():
    shapes = [set(x) for x in enumerate_shapes() if "combination:two_responses" in x]
    assert len(shapes) == 8
    allowed = {
        "combination:two_responses",
        "keywords:existence",
        "keywords:forbidden_words",
        "detectable_format:title",
    }
    assert all(s <= allowed for s in shapes)


def test_repeat_prompt_branch_is_tiny():
    shapes = [set(x) for x in enumerate_shapes() if "combination:repeat_prompt" in x]
    assert len(shapes) == 4
    allowed = {
        "combination:repeat_prompt",
        "keywords:existence",
        "detectable_format:title",
    }
    assert all(s <= allowed for s in shapes)


def test_known_conflicts_rejected():
    assert not conflict_compatible([
        "detectable_format:json_format",
        "startend:end_checker",
    ])
    assert not conflict_compatible([
        "length_constraints:number_paragraphs",
        "length_constraints:number_sentences",
    ])
    assert not conflict_compatible([
        "detectable_format:title",
        "startend:quotation",
    ])


def test_verification_receipt_is_zero_terminal_zero_credit():
    out = verify_reduction()
    assert out["status"] == "PASS__EXACT_CONFLICT_COMPATIBLE_IDENTITY_SHAPE_REDUCTION"
    assert out["new_terminal_cases_exposed"] == 0
    assert out["terminal_case_content_used"] is False
    assert out["terminal_case_metadata_used"] is False
    assert out["case_frequency_claimed"] is False
    assert out["acceptance_credit"] is False
