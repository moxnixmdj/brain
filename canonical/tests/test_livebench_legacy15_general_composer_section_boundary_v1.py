import re

from canonical.runtime import livebench_legacy15_general_composer_v1 as composer


def test_section_splitter_can_coexist_with_same_forbidden_word():
    prompt = (
        "Synthetic public source text.\n"
        "-------\n"
        "Your response must have 2 sections. Mark the beginning of each section "
        "with Section X, such as: "
        "Do not include keywords ['section'] in the response."
    )
    out = composer.compose_visible_prompt(prompt)
    assert out["status"] == "PASS_CANDIDATE_GENERAL_BRANCH"
    response = out["response"]
    assert re.search(r"\bsection\b", response, flags=re.IGNORECASE) is None
    assert len(re.findall(r"Section\d+", response)) >= 2
