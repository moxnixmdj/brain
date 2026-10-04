#!/usr/bin/env python3
from canonical.runtime import livebench_legacy_ifeval_description_inverter_v1 as inv


CASES = {
    "keywords:existence":
        "Include keywords ['alpha', 'beta'] in the response.",
    "keywords:frequency":
        "In your response, the word alpha should appear at least 3 times.",
    "keywords:forbidden_words":
        "Do not include keywords ['alpha', 'beta'] in the response.",
    "keywords:letter_frequency":
        "In your response, the letter x should appear less than 7 times.",
    "language:response_language":
        "Your ENTIRE response should be in English language, no other language is allowed.",
    "length_constraints:number_sentences":
        "Your response should contain at least 4 sentences.",
    "length_constraints:number_paragraphs":
        "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
    "length_constraints:number_words":
        "Answer with less than 120 words.",
    "length_constraints:nth_paragraph_first_word":
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other "
        "by two new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word alpha.",
    "detectable_content:number_placeholders":
        "The response must contain at least 3 placeholders represented by square brackets, such as [address].",
    "detectable_content:postscript":
        "At the end of your response, please explicitly add a postscript starting with P.S.",
    "detectable_format:number_bullet_lists":
        "Your answer must contain exactly 4 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2",
    "detectable_format:constrained_response":
        "Answer with one of the following options: My answer is yes., My answer is no., My answer is maybe.",
    "detectable_format:number_highlighted_sections":
        "Highlight at least 3 sections in your answer with markdown, i.e. *highlighted section*.",
    "detectable_format:multiple_sections":
        "Your response must have 3 sections. Mark the beginning of each section with Section X, such as:\n"
        "Section 1\n[content of section 1]",
    "detectable_format:json_format":
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as ```.",
    "detectable_format:title":
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
    "combination:two_responses":
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
    "combination:repeat_prompt":
        "Explain gravity.\n-------\n"
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)",
    "startend:end_checker":
        "Finish your response with this exact phrase Any other questions?. "
        "No other words should follow this phrase.",
    "change_case:capital_word_frequency":
        "In your response, words with all capital letters should appear at least 5 times.",
    "change_case:english_capital":
        "Your entire response should be in English, and in all capital letters.",
    "change_case:english_lowercase":
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
    "punctuation:no_comma":
        "In your entire response, refrain from the use of any commas.",
    "startend:quotation":
        'Wrap your entire response with double quotation marks.',
}


def test_registry_count_and_identity():
    assert len(inv.ENABLED_INSTRUCTION_IDS) == 25
    assert len(set(inv.ENABLED_INSTRUCTION_IDS)) == 25
    assert set(CASES) == set(inv.ENABLED_INSTRUCTION_IDS)


def test_every_source_description_is_inverted():
    for instruction_id, prompt in CASES.items():
        matches = inv.recognize(prompt)
        ids = [m["instruction_id"] for m in matches]
        assert instruction_id in ids, (instruction_id, ids, prompt)


def test_parameter_recovery():
    m = inv.recognize(CASES["keywords:existence"])[0]
    assert m["slots"]["keywords"] == ["alpha", "beta"]

    m = inv.recognize(CASES["keywords:frequency"])[0]
    assert m["slots"] == {"keyword": "alpha", "relation": "at least", "frequency": 3}

    m = inv.recognize(CASES["language:response_language"])[0]
    assert m["slots"]["language"] == "en"

    m = inv.recognize(CASES["length_constraints:nth_paragraph_first_word"])[0]
    assert m["slots"]["num_paragraphs"] == 3
    assert m["slots"]["nth_paragraph"] == 2
    assert m["slots"]["first_word"] == "alpha"

    m = inv.recognize(CASES["combination:repeat_prompt"])[0]
    assert m["slots"]["prompt_to_repeat"] == "Explain gravity."

    m = inv.recognize(CASES["startend:end_checker"])[0]
    assert m["slots"]["end_phrase"] == "Any other questions?"


def test_multi_constraint_prompt_preserves_all_recognized_constraints():
    prompt = (
        "Base request.\n-------\n"
        + CASES["keywords:existence"] + "\n"
        + CASES["length_constraints:number_words"] + "\n"
        + CASES["punctuation:no_comma"]
    )
    ids = {m["instruction_id"] for m in inv.recognize(prompt)}
    assert ids == {
        "keywords:existence",
        "length_constraints:number_words",
        "punctuation:no_comma",
    }


def test_unknown_text_fails_closed_to_zero_matches():
    assert inv.recognize("Invent a beautiful theory of everything.") == []
