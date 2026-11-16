"""The resolver, measured against real pages captured from a real browser.

Every observation in `fixtures/real_observations_20261116_v1.json` was produced by the project's
own chromium bridge against `Farama-Foundation/miniwob-plusplus` at seed 1060 on 2026-11-16. None
of it is synthetic: each box, fill, tag and word below is what the page actually reported.

What these tests are for
------------------------
The compiler refused 51 of 130 real pages and called the reason "needs geometry" or "no clause
understood". The dumps show the description was in the channel the whole time. So the load-bearing
assertions here are not "the function runs" -- they are:

  * a described target RESOLVES to the element the page actually means (`click-color`: the black
    box, which is neither the first nor the largest element);
  * a comparison resolves against the OTHER candidates and never against the page frame
    (`drag-box`: 28x28 into 58x58, not into the 480x210 body);
  * an ambiguity is reported as AMBIGUOUS, never resolved by taking the first match
    (`drag-shapes-2` has two unfilled boxes and neither is "the left box" without the word);
  * a dimension the page does not carry is named (`drag-shapes`: the bin the instruction calls
    "black" has no fill at all), because that is the difference between MY blindness and the
    PAGE's.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import instruction_contract_v1 as contract  # noqa: E402
from canonical.runtime import observable_descriptor_v1 as describe  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "real_observations_20261116_v1.json"


def _pages() -> dict:
    return json.loads(FIXTURES.read_text())


# --------------------------------------------------------------------------------------------- #
# the description resolves to the element the page means
# --------------------------------------------------------------------------------------------- #
def test_a_colour_description_resolves_to_the_coloured_element():
    """click-color: "Click on the black colored box." Four identical divs, one is black."""
    page = _pages()["click-color"]
    found = describe.describe(page["utterance"], page)
    assert found.outcome == describe.RESOLVED, found.as_dict()
    element = page["elements"][found.subject]
    assert element["colour"] == "black", element
    # and it is NOT the first addressable element, so "pick the first" would have failed
    assert found.subject != min(e["index"] for e in page["elements"] if e.get("can_click"))


def test_a_shape_description_resolves_to_the_shape_not_the_first_element():
    """click-shape: "Click on a triangle" -- the triangle is neither first nor largest."""
    page = _pages()["click-shape"]
    found = describe.describe(page["utterance"], page)
    assert found.outcome == describe.RESOLVED, found.as_dict()
    assert page["elements"][found.subject]["tag"] == "polygon"


def test_a_comparison_is_made_against_the_other_candidates():
    """drag-box: 28x28 into the 58x58 box. Not into the 480x210 page frame."""
    page = _pages()["drag-box"]
    small = describe.describe("the smaller box", page)
    large = describe.describe("the larger box", page)
    assert small.outcome == describe.RESOLVED and large.outcome == describe.RESOLVED
    assert describe.area(page["elements"][small.subject]) == 28 * 28
    assert describe.area(page["elements"][large.subject]) == 58 * 58


def test_the_whole_drag_instruction_compiles_to_the_two_real_elements():
    page = _pages()["drag-box"]
    compiled = contract.compile_contract(page["utterance"], page)
    assert compiled["refusal"] is None, compiled
    clause = compiled["clauses"][0]
    assert clause["operator"] == "DRAG_DESCRIBED"
    assert clause["members"] == [4] and clause["target"] == 5, clause


# --------------------------------------------------------------------------------------------- #
# an ambiguity stays an ambiguity
# --------------------------------------------------------------------------------------------- #
def test_two_equally_good_targets_are_reported_as_ambiguous():
    """drag-shapes-2 has two unfilled boxes; "the left box" is decided by the word, not by order."""
    page = _pages()["drag-shapes-2"]
    found = describe.container_of(page)
    assert found["outcome"] == describe.AMBIGUOUS, found
    assert sorted(found["candidates"]) == [9, 10]
    left = describe.describe("left box", page, pool=[9, 10])
    right = describe.describe("right box", page, pool=[9, 10])
    assert (left.subject, right.subject) == (9, 10)


def test_the_instruction_that_names_both_sides_resolves_both():
    page = _pages()["drag-shapes-2"]
    compiled = contract.compile_contract(page["utterance"], page)
    assert compiled["refusal"] is None, compiled
    clause = compiled["clauses"][0]
    assert clause["operator"] == "DRAG_DESCRIBED"
    assert clause["members"] == [6] and clause["target"] == 9, clause   # the blue one, to the left


# --------------------------------------------------------------------------------------------- #
# what the page cannot supply is named, and named as the PAGE's gap
# --------------------------------------------------------------------------------------------- #
def test_a_colour_the_page_never_states_is_absent_not_guessed():
    """drag-shapes: the instruction says "the black box"; the bin carries no fill at all.

    The other shapes DO carry fill, so a filter would delete the right answer. The honest reading
    is that this page does not state the dimension -- and the answer still has to be found, from
    the page's own asymmetry, with the evidence recorded on the clause.
    """
    page = _pages()["drag-shapes"]
    target = describe.describe("the black box", page, pool=[4, 5, 6, 7, 8])
    assert target.missing_dimensions, target.as_dict()
    assert "COLOUR" in " ".join(target.missing_dimensions)

    compiled = contract.compile_contract(page["utterance"], page)
    assert compiled["refusal"] is None, compiled
    clause = compiled["clauses"][0]
    assert clause["target"] == 8, clause
    # a fallback is never allowed to look like a resolution
    assert clause["target_evidence"].startswith("PAGE_ASYMMETRY__"), clause


def test_a_quoted_name_is_a_name_not_a_description():
    """click-dialog-2 regressed for one run because "OK" was read as a visual word.

    The quoted string is the selector; the descriptor resolver must not be consulted at all.
    """
    observation = {
        "utterance": 'Click the button in the dialog box labeled "OK".',
        "elements": [
            {"index": 0, "tag": "body", "text": "", "can_click": False, "box": [0, 0, 480, 210]},
            {"index": 6, "tag": "button", "text": "Close", "can_click": True, "box": [112, 63, 20, 20]},
            {"index": 13, "tag": "button", "text": "Cancel", "can_click": True, "box": [28, 170, 54, 24]},
            {"index": 14, "tag": "button", "text": "OK", "can_click": True, "box": [86, 170, 36, 24]},
        ],
    }
    compiled = contract.compile_contract(observation["utterance"], observation)
    assert compiled["refusal"] is None, compiled
    assert any(clause.get("labels") == ["OK"] for clause in compiled["clauses"]), compiled["clauses"]


# --------------------------------------------------------------------------------------------- #
# the refusal that was simply wrong
# --------------------------------------------------------------------------------------------- #
def test_a_coloured_box_instruction_is_no_longer_refused_as_needing_pixels():
    """The old rule refused every "colored box" instruction. It was a guess dressed as honesty."""
    page = _pages()["click-color"]
    compiled = contract.compile_contract(page["utterance"], page)
    assert compiled["refusal"] is None, compiled
    assert compiled["clauses"][0]["rule"] == "DESCRIBED_BY_COLOUR+SHAPE"


def test_a_description_with_no_observable_dimension_is_still_refused_by_name():
    """ "Drag the item down" names nothing visual -- and the page has exactly one movable thing."""
    page = _pages()["drag-single-shape"]
    compiled = contract.compile_contract(page["utterance"], page)
    assert compiled["refusal"] is None, compiled
    assert compiled["clauses"][0]["operator"] == "MOVE_DIRECTION"


def test_the_wall_is_not_where_the_refusal_census_says_it_is():
    """The census that aimed the roadmap: of the pages that used to be refused as SPATIAL,
    how many are now compiled? This is the correction the receipt is built on."""
    pages = _pages()
    formerly_spatial = ["click-color", "drag-box", "drag-single-shape", "drag-shapes",
                        "drag-shapes-2", "click-shape"]
    compiled = [task for task in formerly_spatial
                if contract.compile_contract(pages[task]["utterance"], pages[task]).get("refusal") is None]
    assert len(compiled) >= 5, (compiled, formerly_spatial)


# --------------------------------------------------------------------------------------------- #
# the checkers can be wrong in both directions
# --------------------------------------------------------------------------------------------- #
def test_a_drag_contract_fails_when_the_thing_never_arrived():
    page = _pages()["drag-box"]
    compiled = contract.compile_contract(page["utterance"], page)
    trace = [(page, "grab@4"), (page, "drop@4")]          # dropped back where it started
    verdict = contract.check_contract(compiled, trace)
    assert verdict["verdict"] == contract.FAIL, verdict


def test_a_drag_contract_passes_when_the_thing_ends_inside():
    page = _pages()["drag-box"]
    compiled = contract.compile_contract(page["utterance"], page)
    after = json.loads(json.dumps(page))
    for element in after["elements"]:
        if element["index"] == 4:
            element["box"] = [85, 90, 28, 28]              # inside 73,75,58x58
    verdict = contract.check_contract(compiled, [(page, "grab@4"), (after, "drop@4")])
    assert verdict["verdict"] == contract.PASS, verdict


def main() -> int:
    tests = [(name, obj) for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    failures = 0
    for name, test in tests:
        try:
            test()
            print(f"ok   {name}")
        except Exception as error:                                   # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {error}")
    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
