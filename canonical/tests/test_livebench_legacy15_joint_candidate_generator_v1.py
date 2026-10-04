import json
import re

from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as g


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_json_mode_is_valid_json_and_carries_keywords():
    out = g.generate([
        c("detectable_format:json_format"),
        c("keywords:existence", keywords=["alpha", "beta"]),
        c("keywords:forbidden_words", forbidden_words=["omega"]),
    ])
    assert out["mode"] == "JSON"
    assert out["candidates"]
    for x in out["candidates"]:
        json.loads(x)
        assert "alpha" in x and "beta" in x
        assert "omega" not in x.lower()


def test_repeat_mode_starts_with_recovered_prompt():
    base = "visible request prefix"
    out = g.generate([
        c("combination:repeat_prompt", prompt_to_repeat=base),
        c("detectable_format:title"),
        c("keywords:existence", keywords=["alpha"]),
    ])
    assert out["mode"] == "REPEAT"
    assert out["candidates"][0].startswith(base)
    assert "<<x>>" in out["candidates"][0]
    assert "alpha" in out["candidates"][0]


def test_two_response_mode_has_exact_delimiter():
    out = g.generate([
        c("combination:two_responses"),
        c("detectable_format:title"),
        c("keywords:existence", keywords=["alpha"]),
        c("keywords:forbidden_words", forbidden_words=["omega"]),
    ])
    x = out["candidates"][0]
    parts = [p.strip() for p in x.split("******") if p.strip()]
    assert len(parts) == 2
    assert parts[0] != parts[1]
    assert "alpha" in x


def test_core_mode_emits_bounded_candidates():
    out = g.generate([
        c("keywords:existence", keywords=["alpha"]),
        c("keywords:forbidden_words", forbidden_words=["omega"]),
        c("length_constraints:number_sentences", num_sentences=4, relation="at least"),
        c("length_constraints:number_words", num_words=100, relation="at least"),
        c("detectable_content:postscript", postscript_marker="P.S."),
        c("detectable_format:number_bullet_lists", num_bullets=2),
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=2),
        c("startend:end_checker", end_phrase="Any other questions?"),
        c("startend:quotation"),
    ])
    assert out["mode"] == "CORE"
    assert 1 <= out["candidate_count"] <= 96
    assert all(x.startswith('"') and x.endswith('"') for x in out["candidates"])
    assert all(x[1:-1].rstrip().endswith("Any other questions?") for x in out["candidates"])
    assert all(len(re.findall(r"\\w+", x)) >= 100 for x in out["candidates"])
    assert all("omega" not in x.lower() for x in out["candidates"])


def test_conflicting_mode_fails_closed():
    out = g.generate([
        c("detectable_format:json_format"),
        c("length_constraints:number_words", num_words=100, relation="at least"),
    ])
    assert out["status"] == "FAIL_CLOSED"
    assert out["candidates"] == []


def test_paragraph_mode_keeps_terminal_material_at_true_response_end():
    out = g.generate([
        c("length_constraints:number_paragraphs", num_paragraphs=3),
        c("length_constraints:number_words", num_words=40, relation="at least"),
        c("detectable_content:postscript", postscript_marker="P.S."),
        c("startend:end_checker", end_phrase="Any other questions?"),
        c("startend:quotation"),
    ])
    assert out["candidates"]
    for x in out["candidates"]:
        assert x.startswith('"') and x.endswith('"')
        inner = x[1:-1]
        assert inner.rstrip().endswith("Any other questions?")
        assert len(re.split(r"\\s?\\*\\*\\*\\s?", inner)) == 3
        assert len(re.findall(r"\\w+", x)) >= 40


def test_required_forbidden_same_word_uses_satisfiable_substring_escape():
    out = g.generate([
        c("keywords:existence", keywords=["rock"]),
        c("keywords:forbidden_words", forbidden_words=["rock"]),
    ])
    assert out["candidates"]
    assert any(re.search("rock", x, re.I) for x in out["candidates"])
    assert all(re.search(r"\\brock\\b", x, re.I) is None for x in out["candidates"])


def test_quotation_keeps_exact_bullet_count_visible_to_frozen_regex():
    out = g.generate([
        c("startend:quotation"),
        c("detectable_format:number_bullet_lists", num_bullets=4),
    ])
    assert out["candidates"]
    for x in out["candidates"]:
        assert x.startswith('"') and x.endswith('"')
        bullets = re.findall(r"^\\s*\\*[^\\*].*$", x, flags=re.MULTILINE)
        assert len(bullets) == 4


def test_postscript_payload_avoids_visible_forbidden_word():
    out = g.generate([
        c("keywords:forbidden_words", forbidden_words=["note"]),
        c("detectable_content:postscript", postscript_marker="P.S."),
        c("startend:end_checker", end_phrase="Any other questions?"),
    ])
    assert out["candidates"]
    for x in out["candidates"]:
        assert re.search(r"\\bnote\\b", x, re.I) is None
        assert "P.S." in x
        assert x.rstrip().endswith("Any other questions?")
