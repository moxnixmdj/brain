import re

from canonical.runtime import livebench_legacy15_general_composer_v1 as c


def _section_contract(n: int = 2):
    return [{
        "instruction_id": "detectable_format:multiple_sections",
        "slots": {"section_spliter": "Section", "num_sections": n},
    }]


def test_section_forbidden_word_uses_boundary_safe_numeric_join():
    lines = c._common_lines(_section_contract(), [], ["section"])
    assert lines[:4] == ["Section1", "zxqv", "Section2", "zxqv"]

    value = "\n".join(lines)
    # Exact pinned SectionChecker shape: optional whitespace around splitter,
    # then digits. Zero whitespace is accepted.
    pieces = re.split(r"\s?Section\s?\d+\s?", value)
    assert len(pieces) - 1 == 2

    # Exact pinned ForbiddenWords shape requires whole-word boundaries.
    assert re.search(r"\bsection\b", value, flags=re.IGNORECASE) is None


def test_section_noncollision_keeps_readable_spaced_form():
    lines = c._common_lines(_section_contract(), [], ["market"])
    assert lines[:4] == ["Section 1", "zxqv", "Section 2", "zxqv"]
