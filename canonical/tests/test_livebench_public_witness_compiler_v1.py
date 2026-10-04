#!/usr/bin/env python3
import pytest

from canonical.runtime.livebench_public_witness_compiler_v1 import compile_witness


@pytest.mark.parametrize(
    "prompt,checker",
    [
        ("Task. Answer with at least 7 words.", "legacy:NumberOfWords"),
        ("Task. Your response should contain at least 3 sentences.", "legacy:NumberOfSentences"),
        (
            "Task. There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
            "legacy:ParagraphChecker",
        ),
        ("Task. Entire output should be wrapped in JSON format.", "legacy:JsonFormat"),
        (
            "Task. Answer with one of the following options: ['Alpha', 'Beta']",
            "legacy:ConstrainedResponseChecker",
        ),
        ("Task. Wrap your entire response with double quotation marks.", "legacy:QuotationChecker"),
        ("Task. The response must contain between 8 and 11 words.", "modern:WordCountRangeChecker"),
        (
            "Task. Include exactly 4 numbers in the response; do not use commas within the numbers.",
            "modern:NumbersCountChecker",
        ),
        ("Task. The output should not contain any whitespace.", "modern:NoWhitespaceChecker"),
        (
            "Task. Write the entire response in title case (capitalize the first letter of every word).",
            "modern:TitleCaseChecker",
        ),
        (
            "Task. Use this exact template for your response: My Answer: [answer] My Conclusion: [conclusion] Future Outlook: [outlook]",
            "modern:OutputTemplateChecker",
        ),
        (
            "Task. Answer with a newline-separated list of items, instead of bullet points use SEPARATOR.",
            "modern:SpecialBulletPointsChecker",
        ),
        (
            "Task. Finish your response with this exact phrase THE END. No other words should follow this phrase.",
            "legacy:EndChecker",
        ),
        (
            "Task. In your entire response, refrain from the use of any commas.",
            "legacy:CommaChecker",
        ),
        (
            "Task. Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
            "legacy:TitleChecker",
        ),
        ("Task. Include keywords ['alpha', 'beta'] in the response.", "legacy:KeywordChecker"),
        ("Task. Do not include keywords ['forbidden', 'ban'] in the response.", "legacy:ForbiddenWords"),
        (
            "Task. In your response, the word alpha should appear at least 3 times.",
            "legacy:KeywordFrequencyChecker",
        ),
        ("Task. Your answer must contain exactly 4 bullet points.", "legacy:BulletListChecker"),
        (
            "Task. Highlight at least 3 sections in your answer with markdown, i.e. *highlighted section*.",
            "legacy:HighlightSectionChecker",
        ),
        (
            "Task. At the end of your response, please explicitly add a postscript starting with P.S.",
            "legacy:PostscriptChecker",
        ),
    ],
)
def test_public_single_checker_witnesses(prompt, checker):
    out = compile_witness(prompt)
    assert out["status"] == "PASS", out
    assert out["matched_checkers"] == [checker]
    assert isinstance(out["response"], str) and out["response"]
    assert out["terminal_case_content_used"] is False
    assert out["hidden_metadata_used"] is False
    assert out["network_used"] is False
    assert out["incremental_spend_usd"] == 0
    assert out["model_dependency_count"] == 0
    assert out["terminal_authority"] is False


def test_unknown_description_fails_closed():
    out = compile_witness("Task. Use an unsupported public instruction form.")
    assert out["status"] == "BLOCKED"
    assert out["reason"] == "NO_SUPPORTED_PUBLIC_DESCRIPTION"


def test_multi_checker_fails_closed():
    out = compile_witness(
        "Task. Answer with at least 5 words. "
        "Wrap your entire response with double quotation marks."
    )
    assert out["status"] == "BLOCKED"
    assert out["reason"] == "MULTI_CHECKER_COMBINATION_NOT_PROVED"
    assert len(out["matched_checkers"]) == 2
