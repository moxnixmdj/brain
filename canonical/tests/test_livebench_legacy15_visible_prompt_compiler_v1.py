from __future__ import annotations

import pytest

from canonical.runtime import livebench_legacy15_visible_prompt_compiler_v1 as c


def _prompt(descriptions, *, article="Article text.", task=None):
    task = task or c.TASK_PROMPTS[0]
    base = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        + article
        + "\n-------\n"
        + task
        + " "
    )
    return base + "".join(" " + d for d in descriptions)


def _desc(iid, **slots):
    if iid == c.EXIST:
        return f"Include keywords {sorted(slots['keywords'])} in the response."
    if iid == c.FORBIDDEN:
        return (
            f"Do not include keywords {sorted(slots['forbidden_words'])} "
            "in the response."
        )
    if iid == c.PARAGRAPHS:
        return (
            f"There should be {slots['num_paragraphs']} paragraphs. "
            "Paragraphs are separated with the markdown divider: ***"
        )
    if iid == c.WORDS:
        return (
            f"Answer with {slots['relation']} {slots['num_words']} words."
        )
    if iid == c.SENTENCES:
        return (
            "Your response should contain "
            f"{slots['relation']} {slots['num_sentences']} sentences."
        )
    if iid == c.NTH:
        return (
            f"There should be {slots['num_paragraphs']} paragraphs. "
            "Paragraphs and only paragraphs are separated with each other by two "
            "new lines as if it was '\\n\\n' in python. "
            f"Paragraph {slots['nth_paragraph']} must start with word "
            f"{slots['first_word'].lower()}."
        )
    if iid == c.POSTSCRIPT:
        return (
            "At the end of your response, please explicitly add a postscript "
            f"starting with {slots['postscript_marker']}"
        )
    if iid == c.BULLETS:
        return (
            f"Your answer must contain exactly {slots['num_bullets']} bullet points. "
            "Use the markdown bullet points such as:\n"
            "* This is point 1. \n"
            "* This is point 2"
        )
    if iid == c.TITLE:
        return (
            "Your answer must contain a title, wrapped in double angular brackets, "
            "such as <<poem of joy>>."
        )
    if iid == c.SECTIONS:
        splitter = slots["section_spliter"]
        return (
            f"Your response must have {slots['num_sections']} sections. "
            f"Mark the beginning of each section with {splitter} X, such as:\n"
            f"{splitter} 1\n"
            "[content of section 1]\n"
            f"{splitter} 2\n"
            "[content of section 2]"
        )
    if iid == c.JSON_ID:
        return (
            "Entire output should be wrapped in JSON format. You can use markdown "
            "ticks such as " + "\x60\x60\x60" + "."
        )
    if iid == c.REPEAT:
        return (
            "First repeat the request word for word without change, then give your "
            "answer (1. do not say any words or characters before repeating the "
            "request; 2. the request you need to repeat does not include this sentence)"
        )
    if iid == c.TWO:
        return (
            "Give two different responses. Responses and only responses should "
            "be separated by 6 asterisk symbols: ******."
        )
    if iid == c.END:
        return (
            "Finish your response with this exact phrase "
            f"{slots['end_phrase']}. No other words should follow this phrase."
        )
    if iid == c.QUOTE:
        return "Wrap your entire response with double quotation marks."
    raise AssertionError(iid)


def _one(iid, **slots):
    out = c.compile_visible_prompt(_prompt([_desc(iid, **slots)]))
    assert out["descriptor_count"] == 1
    return out["contracts"][0]


def test_every_fixed_and_discrete_descriptor_family():
    words = ["alpha", "bridge", "cloud", "dream", "energy"]
    assert _one(c.EXIST, keywords=words)["slots"]["keywords"] == words
    assert _one(c.FORBIDDEN, forbidden_words=words)["slots"]["forbidden_words"] == words

    for n in range(1, 6):
        assert _one(c.PARAGRAPHS, num_paragraphs=n)["slots"]["num_paragraphs"] == n
        assert _one(c.BULLETS, num_bullets=n)["slots"]["num_bullets"] == n
        for splitter in ("Section", "SECTION"):
            slots = _one(
                c.SECTIONS,
                section_spliter=splitter,
                num_sections=n,
            )["slots"]
            assert slots == {
                "section_spliter": splitter,
                "num_sections": n,
            }

    for marker in ("P.S.", "P.P.S"):
        assert _one(c.POSTSCRIPT, postscript_marker=marker)["slots"] == {
            "postscript_marker": marker
        }

    for phrase in (
        "Any other questions?",
        "Is there anything else I can help with?",
    ):
        assert _one(c.END, end_phrase=phrase)["slots"] == {
            "end_phrase": phrase
        }

    for iid in (c.TITLE, c.JSON_ID, c.TWO, c.QUOTE):
        assert _one(iid)["slots"] == {}


def test_every_public_word_and_sentence_threshold():
    for relation in ("less than", "at least"):
        for n in range(100, 501):
            assert _one(c.WORDS, num_words=n, relation=relation)["slots"] == {
                "num_words": n,
                "relation": relation,
            }

        for n in range(1, 21):
            assert _one(
                c.SENTENCES,
                num_sentences=n,
                relation=relation,
            )["slots"] == {
                "num_sentences": n,
                "relation": relation,
            }


def test_every_nth_location():
    for paragraphs in range(1, 6):
        for nth in range(1, paragraphs + 1):
            slots = _one(
                c.NTH,
                num_paragraphs=paragraphs,
                nth_paragraph=nth,
                first_word="River",
            )["slots"]
            assert slots == {
                "num_paragraphs": paragraphs,
                "nth_paragraph": nth,
                "first_word": "river",
            }


def test_five_descriptor_suffix_composes_without_hidden_metadata():
    rows = [
        (c.EXIST, {"keywords": ["alpha", "bridge", "cloud", "dream", "energy"]}),
        (c.WORDS, {"num_words": 500, "relation": "at least"}),
        (c.POSTSCRIPT, {"postscript_marker": "P.S."}),
        (c.END, {"end_phrase": "Any other questions?"}),
        (c.QUOTE, {}),
    ]
    prompt = _prompt([_desc(iid, **slots) for iid, slots in rows])
    out = c.compile_visible_prompt(prompt)
    assert out["instruction_ids"] == [iid for iid, _ in rows]
    assert out["terminal_rows_used"] is False
    assert out["hidden_kwargs_used"] is False


def test_repeat_prompt_reconstructs_historical_split_semantics_exactly():
    marker = c.REPEAT_MARKER
    article = "Prefix " + marker + " collision inside article."
    descriptions = [
        _desc(c.EXIST, keywords=["alpha", "bridge", "cloud", "dream", "energy"]),
        _desc(c.REPEAT),
        _desc(c.TITLE),
    ]
    prompt = _prompt(descriptions, article=article)
    out = c.compile_visible_prompt(prompt)
    repeat = next(
        row for row in out["contracts"] if row["instruction_id"] == c.REPEAT
    )
    assert repeat["slots"]["prompt_to_repeat"] == prompt.split(marker, 1)[0]


def test_all_four_historical_task_prompts_are_accepted():
    descriptor = _desc(c.QUOTE)
    for task in c.TASK_PROMPTS:
        out = c.compile_visible_prompt(_prompt([descriptor], task=task))
        assert out["instruction_ids"] == [c.QUOTE]


def test_fail_closed_on_incompatible_or_outside_domain_suffixes():
    with pytest.raises(c.PromptCompileError, match="INCOMPATIBLE"):
        c.compile_visible_prompt(_prompt([_desc(c.TITLE), _desc(c.QUOTE)]))

    bad = _prompt(["Answer with less than 999 words."])
    with pytest.raises(c.PromptCompileError, match="WORD_THRESHOLD_OUTSIDE"):
        c.compile_visible_prompt(bad)

    with pytest.raises(c.PromptCompileError, match="NO_ACTIVE15_DESCRIPTOR_SUFFIX"):
        c.compile_visible_prompt("not a historical generated prompt")
