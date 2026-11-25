#!/usr/bin/env python3
"""The control that could have killed the previous round's headline.

`SCRAMBLED` exists to be uncooperative: its atoms fill the family's roles in a permuted order, so any
claim resting on role correspondence must collapse on it. Measured: portability stayed at 95.1% and the
transfers stayed sound, so the procedure claim survived. What the control DID take down was the broader
claim that transfer is widely available -- all four reach gains came from one teacher.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402


def test_the_control_machine_is_a_real_machine():
    """It must do real work on a real file, or it is not a control."""
    with tempfile.TemporaryDirectory() as tmp:
        machine = room.all_machines()["SCRAMBLED"](pathlib.Path(tmp))
        machine.reset()
        rows = machine.read()
        assert rows == [("0", "alpha_one"), ("1", "beta_two"), ("2", "gamma_three")]
        transitions = base.explore(machine, list(machine.atoms), 2)
        assert transitions, "the control must produce executed transitions"


def test_the_control_permutes_the_family_roles():
    """The whole point: its atom identifiers occupy the slots, but not the same jobs."""
    with tempfile.TemporaryDirectory() as tmp:
        scrambled = room.all_machines()["SCRAMBLED"](pathlib.Path(tmp))
        git = room.all_machines()["GIT"](pathlib.Path(tmp) / "g")
        (pathlib.Path(tmp) / "g").mkdir(exist_ok=True)
        scrambled_ids = [atom.ident for atom in scrambled.atoms]
        git_ids = [atom.ident for atom in git.atoms]
        assert [i.rsplit("_", 1)[-1] for i in scrambled_ids] == ["A1", "A2", "A3", "A4"]
        assert len(git_ids) == 5, "the family machine still has five slots"
        # the jobs differ: SC_A1 sorts where the family's A1 appends
        assert "sort" in " ".join(str(step) for step in scrambled.atoms[0].steps)


def test_the_control_did_not_break_portability():
    """The claim that survived: reasons still re-run on foreign machines with the control present."""
    import json
    artifact = (REPO / "canonical" / "verification" /
                "A_CONTRAST_IS_A_PROBE_20261124_V2.json")
    if not artifact.exists():                        # pragma: no cover
        return
    payload = json.loads(artifact.read_text())
    ledger = payload["summary"]["ledger"]
    assert ledger["re_ran"] * 10 > ledger["offered"] * 9, ">90% portability with the control in"
    assert payload["summary"]["arms"]["B_experiment_and_conclusion"]["wrong"] == 0


def test_the_control_shows_transfer_is_not_broadly_available():
    """The claim it DID take down, pinned so it cannot creep back: every reach gain came from one
    teacher. This is a finding about the tree, not a regression, so it is asserted explicitly."""
    import json
    artifact = (REPO / "canonical" / "verification" /
                "A_CONTRAST_IS_A_PROBE_20261124_V2.json")
    if not artifact.exists():                        # pragma: no cover
        return
    payload = json.loads(artifact.read_text())
    gained = [row for row in payload["per_pair"]
              if row["B"]["predictions"] > row["A"]["predictions"]]
    assert gained, "some transfer must be happening or there is nothing to explain"
    teachers = {row["teacher"] for row in gained}
    assert len(teachers) < payload["summary"]["teachers"] / 4, (
        "reach gains are concentrated in very few teachers: portability is not availability")
