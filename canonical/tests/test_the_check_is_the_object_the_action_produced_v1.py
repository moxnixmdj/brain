"""The witness is credited only for the bytes the action changed.

These tests are the measured failures of the previous round plus the three mistakes this
round made while wiring the witness into the shipped loop. Each one is a real regression:

  1. the eight which-object probes still accept a decoy, but the witness must never credit it;
  2. a check that holds BEFORE the action ran is a false done, not a success;
  3. an all-reject verifier is its own defect, not a false done (VerifierBench);
  4. a valid alternative producer and a different output name must still witness (no over-reject);
  5. an action that changes two same-kind objects is ambiguous; a stored binding that names the
     untouched decoy is refused; state drift is refused;
  6. destroyed bytes are ACCEPTED_CHANGED, never ACCEPTED_INERT;
  7. producers chosen after the rule was frozen still bind (thin machine);
  8. a REMOVED object is a legitimate witness. The first wiring reported STATE_DRIFT for both
     removal needs (N10, N11) because absence was compared to a digest. This test is why that
     bug cannot come back;
  9. `execute_path` refuses a goal that was already true before the action, so the shipped loop
     cannot claim a false done any more.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import room_witness_v1 as rw  # noqa: E402
from canonical.tools import (  # noqa: E402
    the_check_is_the_object_the_action_produced_v1 as subject,
    the_guide_is_an_action_grammar_v1 as guide,
)


def _room() -> tuple[pathlib.Path, object]:
    tmp = tempfile.TemporaryDirectory(prefix="witness-test-")
    root = pathlib.Path(tmp.name) / "room"
    subject._base_room(root)
    return root, tmp


def _replay(root: pathlib.Path):
    def read(rel: str) -> str:
        return hashlib.sha256((root / rel).read_bytes()).hexdigest()
    return read


# 1 --------------------------------------------------------------------------- #

def test_the_eight_blind_probes_are_bound_to_the_action_not_the_decoy():
    got = subject.which_object_round()
    assert got["probes"] == 8
    assert got["checks_still_blind"] == 8, "this round does not repair the check"
    assert got["witnessed"] == 8
    assert got["bound_to_right"] == 8
    assert got["decoy_credited"] == 0
    assert all(row["invariants"] == 1 for row in got["rows"])


def test_every_declared_gate_is_met():
    verdict = subject.judged(subject.measure())
    assert all(row["MET"] for row in verdict.values()), {
        k: v for k, v in verdict.items() if not v["MET"]}


# 2, 3, 4, 5 ------------------------------------------------------------------ #

def test_controls_refuse_both_error_directions_and_never_over_reject():
    got = subject.controls()
    assert got["false_done_cases"] == 4 and got["false_done_refused"] == 4
    assert got["all_reject_named"] == 1
    assert got["alternatives"] == 2 and got["alternatives_witnessed"] == 2
    assert got["ambiguous_refused"] == 1
    assert got["wrong_memory_refused"] == 1
    assert got["drift_refused"] == 1


def test_a_held_check_on_an_untouched_object_is_an_invariant_not_a_witness():
    got = rw.witness({"a": "1"}, {"a": "1", "b": "2"},
                     [{"check": "any", "held": True, "path": "a"}])
    assert got["status"] == "REFUSED__GOAL_HELD_BEFORE_THE_ACTION"
    assert got["invariants"] == 1 and got["bound"] == []


def test_all_reject_is_named_separately_from_false_done():
    got = rw.witness({"a": "1"}, {"a": "1", "b": "2"},
                     [{"check": "any", "held": False, "path": "b"}])
    assert got["status"] == "REFUSED__NO_HELD_CHECK"
    assert "all-reject" in got["reason"]


def test_targets_of_separates_the_object_asserted_from_the_source_read():
    rows = rw.targets_of([
        {"check": "bytes_equal", "held": True, "left": "notes/a.txt", "right": "a.out"},
        {"check": "archive_contains", "held": True,
         "tried": [{"archive": "src.tar", "held": True}]},
    ])
    assert rows[0] == {"check": "bytes_equal", "held": True, "targets": ["a.out"],
                       "sources": ["notes/a.txt"]}
    assert rows[1]["targets"] == ["src.tar"]


# 6 --------------------------------------------------------------------------- #

def test_an_overwrite_is_seen_by_bytes_not_by_a_kind_map():
    delta = rw.delta_of({"payload.txt": "aaa"}, {"payload.txt": "bbb"})
    assert delta["overwritten"] == ["payload.txt"]
    assert delta["produced"] == ["payload.txt"] == delta["consumed"]


def test_destroyed_bytes_are_never_reported_inert():
    got = subject.destroyer_status_round()
    assert got["writers_found"] > 0
    assert got["accepted_destroyers"] > 0
    assert got["bytes_destroyed_reported_inert"] == 0
    assert rw.status_of({"a": "1"}, {"a": "2"}, True)["status"] == "ACCEPTED_CHANGED"
    assert rw.status_of({"a": "1"}, {"a": "1"}, True)["status"] == "ACCEPTED_INERT"


# 7 --------------------------------------------------------------------------- #

def test_transfer_to_producers_chosen_after_the_rule_was_frozen():
    got = subject.transfer_round()
    assert got["producers_available"] >= 2
    assert got["witnessed"] == got["producers_available"]
    assert got["bound_to_right"] == got["producers_available"]


# 8 --------------------------------------------------------------------------- #

def test_a_removed_object_is_a_witness_and_absence_is_not_state_drift():
    """N10/N11 regressed on the first wiring: `absent` bound to a removed path was read back
    and reported as drift. Absence is the expected state of a removal."""
    root, tmp = _room()
    try:
        before = rw.digest(root)
        (root / "payload.txt").unlink()
        after = rw.digest(root)
        verdict = rw.witness(before, after,
                             [{"check": "absent", "held": True, "path": "payload.txt"}],
                             argv=["rm", "payload.txt"], reread=_replay(root))
        assert verdict["status"] == "WITNESSED", verdict
        assert verdict["bound"] == ["payload.txt"]
        assert verdict["drift"] == []
        # The object coming back really is drift.
        (root / "payload.txt").write_text("back\n", encoding="utf-8")
        back = rw.witness(before, after,
                          [{"check": "absent", "held": True, "path": "payload.txt"}],
                          argv=["rm", "payload.txt"], reread=_replay(root))
        assert back["status"] == "REFUSED__STATE_DRIFT"
    finally:
        tmp.cleanup()


# 9 --------------------------------------------------------------------------- #

def test_the_shipped_loop_cannot_claim_a_goal_that_was_already_true():
    """An action that changed nothing must not be credited with a pre-existing goal.

    The need asks for a file to be absent and the file never existed. Without the witness
    `execute_path` returns PASS__GOAL_HELD immediately; with it, the goal is an invariant.
    """
    page = guide.page_of("true")
    edge = {"page": page, "verb": "remove", "in_kind": "plain", "out_kind": "plain",
            "source": "description", "program": "true", "flag": None}
    need = {"need": "remove the ghost file",
            "requires": [{"check": "absent", "path": "ghost.txt"}], "target": "absent"}
    with tempfile.TemporaryDirectory(prefix="witness-loop-") as where:
        root = pathlib.Path(where) / "room"
        guide.make_room(root)
        result = guide.execute_path([edge], need, root)
    assert result["status"] != "PASS__GOAL_HELD"
    witness = (result["steps"] or [{}])[-1].get("witness") or {}
    assert witness.get("status") == "REFUSED__GOAL_HELD_BEFORE_THE_ACTION"


def test_the_wiring_did_not_change_the_eleven_shipped_need_verdicts():
    """G1..G8 of the 446-page instrument, re-measured on both sides of the wiring."""
    baseline = REPO / "canonical/verification/ROOM_WITNESS_GRAMMAR_REGRESSION_20261124_V1.json"
    if not baseline.exists():
        pytest.skip("regression receipt not present in this checkout")
    import json
    data = json.loads(baseline.read_text(encoding="utf-8"))
    assert data["baseline"]["summary"]["goals_held"] == data["wired"]["summary"]["goals_held"]
    assert data["wired"]["summary"]["witnessed_goals"] == \
        data["wired"]["summary"]["goals_held"]
    assert data["same_per_need_verdicts"]
    assert data["g1_to_g7_unchanged"]
    assert data["wired"]["verdict"]["G8_the_goal_is_witnessed_by_the_action"]["MET"]
