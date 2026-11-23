"""The owner's sentence, made checkable: scan the environment, say what I know and what I don't.

    "All the agent should do is scan everything in the environment and then retrieve from his memory
     what he knows and what he doesn't know. What he doesn't know, he should get it instantly."

Before this module that sentence had two half-answers that nothing connected and that disagreed:

  * `capability_type_surface_v1.unknowns()` -- slots with no derivable TYPE. Its only caller in the tree
    was a test asserting `{}`.
  * `reachability_v2` -- slots that could not be FILLED from real values here.

Measured: they disagree on 4 rows. `git.repository.operate.v1` is reported by the surface with five
untyped slots and by the census as also needing `repo_root` and `limit`; `repo_root` is typed `PATH_DIR`,
so it is not "unknown" -- it is simply unfilled. A reader of `unknowns()` alone concludes the machine knows
more than it does. Two implementations of one question drift; this suite pins the composed answer.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import capability_type_surface_v1 as surface  # noqa: E402
from canonical.runtime import known_and_unknown_v1 as kn  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def report() -> dict:
    return kn.known_and_unknown()


def test_every_claiming_capability_gets_exactly_one_state(report: dict) -> None:
    """A capability with two answers has none. A capability with zero has disappeared."""
    assert report["claims"] == sum(report["counts"].values())
    assert report["claims"] >= 140, report["claims"]
    for cid, row in report["rows"].items():
        assert row["state"] in {"DO", "SELF_ATTESTING", "REFUSES", "TYPED_OUT", "UNTYPED",
                                "UNDECLARED", "UNREACHABLE"}, (cid, row["state"])


def test_running_and_refusing_are_different_knowledge(report: dict) -> None:
    """`DO` means it produced something readable. `REFUSES` means the code answered and declined.

    Collapsing them would make a capability that rejects every input look as useful as one that works --
    which is the "a gate that rejects everything passes every failure test" lesson, one layer up.
    """
    do = {cid for cid, row in report["rows"].items() if row["state"] == "DO"}
    refuses = {cid for cid, row in report["rows"].items() if row["state"] == "REFUSES"}
    assert do and refuses
    assert not (do & refuses)
    for cid in do:
        assert report["rows"][cid]["evidence"]


def test_a_self_attesting_row_is_never_counted_as_knowledge(report: dict) -> None:
    """19 rows take no input and report `verified: true` from the registry's own vocabulary.

    They are reachable, so they are not UNREACHABLE; they are not informative, so they are not DO. A state
    of their own is the only honest place for them.
    """
    self_attesting = {cid for cid, row in report["rows"].items() if row["state"] == "SELF_ATTESTING"}
    assert len(self_attesting) >= 10, sorted(self_attesting)
    for cid in self_attesting:
        assert "no input" in report["rows"][cid]["evidence"]


def test_unfilled_and_untyped_are_separately_named(report: dict) -> None:
    """THE DISAGREEMENT THIS MODULE EXISTS TO END.

    `TYPED_OUT` needs a value from somewhere. `UNTYPED` needs a value AND a way to recognise a correct one.
    Only the second requires learning what the slot means, and only the second is invisible to
    `unknowns()`.
    """
    typed_out = {cid for cid, row in report["rows"].items() if row["state"] == "TYPED_OUT"}
    untyped = {cid for cid, row in report["rows"].items() if row["state"] == "UNTYPED"}
    assert typed_out, "an audit of this machine must find slots it cannot fill"
    assert untyped, "and slots whose type it cannot derive"
    for cid in typed_out:
        row = report["rows"][cid]
        assert row["missing"], cid
        assert not row.get("untyped_slots"), "%s is untyped and must not be filed as TYPED_OUT" % cid
    for cid in untyped:
        assert report["rows"][cid]["untyped_slots"], cid


def test_the_state_agrees_with_the_surface_it_composes(report: dict) -> None:
    """If the surface says a slot has no type, the composed answer may not call that row merely unfilled."""
    untyped_slots = surface.unknowns()
    for cid, slots in untyped_slots.items():
        row = report["rows"].get(cid)
        if row is None:
            continue
        if row["state"] in {"TYPED_OUT", "TYPED_OUT"}:
            pytest.fail("%s has untyped slots %s but is filed as %s" % (cid, slots, row["state"]))


def test_the_surface_alone_understates_the_gap() -> None:
    """The measurement that motivated the module: `unknowns()` reports fewer missing slots than the census.

    This is not a bug in either module. It is why neither may be read alone, and the test exists so the
    claim cannot rot if somebody quietly "fixes" one of them.
    """
    from canonical.runtime import live_integrated_brain_v1 as brain
    from canonical.runtime import reachability_v2 as reach
    untyped = surface.unknowns()
    plan, blocked = reach.plan_for(brain.load_verified_registry(), ROOT)
    needs = {cid: set(v.split(":", 1)[1].split(",")) for cid, v in blocked.items()
             if v.startswith("NEEDS_INPUT:")}
    smaller = [cid for cid in needs if cid in untyped and set(untyped[cid]) < needs[cid]]
    assert smaller, ("the two sources now agree exactly, which would mean one of them was changed; "
                     "re-measure before deleting this test")


def test_the_answer_says_it_was_measured_in_a_disposable_world(report: dict) -> None:
    """The scan runs real capabilities, so the proof that it did not touch this tree is part of the answer."""
    assert report["world"]["host_untouched"] is True
    assert report["world"]["verified"] is True
    assert report["interpreter"]


def test_a_missing_value_is_a_work_item_not_a_verdict(report: dict) -> None:
    """`TYPED_OUT` names the slots. A named gap can be closed by looking; a category cannot."""
    for cid, row in report["rows"].items():
        if row["state"] == "TYPED_OUT":
            for slot in row["missing"]:
                assert slot and slot != "unknown", (cid, slot)
                assert " " not in slot, (cid, slot)
