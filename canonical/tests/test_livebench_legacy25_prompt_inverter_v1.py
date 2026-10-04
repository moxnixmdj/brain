from canonical.runtime.livebench_legacy25_prompt_inverter_v1 import (
    LEGACY_INSTRUCTION_IDS,
    recognize,
)


def _all_descriptions() -> str:
    return "\n".join([
        "Include keywords ['alpha', 'beta'] in the response.",
        "In your response, the word gamma should appear at least 3 times.",
        "Do not include keywords ['delta', 'epsilon'] in the response.",
        "In your response, the letter q should appear less than 4 times.",
        "Your ENTIRE response should be in French language, no other language is allowed.",
        "Your response should contain at least 3 sentences.",
        "There should be 2 paragraphs. Paragraphs are separated with the markdown divider: ***",
        "Answer with less than 100 words.",
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word anchor.",
        "The response must contain at least 2 placeholders represented by square brackets, such as [address].",
        "At the end of your response, please explicitly add a postscript starting with P.S.",
        "Your answer must contain exactly 4 bullet points. Use the markdown bullet points such as:",
        "Answer with one of the following options: ['My answer is yes.', 'My answer is no.', 'My answer is maybe.']",
        "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*.",
        "Your response must have 3 sections. Mark the beginning of each section with SECTION X, such as:",
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as code fences.",
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
        "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)",
        "Finish your response with this exact phrase The End. No other words should follow this phrase.",
        "In your response, words with all capital letters should appear at least 5 times.",
        "Your entire response should be in English, and in all capital letters.",
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
        "In your entire response, refrain from the use of any commas.",
        "Wrap your entire response with double quotation marks.",
    ])


def test_recognizes_all_25_pinned_legacy_types_from_visible_descriptions():
    result = recognize(_all_descriptions())
    assert result["status"] == "PASS"
    assert result["recognized_instruction_type_count"] == 25
    assert set(result["recognized_instruction_ids"]) == set(LEGACY_INSTRUCTION_IDS)
    assert not result["hidden_instruction_id_list_read"]
    assert not result["hidden_kwargs_read"]


def test_recovers_rendered_parameters():
    result = recognize(_all_descriptions())
    by_id = {m["instruction_id"]: m for m in result["matches"]}
    assert by_id["keywords:existence"]["kwargs"]["keywords"] == ["alpha", "beta"]
    assert by_id["keywords:frequency"]["kwargs"] == {
        "keyword": "gamma",
        "frequency": 3,
        "relation": "at least",
    }
    assert by_id["language:response_language"]["kwargs"]["language"] == "fr"
    assert by_id["length_constraints:nth_paragraph_first_word"]["kwargs"] == {
        "num_paragraphs": 3,
        "nth_paragraph": 2,
        "first_word": "anchor",
    }
    assert by_id["detectable_format:multiple_sections"]["kwargs"] == {
        "section_spliter": "SECTION",
        "num_sections": 3,
    }
    assert by_id["startend:end_checker"]["kwargs"]["end_phrase"] == "The End"
    assert by_id["combination:repeat_prompt"]["kwargs"]["prompt_to_repeat"] is None
    assert by_id["combination:repeat_prompt"]["kwargs"]["prompt_to_repeat_recovery"] == "VISIBLE_PROMPT_RECOVERY_REQUIRED"


def test_unknown_language_fails_closed_by_not_claiming_recognition():
    result = recognize("Your ENTIRE response should be in Klingon language, no other language is allowed.")
    assert "language:response_language" not in result["recognized_instruction_ids"]


def test_duplicate_same_type_is_flagged_ambiguous():
    prompt = (
        "Answer with at least 5 words.\n"
        "Answer with less than 20 words."
    )
    result = recognize(prompt)
    assert result["status"] == "AMBIGUOUS_FAIL_CLOSED"
    assert result["ambiguous_instruction_ids"] == ["length_constraints:number_words"]
