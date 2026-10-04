from canonical.runtime.legacy_ifeval_visible_constraint_compiler_v1 import compile_visible_constraints, kinds


def test_all_25_public_legacy_checker_templates_parse_without_terminal_data():
    prompt = "\n".join([
        "Include keywords ['amber', 'birch'] in the response.",
        "In your response, the word cedar should appear at least 2 times.",
        "Do not include keywords ['delta', 'ember'] in the response.",
        "In your response, the letter q should appear less than 7 times.",
        "Your ENTIRE response should be in English language, no other language is allowed.",
        "Your response should contain at least 3 sentences.",
        "There should be 2 paragraphs. Paragraphs are separated with the markdown divider: ***",
        "Answer with less than 50 words.",
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word frost.",
        "The response must contain at least 2 placeholders represented by square brackets, such as [address].",
        "At the end of your response, please explicitly add a postscript starting with P.S.",
        "Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as:\n* This is point 1. \n* This is point 2",
        "Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')",
        "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*.",
        "Your response must have 2 sections. Mark the beginning of each section with Section X, such as:\nSection 1\n[content of section 1]\nSection 2\n[content of section 2]",
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as \`\`\`.",
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
        "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)",
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase.",
        "In your response, words with all capital letters should appear at least 4 times.",
        "Your entire response should be in English, and in all capital letters.",
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
        "In your entire response, refrain from the use of any commas.",
        "Wrap your entire response with double quotation marks.",
    ])
    parsed = compile_visible_constraints(prompt)
    assert len({c.kind for c in parsed}) == 25


def test_parameter_extraction_is_exact_for_representative_templates():
    prompt = "\n".join([
        "Include keywords ['beta', 'alpha'] in the response.",
        "In your response, the word orbit should appear at least 3 times.",
        "Finish your response with this exact phrase Done now. No other words should follow this phrase.",
    ])
    parsed = {c.kind: c.params for c in compile_visible_constraints(prompt)}
    assert parsed["keywords:existence"]["keywords"] == ["beta", "alpha"]
    assert parsed["keywords:frequency"] == {"keyword": "orbit", "relation": "at least", "frequency": 3}
    assert parsed["startend:end_checker"]["end_phrase"] == "Done now"


def test_repeat_prompt_derivation_uses_visible_text_only():
    instruction = "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)"
    prompt = "Write a concise description. " + instruction
    parsed = [c for c in compile_visible_constraints(prompt) if c.kind == "combination:repeat_prompt"]
    assert len(parsed) == 1
    assert parsed[0].params["prompt_to_repeat"] == "Write a concise description."


def test_no_constraint_text_does_not_hallucinate_types():
    assert kinds("Write a useful answer.") == ()
