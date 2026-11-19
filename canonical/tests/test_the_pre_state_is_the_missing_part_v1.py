"""The pre-state is the missing part: the retraction, the witness, the price, and the arithmetic.

The round claims something narrow and checkable: the previous receipt's "irreducible" pair of statements
was forced by the suite starting at reset, and one real action from one real pre-state separates it. These
tests hold the retraction, the two witnesses (one substantive, one necessarily degenerate), the price in
actions, the fall of the goal's class to a single conjunction, and the machine whose own reader hides the
second copy. One test re-runs the whole tool and demands the same verdicts.
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
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_pre_state_is_the_missing_part_v1 as round_  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

RECEIPT = (ROOT / "canonical" / "verification"
           / "THE_PRE_STATE_IS_THE_MISSING_PART_20261116_V1.json")
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def _machine(name: str) -> env.Machine:
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-prestate-test-"))
    machine = vocab.MACHINES[name](where / name.lower())
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    return machine


# --------------------------------------------------------------------------------------------------
# the retraction: what the last round measured, and what it was
# --------------------------------------------------------------------------------------------------

def test_the_retraction_names_the_claim_it_withdraws() -> None:
    retraction = _receipt()["retraction_of_the_previous_round"]
    assert "log2(2) = 1" in retraction["what_was_claimed"]
    assert "0 runs" in retraction["what_was_claimed"]
    assert "begins at reset" in retraction["what_it_was"] or "begin at reset" in retraction["what_it_was"]
    assert "one real action from one real pre-state" in retraction["what_is_true_now"]
    assert "convention" in retraction["why_it_matters"]


def test_the_equivalence_is_forced_and_the_premise_is_measured_not_assumed() -> None:
    verdict = _receipt()["verdict"]["P1_the_equivalence_is_forced_on_reset_started_suites"]
    assert verdict["runs"] == {"TARBALL": 87, "FILESYSTEM": 68, "SQLITE": 48}
    assert verdict["disagreements"] == 0
    assert verdict["delta_values_by_machine"] == {
        "TARBALL": [-1, 0, 1], "FILESYSTEM": [-1, 0, 1], "SQLITE": [0, 1]}
    assert verdict["unit_steps_observed"] is True
    assert verdict["fidelity_pin_walks_equal_traces_for"] == {
        "TARBALL": True, "FILESYSTEM": True, "SQLITE": True}
    assert verdict["MET"] is True


# --------------------------------------------------------------------------------------------------
# the witness, its price, and the direction that cannot be substantive
# --------------------------------------------------------------------------------------------------

def test_one_action_from_a_real_pre_state_separates_the_pair() -> None:
    verdict = _receipt()["verdict"]["P2_the_pair_separates_in_one_substantive_direction_only"]
    assert verdict["substantive_created_once_only"] == 8
    assert verdict["substantive_single_copy_only"] == 0
    assert verdict["machines_with_a_substantive_witness"] == ["FILESYSTEM", "SQLITE"]
    assert verdict["all_substantive_witnesses_exited_zero"] is True
    assert verdict["degenerate_separations_the_tool_accepted"] == 15
    assert verdict["degenerate_separations_the_tool_refused"] == 2
    assert verdict["MET"] is True


def test_the_first_witness_is_write_then_copy_and_costs_two_actions() -> None:
    price = _receipt()["verdict"]["P3_the_price_is_actions_and_not_questions"]
    witness = price["first_substantive_witness"]
    assert witness["machine"] == "FILESYSTEM"
    assert witness["prefix"] == ["FS_A1"] and witness["prefix_length"] == 1
    assert witness["atom"] == "FS_A4"
    assert (witness["count_before"], witness["count_after"], witness["delta"]) == (1, 2, 1)
    assert witness["created_once"] is True and witness["single_copy"] is False
    assert price["longest_prefix_used"] == 2
    assert price["questions_of_the_user"] == 0
    assert price["MET"] is True


def test_the_second_direction_cannot_change_anything_and_the_arithmetic_is_written_down() -> None:
    """With no decrease and unit steps, final = start + increases, so `single ∧ ¬created` forces no-ops."""
    created, single = round_.residual_pair()
    state = lambda rows: tuple((str(i), str(v)) for i, v in rows)  # noqa: E731
    one = state([("seed", env.PROBE_NEW)])
    two = state([("seed", env.PROBE_NEW), ("copy", env.PROBE_NEW)])
    # a real duplication: created_once holds, the single-copy sentence does not
    assert created.holds((one, two)) and not single.holds((one, two))
    # a do-nothing run from a state holding one copy: the only way the other direction can appear
    assert not created.holds((one, one)) and single.holds((one, one))
    # a removal never produces it, because it breaks monotonicity
    assert not created.holds((two, one)) and not single.holds((two, one))
    verdict = _receipt()["verdict"]["P2_the_pair_separates_in_one_substantive_direction_only"]
    assert "impossible" in verdict["why_the_other_direction_cannot_be_substantive"]


# --------------------------------------------------------------------------------------------------
# the goal is decided by the world once the first state is allowed to be real
# --------------------------------------------------------------------------------------------------

def test_the_goals_class_falls_from_two_statements_to_one_conjunction() -> None:
    verdict = _receipt()["verdict"]["P4_the_residual_class_is_one_on_the_widened_suite"]
    assert verdict["standard"]["disagreements"] == 0 and verdict["standard"]["class_size"] == 2
    assert verdict["widened"]["disagreements"] > 0 and verdict["widened"]["class_size"] == 1
    assert verdict["goal_statements_standard"] == 2
    assert verdict["goal_statements_widened"] == 1
    assert verdict["goal_text_widened"] == [
        "created_once[probe_new_content] ∧ final:count[probe_new_content]==1"]
    assert verdict["MET"] is True


def test_widening_costs_behaviours_and_the_receipt_says_so() -> None:
    secondary = _receipt()["secondary_evidence_full_grammar_term_set_held_fixed"]
    assert secondary["standard"]["runs"] == 203 and secondary["widened"]["runs"] == 283
    assert secondary["standard"]["behaviours"] == 429
    assert secondary["widened"]["behaviours"] == 649
    assert secondary["widened"]["behaviours"] > secondary["standard"]["behaviours"]
    assert secondary["standard"]["hypotheses"] == secondary["widened"]["hypotheses"] == 17955


# --------------------------------------------------------------------------------------------------
# the machine whose own reader is the limiting part
# --------------------------------------------------------------------------------------------------

def test_the_tarball_cannot_show_a_second_copy_because_its_reader_folds_it() -> None:
    probe = _receipt()["discovery_where_the_substantive_direction_is_missing"][
        "tarball_duplicate_member_probe"]
    assert probe["count_after_one"] == 1
    assert probe["count_after_two"] == 0
    assert [row[1] for row in probe["rows_after_two_appends"]].count(
        env.PROBE_NEW + env.PROBE_NEW) == 2
    deltas = _receipt()["discovery_where_the_substantive_direction_is_missing"][
        "delta_from_a_state_holding_one_copy"]
    assert max(deltas["TARBALL"].values()) <= 0, "no atom adds a copy on the tarball"
    assert deltas["FILESYSTEM"]["FS_A4"] == 1 and deltas["SQLITE"]["SQL_A1"] == 1


# --------------------------------------------------------------------------------------------------
# the same facts, executed here rather than read out of the receipt
# --------------------------------------------------------------------------------------------------

def test_walks_reproduces_the_runs_every_earlier_round_used() -> None:
    machine = _machine("FILESYSTEM")
    found = round_.walks(machine, ARGS, depth=2)
    assert [trace for _sequence, trace in found] == runs.traces_for(machine, ARGS, depth=2)


def test_the_witness_is_a_real_copy_of_a_real_file() -> None:
    machine = _machine("FILESYSTEM")
    atoms = {atom.ident: atom for atom in machine.atoms}
    env.execute(atoms["FS_A1"], machine, ARGS)
    one = machine.read()
    assert round_.count(tuple((i, v) for i, v in one)) == 1
    env.execute(atoms["FS_A4"], machine, ARGS)
    two = machine.read()
    assert round_.count(tuple((i, v) for i, v in two)) == 2
    created, single = round_.residual_pair()
    trace = (tuple((i, v) for i, v in one), tuple((i, v) for i, v in two))
    assert created.holds(trace) and not single.holds(trace)


def test_the_zero_disagreement_is_the_pair_and_not_every_pair() -> None:
    """A control: another statement of the same content differs from created_once on the same runs."""
    machine = _machine("FILESYSTEM")
    traces = runs.traces_for(machine, ARGS, depth=2)
    created, single = round_.residual_pair()
    assert round_.disagreements((created, single), traces) == 0
    at_least_once = demand.Term(
        f"at_least_once[{env.PROBE_NEW}]",
        lambda t: any(round_.count(state) >= 1 for state in t))
    assert round_.disagreements((created, at_least_once), traces) > 0
    assert round_.disagreements((single, at_least_once), traces) > 0


def test_nothing_was_answered_by_a_model() -> None:
    receipt = _receipt()
    assert receipt["verdict"]["P6_zero"]["MET"] is True
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    assert receipt["verdict"][
        "P5_no_pre_state_is_fabricated_and_no_substantive_witness_is_a_refusal"]["not_reproduced"] == 0


# --------------------------------------------------------------------------------------------------
# the receipt is not stale
# --------------------------------------------------------------------------------------------------

def test_the_receipt_recomputes_to_the_same_verdicts() -> None:
    committed = _receipt()
    with tempfile.TemporaryDirectory() as where:
        fresh_path = pathlib.Path(where) / "receipt.json"
        round_.main(["--receipt", str(fresh_path)])
        fresh = json.loads(fresh_path.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert fresh["witnesses"] == committed["witnesses"]
    assert fresh["secondary_evidence_full_grammar_term_set_held_fixed"] == \
        committed["secondary_evidence_full_grammar_term_set_held_fixed"]
    assert fresh["discovery_where_the_substantive_direction_is_missing"] == \
        committed["discovery_where_the_substantive_direction_is_missing"]
