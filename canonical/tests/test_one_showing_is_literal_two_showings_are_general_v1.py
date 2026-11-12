"""What one showing buys on the coding surface: a literal rule, not a general one.

`canonical/swe_kernel/taught_actions/edit_by_example_v1.py` is the tree's demonstration-to-edit
learner. This pins the measurement that answers "show it once and it learns it":

  * one showing gives a rule about **exactly that code** — `product == None` — and it refuses the
    same defect written with another name, attribute, call or local;
  * a **second, different** showing is what turns the rule into `?1 == None`, and then all four are
    edited;
  * a use no example showed is refused by line rather than rewritten — which is the regression the
    module's own notes record on real commits (`yaml.load(stream, Loader=...)`);
  * a change that adds a statement is never learned, because the learnt space is "inside one
    expression or one simple statement".

That last line is the ceiling, and it is the same ceiling round 9 measured on the word learner:
the algebra is fixed; the examples only choose within it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from one_showing_is_literal_two_showings_are_general_probe_20261112 import (  # noqa: E402
    STRUCTURAL,
    TARGETS,
    YAML_TARGET,
    run,
)

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as learner  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def test_one_showing_is_a_rule_about_the_code_it_showed():
    assert _report()["rules"]["after_one_showing"] == ["product == None -> product is None"]


def test_two_showings_make_one_rule_with_a_blank():
    assert _report()["rules"]["after_two_showings"] == ["?1 == None -> ?1 is None"]


def test_one_showing_reaches_one_of_four_unseen_sites():
    s = _report()["summary"]
    assert s["unseen_sites"] == 4
    assert s["edited_after_one_showing"] == 1
    assert s["refused_after_one_showing"] == 3
    edited = [row["target"] for row in _report()["generalisation"] if row["edited_after_one_showing"]]
    assert edited == ["the_same_name"], "one showing must not generalise past the shape it saw"


def test_two_showings_reach_all_four():
    s = _report()["summary"]
    assert s["edited_after_two_showings"] == len(TARGETS) == 4


def test_a_use_no_example_showed_is_refused_by_line_not_rewritten():
    case = _report()["safety"]["one_showing"]
    assert case["edited"] is False
    assert "has yaml.load called with 1 argument and the keyword Loader" in case["reason"]
    assert "line" in case["reason"]


def test_saying_leave_the_rest_alone_changes_only_the_shown_use():
    case = _report()["safety"]["one_showing_leave_unshown"]
    assert case["edited"] is True
    assert "yaml.safe_load(h)" in case["text"]
    assert "yaml.load(h, Loader=yaml.FullLoader)" in case["text"], (
        "the unshown call must survive untouched"
    )


def test_a_second_showing_settles_the_unshown_use_without_being_asked():
    case = _report()["safety"]["two_showings"]
    assert case["edited"] is True
    assert "yaml.safe_load(h)" in case["text"]
    assert "yaml.load(h, Loader=yaml.FullLoader)" in case["text"]
    assert YAML_TARGET.count("yaml.load(") == 2


def test_a_structural_change_is_never_learned_from_showing():
    ceiling = _report()["ceiling"]
    assert ceiling["learned"] is False
    assert "adds, removes or reshapes whole statements" in ceiling["reason"]
    try:
        learner.learn_all([STRUCTURAL])
    except learner.Refused:
        return
    raise AssertionError("a structural change was learned from a demonstration")


def test_the_probe_ran_the_shipped_learner_and_spent_nothing():
    report = _report()
    assert report["model_dependency_count"] == 0
    assert report["incremental_spend_usd"] == 0
    assert report["learner"].endswith("edit_by_example_v1.py")
