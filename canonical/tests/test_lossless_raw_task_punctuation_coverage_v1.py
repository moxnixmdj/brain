from canonical.runtime import explicit_requirement_index_v2 as requirement_index
from canonical.runtime import lossless_raw_task_contract_v1 as raw_contract


def _nonwhitespace_positions(text: str) -> set[int]:
    return {i for i, ch in enumerate(text) if not ch.isspace()}


def _covered_positions(text: str, segments: list[tuple[int, int, str]]) -> set[int]:
    covered: set[int] = set()
    previous_end = -1
    for start, end, segment in segments:
        assert 0 <= start < end <= len(text)
        assert start >= previous_end
        assert text[start:end] == segment
        covered.update(i for i in range(start, end) if not text[i].isspace())
        previous_end = end
    return covered


def _assert_lossless_and_aligned(text: str) -> None:
    raw_segments = raw_contract._segments(text)
    index_segments = requirement_index._segments(text)
    assert raw_segments == index_segments
    assert _covered_positions(text, raw_segments) == _nonwhitespace_positions(text)

    contract = raw_contract.compile_contract(
        text,
        source_id="PUNCTUATION_COVERAGE_TEST",
        routing_target_effects=["TEST_EFFECT"],
    )
    assert contract["pass"] is True, contract
    assert contract["nonwhitespace_source_coverage_complete"] is True

    obligations = contract["acceptance_contract"]["obligations"]
    assert len(obligations) == len(raw_segments)
    req_index = contract["positive_structured_requirement_index"]
    assert req_index["segment_count"] == len(raw_segments)

    for i, ((start, end, segment), obligation) in enumerate(zip(raw_segments, obligations)):
        assert obligation["segment_index"] == i
        assert obligation["span"] == [start, end]
        assert obligation["text"] == segment

    for row in list(req_index["modal_obligations"]) + list(req_index["imperative_directives"]):
        idx = row["segment_index"]
        assert row["segment_span"] == obligations[idx]["span"]


def test_exact_rank17_failure_shape_positions_396_397_398_are_covered() -> None:
    # Old segmentation missed the final standalone ellipsis exactly at these
    # three non-whitespace positions.
    text = ("A" * 395) + "\n..."
    assert [396, 397, 398] == sorted(
        _nonwhitespace_positions(text) - _covered_positions(
            text,
            # Recreate the old sentence-leading-only segmentation.
            [(0, 395, "A" * 395)],
        )
    )
    _assert_lossless_and_aligned(text)


def test_standalone_punctuation_lines_remain_exact_raw_obligations() -> None:
    _assert_lossless_and_aligned("Header.\n...\nDo this!\n???\n")
    _assert_lossless_and_aligned("?\nA.\n!\nB")
    _assert_lossless_and_aligned("!!!")


def test_ordinary_sentence_segmentation_stays_stable() -> None:
    text = "Alpha. Beta?\nGamma!"
    expected = [
        (0, 6, "Alpha."),
        (7, 12, "Beta?"),
        (13, 19, "Gamma!"),
    ]
    assert raw_contract._segments(text) == expected
    assert requirement_index._segments(text) == expected
    _assert_lossless_and_aligned(text)


if __name__ == "__main__":
    test_exact_rank17_failure_shape_positions_396_397_398_are_covered()
    test_standalone_punctuation_lines_remain_exact_raw_obligations()
    test_ordinary_sentence_segmentation_stays_stable()
    print("PASS__LOSSLESS_RAW_TASK_PUNCTUATION_COVERAGE_AND_INDEX_ALIGNMENT")
