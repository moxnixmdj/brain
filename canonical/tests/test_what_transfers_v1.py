"""Pins `what_transfers_v1.py` and the organ resolution, so neither can quietly revert.

The claims in `WHAT_IS_REAL_AND_WHAT_IS_NOT_20261113_V1.md` are only worth what their weakest
measurement is worth. Each test here pins one of those measurements, including the ones that say the
news is bad -- a test that only pins good news is a rubber stamp.

Run: python3 -m pytest canonical/tests/test_what_transfers_v1.py -q
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ORGAN = ROOT / "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"
record_path = ROOT / "canonical/verification/WHAT_TRANSFERS_20261113_V1.json"

sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------- 0. the organ is not broken


def test_the_organ_that_every_generalisation_claim_rests_on_can_be_parsed():
    """On 2026-11-13 this file was a SyntaxError at line 1598 and 10 test files could not start."""
    source = ORGAN.read_text(encoding="utf-8")
    ast.parse(source)  # raises SyntaxError, which is the point


def test_no_merge_conflict_markers_are_left_in_the_organ():
    source = ORGAN.read_text(encoding="utf-8")
    for marker in ("<<<<<<<", ">>>>>>>"):
        assert marker not in source, marker


def test_the_resolution_kept_both_sides_of_each_union():
    """Neither region was an either/or: taking one side deletes working code."""
    source = ORGAN.read_text(encoding="utf-8")
    assert "aliases_to_add(text" in source, "main's side of the union was dropped"
    assert "swaps_to_make(text, example" in source, "the branch's side of the union was dropped"


def test_the_organ_still_refuses_a_use_the_example_never_showed():
    """The refusal IS the feature. If this ever returns an edit, a guard has been removed."""
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ

    before = "def f(handle):\n    return yaml.load(handle)  # ours\n"
    after = "def f(handle):\n    return yaml.safe_load(handle)  # ours\n"
    shown = "import yaml\n\n\ndef go(handle):\n    return yaml.load(handle)  # ours\n"
    unseen = "import yaml\n\n\ndef go(handle):\n    return yaml.load(handle, Loader=yaml.FullLoader)  # ours\n"

    assert "yaml.safe_load" in organ.edit_by_example(shown, before, after)
    with pytest.raises(organ.Refused) as refused:
        organ.edit_by_example(unseen, before, after)
    assert "the keyword Loader" in str(refused.value)


# ---------------------------------------------------------------- 1. one showing does not transfer


def one_showing_refuses(target: str) -> bool:
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ

    before = "def at_limit(n):\n    if n <= MAX:\n        return True\n    return False\n"
    after = "def at_limit(n):\n    if n < MAX:\n        return True\n    return False\n"
    try:
        organ.edit_by_example(target, before, after)
        return False
    except organ.Refused:
        return True


@pytest.mark.parametrize("target,what", [
    ("def is_small(size, cap):\n    if size <= cap:\n        return True\n    return False\n",
     "same defect, different names"),
    ("def keep(values, hi):\n    return [v for v in values if v <= hi]\n", "another shape"),
    ("class Window:\n    def admits(self, x):\n        return x <= self.hi\n", "another operator form"),
])
def test_one_showing_is_refused_on_every_new_shape(target, what):
    """The owner's claim is 'the action happens once and it is learned everywhere'. It is not."""
    assert one_showing_refuses(target) is True, what


# ---------------------------------------------------------------- 2. two showings do transfer


def test_two_showings_from_two_places_reach_a_name_never_shown():
    """The real, shipped capability, and the reason 'revolutionary' is not empty."""
    import canonical.runtime.edit_kind_learning_v1 as ladder

    lessons = ladder.Lessons()
    lessons.learn("e0",
                  "def at_limit(n):\n    if n <= MAX:\n        return True\n    return False\n",
                  "def at_limit(n):\n    if n < MAX:\n        return True\n    return False\n")
    lessons.learn("e1",
                  "def is_small(size, cap):\n    if size <= cap:\n        return True\n    return False\n",
                  "def is_small(size, cap):\n    if size < cap:\n        return True\n    return False\n")
    proposals = lessons.proposals(
        "def admits(x, hi):\n    if x <= hi:\n        return True\n    return False\n", limit=12)
    assert proposals, "two showings produced no proposal at all"
    assert "if x < hi" in proposals[0]["source"], proposals[0]["source"]


def test_two_showings_still_offer_to_change_a_boundary_that_is_required():
    """THE LIMIT, pinned on purpose: the second showing widens the rule, it does not make it right.

    Only a check on the target file can refuse this. If this test ever fails, something started
    reading the target's tests, and that is a different mechanism worth naming in the doc.
    """
    import canonical.runtime.edit_kind_learning_v1 as ladder

    lessons = ladder.Lessons()
    for index, (before, after) in enumerate([
        ("def at_limit(n):\n    if n <= MAX:\n        return True\n    return False\n",
         "def at_limit(n):\n    if n < MAX:\n        return True\n    return False\n"),
        ("def is_small(size, cap):\n    if size <= cap:\n        return True\n    return False\n",
         "def is_small(size, cap):\n    if size < cap:\n        return True\n    return False\n"),
    ]):
        lessons.learn(f"e{index}", before, after)
    required = "def in_closed(x, hi):\n    if x <= hi:\n        return True\n    return False\n"
    assert lessons.proposals(required, limit=12), "if this is empty, a guard moved into the learner"


# ---------------------------------------------------------------- 3. the solved-claim, measured


def test_the_retrieval_store_cannot_hold_a_failure():
    """A store of successes cannot learn where a lesson stops applying."""
    data = json.loads((ROOT / "canonical/astra_runtime/generalization/"
                       "GENERALIZATION_EXPERIENCES_V1.json").read_text(encoding="utf-8"))
    assert {row["outcome"] for row in data["experiences"]} == {"success"}


def test_the_retrieval_store_is_far_smaller_than_its_record_count():
    data = json.loads((ROOT / "canonical/astra_runtime/generalization/"
                       "GENERALIZATION_EXPERIENCES_V1.json").read_text(encoding="utf-8"))
    rows = data["experiences"]
    unique = {row["task_description"] for row in rows}
    assert len(unique) < len(rows), "duplicates inflate the record count"


def test_the_retrieval_engine_is_not_importable_or_works():
    """It is importable and it runs; that is not the same as it generalising."""
    engine_mod = ROOT / "canonical/swe_kernel/semantic_generalization_engine_v1.py"
    ast.parse(engine_mod.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 4. the record


@pytest.fixture(scope="module")
def record():
    if not record_path.is_file():
        pytest.skip("the record is not on this branch")
    return json.loads(record_path.read_text(encoding="utf-8"))


def test_the_record_says_the_organ_is_importable(record):
    assert record["shipped_organ"]["importable"] is True


def test_the_record_admits_one_showing_refuses_all_four_shapes(record):
    shapes = record["claim_a_transfer"]["one_showing_against_four_shapes"]
    assert set(shapes.values()) == {"REFUSED"}, shapes


def test_the_record_shows_two_showings_changing_the_bound(record):
    two = record["claim_a_transfer"]["two_showings"]
    assert two["proposals"] >= 1
    assert two["first_proposal_changes_the_bound"] is True


def test_the_record_states_the_answer_does_not_come_from_the_memory(record):
    b = record["claim_b_the_retrieval_engine"]
    assert b["the_content_comes_from_the_memory"] is False
    assert b["answer_dependence_test_is_conclusive"] is False, (
        "if this becomes true the probe got stronger: re-read §2 of the doc before trusting it")


def test_the_record_carries_no_capability_and_no_spend(record):
    assert record["incremental_spend_usd"] == 0
    assert record["model_calls"] == 0
    assert record["authority"].startswith("NONE__")
