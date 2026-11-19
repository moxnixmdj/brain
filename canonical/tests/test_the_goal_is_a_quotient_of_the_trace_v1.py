"""The hardest material this round has: real runs, a computed lattice, and the two criteria it missed.

Nothing here re-checks what earlier rounds proved. These tests run the machines, re-execute the pair of
sequences that no reading can tell apart, and pin both declared failures so that a future edit cannot
turn them green quietly.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

RECEIPT = (ROOT / "canonical" / "verification"
           / "THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.json")


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def _filesystem() -> env.Machine:
    machine = vocab.MACHINES["FILESYSTEM"](pathlib.Path(tempfile.mkdtemp(prefix="test-quotient-")))
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    return machine


def test_the_ladder_is_the_exchange_rate_and_every_rung_is_coarser_than_the_last() -> None:
    """68 -> 55 -> 19 -> 5 on FILESYSTEM is the whole claim: supplied structure buys experiences."""
    cells = _receipt()["verdict"]["F4_the_ladder_is_the_exchange_rate"]["cells_by_rung"]
    for machine, rungs in cells.items():
        values = [rungs[rung] for rung in ("raw", "fields", "literal", "derived")]
        assert values == sorted(values, reverse=True), f"{machine} is not monotone: {values}"
        assert values[0] > values[-1], f"{machine} bought nothing"
    assert cells["FILESYSTEM"]["derived"] == 5
    assert cells["TARBALL"]["derived"] == 3


def test_the_goal_chooses_the_statistic_and_each_is_blind_to_the_other() -> None:
    """On one machine, two goals need different statistics, and each has a witness against the other."""
    verdict = _receipt()["verdict"]["F2_the_quotient_is_chosen_by_the_goal"]
    assert verdict["MET"] is True
    assert verdict["portable_winner"] != verdict["pair_goal_winner"]
    assert verdict["portable_winner_on_the_pair_pool"] == [False]
    assert verdict["pair_winner_on_the_portable_pool"] == [False]
    assert verdict["portable_winner_witnesses_there"], "no witness pair: the refusal is asserted"
    assert verdict["pair_winner_witnesses_there"]


def test_the_reading_cannot_see_a_command_that_changes_nothing() -> None:
    """The certificate in one line, re-executed here: `A1,A1` and `A1,A5` read identically.

    A5 is a listing. It changes nothing, so the reading after every step is the same for both
    sequences -- and the user's judgment ("the listing ran") is opposite. No projection of the reading
    can separate them, at any rung; the executor's own call log can.
    """
    machine = _filesystem()
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    traces = {}
    for sequence in (("FS_A1", "FS_A1"), ("FS_A1", "FS_A5")):
        machine.reset()
        states = [tuple(machine.read())]
        for ident in sequence:
            atom = next(atom for atom in machine.atoms if atom.ident == ident)
            env.execute(atom, machine, args)
            states.append(tuple(machine.read()))
        traces[sequence] = tuple(states)
    assert traces[("FS_A1", "FS_A1")] == traces[("FS_A1", "FS_A5")]

    receipt = _receipt()["atom_goal"]
    assert receipt["reading_ladder"]["raw"]["sufficient"] == 0
    assert receipt["reading_ladder"]["derived"]["sufficient"] == 0
    assert receipt["repair"]["projections"] == ["atom_sequence"]
    assert receipt["repair_cells"] == receipt["sequences"]
    assert receipt["two_sequences_one_reading_opposite_judgments"]


def test_the_statistic_that_sufficed_on_shallow_runs_fails_on_deeper_ones() -> None:
    """The declared failure, kept: sufficiency is relative to the run set it was measured on.

    Chosen on one- and two-action runs, the statistic collides on three-action runs -- because deeper
    runs contain a case (add, then remove) the shallow pool never showed it. 208 witnesses.
    """
    verdict = _receipt()["verdict"]["F5_held_out_reachability"]
    assert verdict["MET"] is False
    assert verdict["collisions_on_depth_3"]["collisions_on_the_deep_pool"] == 208
    assert verdict["chosen_on_depth_2"] == ["increments[probe_new_content]",
                                            "decrements[probe_new_content]"]


def test_the_declared_cell_threshold_is_reported_as_missed_not_as_moved() -> None:
    """F4 declared at most four cells at the top rung. FILESYSTEM gives five. It stays missed."""
    verdict = _receipt()["verdict"]["F4_the_ladder_is_the_exchange_rate"]
    assert verdict["MET"] is False
    assert verdict["cells_by_rung"]["FILESYSTEM"]["derived"] == 5
    assert verdict["cells_are_pure_at_the_top"] is True
    assert verdict["non_increasing_along_the_ladder"] is True


def test_the_receipt_is_not_stale() -> None:
    """Re-run the round and demand the same verdicts and the same cell counts."""
    committed = _receipt()
    with tempfile.TemporaryDirectory() as where:
        fresh_path = pathlib.Path(where) / "receipt.json"
        quotient.main(["--receipt", str(fresh_path)])
        fresh = json.loads(fresh_path.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert (fresh["verdict"]["F4_the_ladder_is_the_exchange_rate"]["cells_by_rung"]
            == committed["verdict"]["F4_the_ladder_is_the_exchange_rate"]["cells_by_rung"])


def test_every_statistic_named_comes_from_the_generators_the_reading_produces() -> None:
    """No winner may name a statistic that `generators_for_rung` did not build."""
    machine = _filesystem()
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    import the_goal_is_a_relation_over_the_run_v1 as runs

    traces = runs.traces_for(machine, args, depth=2)
    names = {rung: set(quotient.generators_for_rung(rung, traces))
             for rung in ("raw", "fields", "literal", "derived")}
    receipt = _receipt()
    for machine_report in receipt["portable_goal"].values():
        for rung, rung_report in machine_report["ladder"].items():
            if rung_report["coarsest"]:
                assert set(rung_report["coarsest"]["projections"]) <= names[rung]
    for rung, rung_report in receipt["pair_goal"]["ladder"].items():
        if rung_report["coarsest"]:
            assert set(rung_report["coarsest"]["projections"]) <= names[rung]
