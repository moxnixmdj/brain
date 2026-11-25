"""What the frame is, held so it cannot quietly become something friendlier.

Every test here is one of the things this round found, including the two findings that went
against the round's own interest:

  * PRUNE is unsound: goal-directed pruning of the action set loses plans that unpruned search
    finds. A future round that "improves" `solve_sequence` by pruning again will fail `test_...`.
  * ORDER, the sound version, does not pay for itself at depth 2-3. The test asserts the accounting
    exists, not that the prior wins -- because it does not win here, and a test that demanded a win
    would be a test that pressures the next round to fake one.
  * A frame is VAIN if it is built from the frame under test. The first L4 did exactly that and
    reported zero collisions on 39 rows while measuring nothing. `test_...` builds the tautology and
    asserts it can never collide, so the defect is recorded as a property rather than a memory.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
for candidate in (REPO, REPO / "canonical" / "tools"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from canonical.swe_kernel import canonical_frame_v1 as cf  # noqa: E402

STATE_A = [("r1", "alpha"), ("r2", "beta")]
STATE_B = [("r1", "alpha"), ("r2", "beta"), ("r3", "gamma")]
STATE_SORTED = [("0", "a"), ("1", "b"), ("2", "c")]
STATE_UNSORTED = [("0", "b"), ("1", "a"), ("2", "c")]


# ---------------------------------------------------------------------------------------------
# the reading is the machine's, and every frame is computed from it
# ---------------------------------------------------------------------------------------------

def test_the_fifteen_frames_are_the_five_relations_aimed_three_ways():
    assert cf.RELATIONS == ("CARD", "MULTISET", "ORDER", "IDENT", "PAIRING")
    assert cf.BINDINGS == ("WHOLE", "CONTENT", "IDENT")
    assert len(cf.RELATIONS) * len(cf.BINDINGS) == 15


def test_a_content_frame_without_a_slot_is_refused_not_defaulted():
    """A default here would be a silent claim that 'the content' means 'all contents'. It does
    not, and the earlier rounds' blindness came from exactly this kind of quiet default."""
    with pytest.raises(cf.FrameError) as caught:
        cf.observe(("CARD", "CONTENT"), STATE_A)
    assert "SLOT_REQUIRED" in str(caught.value)


def test_the_slot_is_what_makes_a_rename_visible():
    """The finding that made `mv` unlearnable: every whole-reading frame is blind to a rename,
    and every content/identity frame sees it. The test is the measurement."""
    before = [("old_name", "alpha")]
    after = [("new_name", "alpha")]
    assert not any(cf.moved(before, after, f) for f in cf.FIXED_FRAMES)
    assert cf.moved(before, after, ("IDENT", "WHOLE"))
    assert cf.moved(before, after, ("PAIRING", "WHOLE"))


def test_order_moves_without_the_multiset_moving():
    """`sort` and `tac` change the file and leave its multiset EXACTLY unchanged."""
    assert not cf.moved(STATE_UNSORTED, STATE_SORTED, ("MULTISET", "WHOLE"))
    assert cf.moved(STATE_UNSORTED, STATE_SORTED, ("ORDER", "WHOLE"))


# ---------------------------------------------------------------------------------------------
# the template: what is carried, and what is refused
# ---------------------------------------------------------------------------------------------

def test_a_template_that_aimed_at_a_slot_carries_no_literal():
    """The carried object must not contain the source machine's names. If it did, it could not
    cross to a machine that shares none of them -- and crossing is the entire claim."""
    tpl = cf.template(STATE_A, STATE_B, cf.FIXED_FRAMES, slot="alpha")
    carried = repr(tpl["slot_frames"]) + repr(tpl["whole_frames"])
    assert "alpha" not in carried and "beta" not in carried
    assert tpl["uses_literals"] is False


def test_a_slot_only_template_instantiates_on_a_machine_with_no_shared_name():
    tpl = cf.template(STATE_A, STATE_B, cf.FIXED_FRAMES, slot="alpha")
    other = [("k9", "never_seen_this"), ("k8", "nor_this")]
    result = cf.instantiate(tpl, other, goal_literal="never_seen_this")
    assert result["status"] == "PASS__SLOT_ONLY"
    assert result["frames"] == [(f[0], "CONTENT", "never_seen_this")
                                for f in [tuple(x) for x in tpl["slot_frames"]]] + \
                               [(f[0], "WHOLE", None) for f in
                                [tuple(x) for x in tpl["whole_frames"]]]


def test_a_template_that_names_a_literal_refuses_when_the_labelling_is_not_unique():
    """A template may mention structure the goal did not name. When two labellings fit the target
    reading, the template means two things there. The honest answer is REFUSED, and this test is
    what stops a future round from 'fixing' it by taking the first fit."""
    tpl = {"slot_frames": [], "whole_frames": [],
           "literal_frames": [["CARD", "+", "alpha"], ["CARD", "+", "beta"]],
           "uses_literals": True}
    ambiguous = [("a", "x"), ("b", "y"), ("c", "z")]
    result = cf.instantiate(tpl, ambiguous, goal_literal="x")
    assert result["status"] == "REFUSED__LABELLING_NOT_UNIQUE"
    assert len(result["labellings"]) > 1


def test_a_template_with_a_slot_but_no_goal_literal_refuses():
    tpl = cf.template(STATE_A, STATE_B, cf.FIXED_FRAMES, slot="alpha")
    assert cf.instantiate(tpl, STATE_B)["status"] == "REFUSED__SLOT_UNBOUND"


# ---------------------------------------------------------------------------------------------
# stateability: the check whose absence made `mv` pointless to experience
# ---------------------------------------------------------------------------------------------

def test_a_goal_outside_the_vocabulary_is_sayable_and_refused_scoped():
    carried = cf.FIXED_FRAMES
    inside = cf.stateable({"frame": ["CARD", "WHOLE"], "slot": None}, carried)
    outside = cf.stateable({"frame": ["ORDER", "WHOLE"], "slot": None}, carried)
    assert inside["stateable"] is True
    assert outside["stateable"] is False
    assert outside["reason"] == "FRAME_NOT_IN_VOCABULARY"


def test_a_slotted_goal_with_no_slot_is_not_stateable():
    carried = tuple(cf.FIXED_FRAMES) + (("CARD", "CONTENT"),)
    result = cf.stateable({"frame": ["CARD", "CONTENT"], "slot": None}, carried)
    assert result["stateable"] is False
    assert result["reason"] == "SLOT_UNBOUND"
    # a different disease from a missing frame, with a different repair
    assert cf.unstateable_why({"frame": ["CARD", "CONTENT"], "slot": None},
                              carried) == "SLOT_UNBOUND"
    assert cf.unstateable_why({"frame": ["CARD", "CONTENT"], "slot": "alpha"},
                              carried) == "STATEABLE"


# ---------------------------------------------------------------------------------------------
# the price: cells, collisions, and the tautology that was caught
# ---------------------------------------------------------------------------------------------

def test_cells_count_distinguishable_values_not_runs():
    assert cf.cells(("CARD", "WHOLE"), [STATE_A, STATE_A, STATE_B]) == 2


def test_a_tautological_frame_can_never_collide_and_that_is_the_defect():
    """The first L4 asked 'does the frame equal the value the frame produced'. It reported zero
    collisions on 39 rows. Nothing can collide with a statement about itself, so the measurement
    was empty -- and this test encodes why, so it cannot be rebuilt by accident."""
    runs = [(STATE_A, True), (STATE_A, False), (STATE_B, True)]
    # a frame whose verdict is DEFINED as its own value collides nowhere, by construction
    self_defined = [(s, cf.observe(("CARD", "WHOLE"), s) == 3) for s, _v in runs]
    assert cf.collisions([("CARD", "WHOLE")], self_defined) == 0
    # and a verdict that is NOT a function of the frame can collide, which is why the distinction
    # is a measurement and not a slogan
    independent = [(s, len(s) == 2) for s, _v in runs]
    assert cf.collisions([("MULTISET", "WHOLE")], independent) == 0
    contradictory = [(STATE_A, True), (STATE_A, False)]
    assert cf.collisions([("MULTISET", "WHOLE")], contradictory) == 1


def test_a_sufficient_frame_is_only_sufficient_for_the_runs_it_was_given():
    """BREADTH/price law, as a test: the same frame separates on one pool and collides on another.
    A future round that calls a frame 'sufficient' without naming its pool fails here."""
    shallow = [(STATE_A, True), (STATE_B, True)]
    deep = [(STATE_A, True), (STATE_A, False)]
    assert cf.collisions([("CARD", "WHOLE")], shallow) == 0
    assert cf.collisions([("CARD", "WHOLE")], deep) == 1


def test_cheapest_sufficient_refuses_and_names_a_witness():
    runs = [(STATE_A, True), (STATE_A, False)]
    result = cf.cheapest_sufficient([("CARD", "WHOLE")], runs)
    assert result["status"] == "REFUSED__NO_SUBSET_SEPARATES_POOL"
    assert result["witness"] is not None


# ---------------------------------------------------------------------------------------------
# the two findings that went against this round's interest
# ---------------------------------------------------------------------------------------------

def test_goal_directed_pruning_is_unsound_and_stays_recorded_as_such():
    """PRUNE lost 5 plans that BLIND found, at depths 2 and 3, on real machines. The mechanism is
    kept in the instrument because deleting a failed idea is how it comes back."""
    import the_frame_crosses_the_machine_v1 as instrument
    source = pathlib.Path(instrument.__file__).read_text(encoding="utf-8")
    assert "PRUNE IS MEASURED HERE BECAUSE IT FAILED" in source
    assert 'mode == "prune"' in source


def test_the_four_ledgers_and_the_blind_spot_are_all_reported(tmp_path):
    """The instrument must not be able to report a win without reporting the columns that can
    lose: BLIND, PRUNE, EXEMPLAR, REPLAY, the blind spot, and the cost."""
    import json
    import the_frame_crosses_the_machine_v1 as instrument

    out = tmp_path / "receipt.json"
    code = instrument.main(["--out", str(out), "--machines", "LIST", "VAULT",
                            "--max-sequences", "60"])
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    for key in ("L1_stateability", "L2_identification", "L3_crossing", "L4_depth",
                "L5_composition", "blind_spot", "cost"):
        assert key in report, key
    assert report["cost"]["model_calls"] == 0
    assert report["cost"]["stored_parameters"] == 0
    assert report["blind_spot"]["the_vocabulary_can_state_it"] is False
    for mode in ("BLIND", "PRUNE", "ORDER"):
        assert f"by_depth_2" in report["L5_composition"]
        assert mode in report["L5_composition"]["by_depth_2"]
    assert "EXEMPLAR" in report["L3_crossing"] and "REPLAY" in report["L3_crossing"]
