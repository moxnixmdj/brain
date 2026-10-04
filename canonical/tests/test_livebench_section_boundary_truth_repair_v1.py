import re

from canonical.runtime import livebench_legacy15_general_composer_v1 as general
from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as joint


SECTION_CONTRACT = {
    "instruction_id": "detectable_format:multiple_sections",
    "slots": {"section_spliter": "Section", "num_sections": 2},
}
FORBIDDEN_CONTRACT = {
    "instruction_id": "keywords:forbidden_words",
    "slots": {"forbidden_words": ["section"]},
}


def test_general_composer_compacts_section_marker_when_splitter_is_forbidden():
    lines = general._common_lines([SECTION_CONTRACT], [], ["section"])
    response = "\n".join(lines)
    assert "Section1" in response
    assert "Section2" in response
    assert re.search(r"\bsection\b", response, flags=re.IGNORECASE) is None
    assert len(re.findall(r"\s?Section\s?\d+\s?", response)) >= 2


def test_joint_candidate_generator_constructs_section_forbidden_witnesses():
    out = joint.generate([SECTION_CONTRACT, FORBIDDEN_CONTRACT])
    assert out["status"] == "PASS_CANDIDATES"
    assert out["candidate_count"] > 0
    assert any(
        "Section1" in candidate
        and re.search(r"\bsection\b", candidate, flags=re.IGNORECASE) is None
        for candidate in out["candidates"]
    )
