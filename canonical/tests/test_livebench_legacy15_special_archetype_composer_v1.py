import json
import re

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_special_archetype_composer_v1 as composer


def c(iid, slots=None):
    return {"instruction_id": iid, "slots": slots or {}, "parameter_complete": True}


def mirror_required(text, words):
    return all(re.search(w, text, flags=re.IGNORECASE) is not None for w in words)


def mirror_forbidden(text, words):
    return all(re.search(r"\b" + w + r"\b", text, flags=re.IGNORECASE) is None for w in words)


def test_structural_cover_is_exactly_16_sets():
    out = composer.verify_structural_cover()
    assert out["covered_structural_set_count"] == 16
    assert out["remaining_structural_set_count"] == 912
    assert out["counts_by_archetype"] == {
        "JSON": 4,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 8,
    }


def test_json_handles_required_forbidden_collision():
    contracts = [
        c(composer.JSON_ID),
        c(composer.EXIST, {"keywords": ["alpha", "beta"]}),
        c(composer.FORBID, {"forbidden_words": ["alpha", "alphax", "omega"]}),
    ]
    out = composer.compose(contracts)
    assert out["status"] == "PASS_CANDIDATE_WITNESS"
    response = out["response"]
    json.loads(response)
    assert mirror_required(response, ["alpha", "beta"])
    assert mirror_forbidden(response, ["alpha", "alphax", "omega"])


def test_repeat_starts_with_exact_visible_prompt_and_satisfies_title_keyword():
    base = "Visible request body\n-------\n"
    contracts = [
        c(composer.REPEAT, {"prompt_to_repeat": base}),
        c(composer.EXIST, {"keywords": ["orchid"]}),
        c(composer.TITLE),
    ]
    out = composer.compose(contracts)
    assert out["status"] == "PASS_CANDIDATE_WITNESS"
    response = out["response"]
    assert response.strip().lower().startswith(base.strip().lower())
    assert re.search("orchid", response, re.IGNORECASE)
    assert re.search(r"<<[^\n]+>>", response)


def test_two_responses_handles_required_forbidden_collision_and_title():
    contracts = [
        c(composer.TWO),
        c(composer.EXIST, {"keywords": ["alpha"]}),
        c(composer.FORBID, {"forbidden_words": ["alpha", "alphax"]}),
        c(composer.TITLE),
    ]
    out = composer.compose(contracts)
    assert out["status"] == "PASS_CANDIDATE_WITNESS"
    response = out["response"]
    parts = response.split("******")
    assert len(parts) == 2
    assert parts[0].strip() and parts[1].strip()
    assert parts[0].strip() != parts[1].strip()
    assert mirror_required(response, ["alpha"])
    assert mirror_forbidden(response, ["alpha", "alphax"])
    assert re.search(r"<<[^\n]+>>", response)


def test_all_16_structural_special_sets_are_dispatchable_with_synthetic_slots():
    for ids in archetypes.enumerate_compatible_sets():
        arch = archetypes.archetype(ids)
        if arch not in composer.SPECIAL_ARCHETYPES:
            continue
        contracts = []
        for iid in ids:
            if iid == composer.EXIST:
                contracts.append(c(iid, {"keywords": ["alpha"]}))
            elif iid == composer.FORBID:
                contracts.append(c(iid, {"forbidden_words": ["alpha"]}))
            elif iid == composer.REPEAT:
                contracts.append(c(iid, {"prompt_to_repeat": "base request"}))
            else:
                contracts.append(c(iid))
        out = composer.compose(contracts)
        assert out["status"] == "PASS_CANDIDATE_WITNESS", (ids, out)
        assert out["archetype"] == arch


def test_non_special_archetype_fails_closed():
    out = composer.compose([c("length_constraints:number_words", {"num_words": 10, "relation": "at least"})])
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"].startswith("OUTSIDE_SPECIAL_ARCHETYPE_SCOPE")
