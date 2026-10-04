import json

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
    assert all("omega" not in x.lower() for x in out["candidates"])


def test_conflicting_mode_fails_closed():
    out = g.generate([
        c("detectable_format:json_format"),
        c("length_constraints:number_words", num_words=100, relation="at least"),
    ])
    assert out["status"] == "FAIL_CLOSED"
    assert out["candidates"] == []
