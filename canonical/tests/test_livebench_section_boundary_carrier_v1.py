import re

from canonical.runtime.livebench_legacy15_general_composer_v1 import compose_visible_prompt


def _public_prompt(*descriptions: str) -> str:
    return (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "Synthetic public article text.\n"
        "-------\n"
        "Please summarize based on the sentences provided. "
        + " ".join(descriptions)
    )


def test_multiple_sections_uses_compact_checker_valid_carrier():
    prompt = _public_prompt(
        "Your response must have 2 sections. Mark the beginning of each section with Section X, such as:\n"
        "Section 1\n"
        "[content of section 1]\n"
        "Section 2\n"
        "[content of section 2]",
        "Do not include keywords ['section'] in the response.",
    )
    result = compose_visible_prompt(prompt)

    assert result["status"] == "PASS_CANDIDATE_GENERAL_BRANCH"
    response = result["response"]
    assert "Section1" in response
    assert "Section2" in response

    # Exact frozen checker geometry: optional whitespace around the numeric index.
    assert len(re.split(r"\s?Section\s?\d+\s?", response)) - 1 >= 2
    # Exact frozen ForbiddenWords geometry: whole-word match only.
    assert re.search(r"\bsection\b", response, flags=re.IGNORECASE) is None
