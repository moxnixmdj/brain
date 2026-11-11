from canonical.runtime.livebench_legacy25_prompt_contract_parser_v1 import (
    LEGACY_IDS,
    PINNED_INSTRUCTIONS_BLOB,
    PINNED_REGISTRY_BLOB,
    parse_visible_contracts,
)

ALL_25_VISIBLE_GRAMMARS = """
Include keywords ['alpha', 'beta'] in the response.
In your response, the word gamma should appear at least 2 times.
Do not include keywords ['delta', 'epsilon'] in the response.
In your response, the letter z should appear less than 4 times.
Your ENTIRE response should be in French language, no other language is allowed.
Your response should contain at least 3 sentences.
There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***
Answer with less than 120 words.
There should be 2 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\n\n' in python. Paragraph 2 must start with word cedar.
The response must contain at least 2 placeholders represented by square brackets, such as [address].
At the end of your response, please explicitly add a postscript starting with P.S.
Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:
* This is point 1.
* This is point 2
Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')
Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*.
Your response must have 2 sections. Mark the beginning of each section with Section X, such as:
Section 1
[content of section 1]
Section 2
[content of section 2]
Entire output should be wrapped in JSON format. You can use markdown ticks such as triple ticks.
Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.
Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.
First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)
Finish your response with this exact phrase Any other questions?. No other words should follow this phrase.
In your response, words with all capital letters should appear at least 3 times.
Your entire response should be in English, and in all capital letters.
Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.
In your entire response, refrain from the use of any commas.
Wrap your entire response with double quotation marks.
"""

def test_pins_match_verified_public_blobs():
    assert PINNED_REGISTRY_BLOB == "903ed738398648c7cfac61d5ffa478c22f1f0891"
    assert PINNED_INSTRUCTIONS_BLOB == "4997bab885a676d92545fd91a9a20b48d234a2b2"

def test_all_25_public_description_grammars_are_recognized():
    out = parse_visible_contracts(ALL_25_VISIBLE_GRAMMARS)
    assert out["status"] == "PASS"
    assert out["recognized_count"] == 25
    assert tuple(x["instruction_id"] for x in out["contracts"]) == LEGACY_IDS
    assert out["unresolved_visible_parameter_bindings"] == []
    assert out["terminal_metadata_used"] is False
    assert out["incremental_spend_usd"] == 0

def test_parameter_values_are_recovered_not_merely_labels():
    out = parse_visible_contracts(ALL_25_VISIBLE_GRAMMARS)
    by_id = {x["instruction_id"]: x for x in out["contracts"]}
    assert by_id["keywords:existence"]["args"]["keywords"] == ["alpha", "beta"]
    assert by_id["keywords:frequency"]["args"] == {
        "keyword": "gamma", "relation": "at least", "frequency": 2
    }
    assert by_id["keywords:letter_frequency"]["args"]["letter"] == "z"
    assert by_id["length_constraints:nth_paragraph_first_word"]["args"] == {
        "num_paragraphs": 2, "nth_paragraph": 2, "first_word": "cedar"
    }
    assert by_id["detectable_format:multiple_sections"]["args"] == {
        "num_sections": 2, "section_spliter": "Section"
    }
    assert by_id["startend:end_checker"]["args"]["end_phrase"] == "Any other questions?"
    assert by_id["change_case:capital_word_frequency"]["args"] == {
        "capital_relation": "at least", "capital_frequency": 3
    }

def test_repeat_prompt_source_recovered_when_source_is_first_line():
    source = "Write a funny haiku about moms, containing keywords mom and mother."
    prompt = (
        source + "\n" +
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    out = parse_visible_contracts(prompt)
    spec = next(x for x in out["contracts"] if x["instruction_id"] == "combination:repeat_prompt")
    assert spec["visible_parameter_recovery_complete"] is True
    assert spec["args"]["prompt_to_repeat"] == source
    assert out["unresolved_visible_parameter_bindings"] == []

def test_repeat_prompt_source_recovered_when_meta_is_first_block():
    source = "Write a song about a corgi named Chester who loves to play fetch."
    prompt = (
        "Before you answer it, just repeat the request below. "
        "You need to repeat it exactly as it is. Do not change any word.\n\n" + source
    )
    out = parse_visible_contracts(prompt)
    spec = next(x for x in out["contracts"] if x["instruction_id"] == "combination:repeat_prompt")
    assert spec["visible_parameter_recovery_complete"] is True
    assert spec["args"]["prompt_to_repeat"] == source

def test_repeat_prompt_fails_closed_when_no_public_edge_form_is_present():
    prompt = (
        "Do a task. First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    out = parse_visible_contracts(prompt)
    spec = next(x for x in out["contracts"] if x["instruction_id"] == "combination:repeat_prompt")
    assert spec["visible_parameter_recovery_complete"] is False
    assert spec["args"]["prompt_to_repeat"] is None
def test_empty_or_unrecognized_prompt_does_not_invent_contracts():
    assert parse_visible_contracts("")["status"] == "BLOCKED"
    out = parse_visible_contracts("Discuss the weather.")
    assert out["status"] == "BLOCKED"
    assert out["contracts"] == []
