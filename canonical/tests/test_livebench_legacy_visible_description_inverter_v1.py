from canonical.runtime.livebench_legacy_visible_description_inverter_v1 import (
    ALL_LEGACY_IDS,
    invert_legacy_descriptions,
    registry_coverage,
)


SAMPLES = {
    "keywords:existence": "Include keywords ['alpha', 'beta'] in the response.",
    "keywords:frequency": "In your response, the word alpha should appear at least 3 times.",
    "keywords:forbidden_words": "Do not include keywords ['alpha', 'beta'] in the response.",
    "keywords:letter_frequency": "In your response, the letter q should appear less than 4 times.",
    "language:response_language": "Your ENTIRE response should be in Spanish language, no other language is allowed.",
    "length_constraints:number_sentences": "Your response should contain at least 4 sentences.",
    "length_constraints:number_paragraphs": "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
    "length_constraints:number_words": "Answer with less than 120 words.",
    "length_constraints:nth_paragraph_first_word": (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated "
        "with each other by two new lines as if it was '\\n\\n' in python. "
        "Paragraph 2 must start with word alpha."
    ),
    "detectable_content:number_placeholders": (
        "The response must contain at least 3 placeholders represented by square "
        "brackets, such as [address]."
    ),
    "detectable_content:postscript": (
        "At the end of your response, please explicitly add a postscript starting with P.S."
    ),
    "detectable_format:number_bullet_lists": (
        "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2"
    ),
    "detectable_format:constrained_response": (
        "Answer with one of the following options: ['My answer is yes.', 'My answer is no.']"
    ),
    "detectable_format:number_highlighted_sections": (
        "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*."
    ),
    "detectable_format:multiple_sections": (
        "Your response must have 3 sections. Mark the beginning of each section with "
        "SECTION X, such as:\nSECTION 1\n[content of section 1]\nSECTION 2\n[content of section 2]"
    ),
    "detectable_format:json_format": (
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as "
        + chr(96) * 3 + "."
    ),
    "detectable_format:title": (
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    ),
    "combination:two_responses": (
        "Give two different responses. Responses and only responses should be separated "
        "by 6 asterisk symbols: ******."
    ),
    "combination:repeat_prompt": (
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    ),
    "startend:end_checker": (
        "Finish your response with this exact phrase The end. "
        "No other words should follow this phrase."
    ),
    "change_case:capital_word_frequency": (
        "In your response, words with all capital letters should appear at least 3 times."
    ),
    "change_case:english_capital": (
        "Your entire response should be in English, and in all capital letters."
    ),
    "change_case:english_lowercase": (
        "Your entire response should be in English, and in all lowercase letters. "
        "No capital letters are allowed."
    ),
    "punctuation:no_comma": "In your entire response, refrain from the use of any commas.",
    "startend:quotation": "Wrap your entire response with double quotation marks.",
}


def test_static_registry_coverage_is_25_of_25():
    coverage = registry_coverage()
    assert coverage["complete"] is True
    assert coverage["registry_instruction_count"] == 25
    assert coverage["pattern_instruction_count"] == 25
    assert set(SAMPLES) == set(ALL_LEGACY_IDS)


def test_every_source_family_has_a_synthetic_rendered_description_match():
    for instruction_id, rendered in SAMPLES.items():
        out = invert_legacy_descriptions(rendered)
        assert out["status"] == "PASS__VISIBLE_LEGACY_DESCRIPTIONS_INVERTED"
        assert out["instruction_ids"] == [instruction_id], (instruction_id, out)


def test_composes_multiple_visible_descriptions_without_hidden_metadata():
    prompt = (
        "Explain the topic briefly. "
        + SAMPLES["keywords:existence"] + " "
        + SAMPLES["length_constraints:number_words"] + " "
        + SAMPLES["punctuation:no_comma"]
    )
    out = invert_legacy_descriptions(prompt)
    assert out["matched_instruction_count"] == 3
    assert out["instruction_ids"] == [
        "keywords:existence",
        "length_constraints:number_words",
        "punctuation:no_comma",
    ]
    assert out["hidden_instruction_id_list_read"] is False
    assert out["hidden_kwargs_read"] is False


def test_parameter_inversion_types():
    out = invert_legacy_descriptions(
        "In your response, the word alpha should appear at least 3 times. "
        "There should be 4 paragraphs. Paragraphs are separated with the markdown divider: ***"
    )
    assert out["matches"][0]["kwargs_visible"] == {
        "keyword": "alpha",
        "relation": "at least",
        "frequency": 3,
    }
    assert out["matches"][1]["kwargs_visible"]["num_paragraphs"] == 4
