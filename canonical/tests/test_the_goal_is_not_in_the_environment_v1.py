"""The goal is not in the environment: what experience can and cannot buy, pinned by count.

These tests hold the round's five numbers and the one registered prediction, plus the filter that
decides what may count as a competing intent. Nothing here re-checks an earlier round.
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
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_goal_is_not_in_the_environment_v1 as tool  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

RECEIPT = (ROOT / "canonical" / "verification"
           / "THE_GOAL_IS_NOT_IN_THE_ENVIRONMENT_20261130_V1.json")
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


# --------------------------------------------------------------------------------------------------
# the ceiling
# --------------------------------------------------------------------------------------------------

def test_two_different_statements_have_one_behaviour_on_every_reachable_run() -> None:
    """Four intentions, one behaviour, 231 runs -- and none of the four can be separated here."""
    witness = _receipt()["verdict"]["G2_two_statements_one_behaviour"]["witness"]
    assert witness["nontrivial"] is True
    assert witness["runs"] == 231
    assert witness["mask_true_runs"] == 5
    assert witness["a"] == ["never_removed[probe_seed_content]"]
    assert witness["b"] == ["monotone[probe_seed_content]"]
    assert witness["class_statements"] == [
        "never_removed[probe_seed_content]",
        "monotone[probe_seed_content]",
        "final:count[probe_seed_content]==1",
        "final:has[seed]=probe_seed_content",
    ]


def test_the_pair_separates_in_the_next_environment() -> None:
    """"Permanently" fails exactly where the first environment never went: 32 of 196 runs."""
    verdict = _receipt()["verdict"]["G3_the_pair_separates_in_a_new_environment"]
    assert verdict["MET"] is True
    assert verdict["disagreements"] == 32
    first = _receipt()["transfer"]["first"][0]
    assert first == {"run": 13, "a": True, "b": False}


def test_the_environment_can_only_ever_identify_a_behaviour() -> None:
    """79 statements survive every run judged and they are one behaviour: the class is the knowledge."""
    report = _receipt()["machines"]["TARBALL"]
    assert report["runs"] == 231
    assert report["hypotheses"] == 11935
    assert report["distinct_behaviours_in_the_family"] == 353
    assert report["statements_consistent_with_every_run"] == 79
    assert report["behaviours_when_every_run_is_judged"] == 1
    assert report["single_term_statements_of_the_users_goal"] == [
        ["created_once[probe_new_content]"]]
    filesystem = _receipt()["machines"]["FILESYSTEM"]
    assert filesystem["distinct_behaviours_in_the_family"] == 129
    assert filesystem["statements_consistent_with_every_run"] == 11


# --------------------------------------------------------------------------------------------------
# the price of asking
# --------------------------------------------------------------------------------------------------

def test_active_questions_buy_eight_bits_where_the_environments_own_order_buys_four() -> None:
    """353 behaviours is 8.46 bits; active questions reach one behaviour in eight judgments."""
    report = _receipt()["machines"]["TARBALL"]
    active = [step["behaviours"] for step in report["active"]["steps"]]
    assert active == [353, 176, 89, 29, 14, 7, 5, 2, 1]
    assert report["active"]["converged"] is True
    assert report["active"]["judgments"] == 8
    passive = [step["behaviours"] for step in report["passive"]["steps"]]
    assert passive[-1] == 20, "the environment's own order still has 20 behaviours after eight runs"
    assert report["passive"]["converged"] is False
    assert report["passive"]["final_survivors"] == 323
    assert _receipt()["machines"]["FILESYSTEM"]["active"]["judgments"] == 6


def test_the_machine_is_known_exactly_on_a_depth_it_was_not_measured_on() -> None:
    """The registered prediction from last round: 229 of 231 decided, zero errors, two abstentions."""
    control = _receipt()["verdict"]["environment_control_registered_last_round"]["control"]
    assert control["shallow_runs"] == 32
    assert control["deep_runs"] == 231
    assert control["false_accepts"] == 0
    assert control["false_rejects"] == 0
    assert control["undecided"] == 2
    assert control["correct_where_decided"] == 229
    assert control["deep_true"] == 42


def test_nothing_was_answered_by_a_model() -> None:
    receipt = _receipt()
    assert receipt["verdict"]["G5_zero"]["MET"] is True
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


# --------------------------------------------------------------------------------------------------
# the filter that decides what may count as a competing intent
# --------------------------------------------------------------------------------------------------

def test_the_witness_filter_refuses_statements_in_vocabulary_one_machine_alone_has() -> None:
    """A literal the other machine does not have cannot carry a competing intent; the filter says so."""
    where = pathlib.Path(tempfile.mkdtemp(prefix="test-goal-"))
    machine = vocab.MACHINES["TARBALL"](where / "tarball")
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    traces = runs.traces_for(machine, ARGS, depth=3)
    family = tool.Family(traces)
    mine = tool.literals(traces)
    shared = mine - {"probe_seed_content"}
    witness = tool.ceiling_witness(family, other_literals=shared)
    assert witness is not None, "depth 3 already has a ceiling under this filter"
    for text in witness["class_statements"]:
        assert "probe_seed_content" not in text, f"a machine-only literal carried the witness: {text}"
    everything = tool.ceiling_witness(family, other_literals=mine)
    assert everything is not None


def test_the_family_is_evaluated_once_and_every_hypothesis_is_a_bitmask() -> None:
    """The eval-once discipline: masks, conjunctions and the version space all read one table."""
    where = pathlib.Path(tempfile.mkdtemp(prefix="test-family-"))
    machine = vocab.MACHINES["FILESYSTEM"](where / "fs")
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    traces = runs.traces_for(machine, ARGS, depth=2)
    family = tool.Family(traces)
    assert len(family.combos) == len(family.terms) * (len(family.terms) + 1) // 2
    assert len(family.masks) == len(family.terms)
    full = (1 << len(traces)) - 1
    assert all(0 <= mask <= full for mask in family.masks)
    combo = family.combos[0]
    assert family.by_combo[combo] == family.masks[combo[0]]
    assert family.survivors(full, 0) == [combo for combo in family.combos
                                         if family.by_combo[combo] == full]


# --------------------------------------------------------------------------------------------------
# the receipt is not stale
# --------------------------------------------------------------------------------------------------

def test_the_receipt_recomputes_to_the_same_verdicts() -> None:
    committed = _receipt()
    with tempfile.TemporaryDirectory() as where:
        fresh_path = pathlib.Path(where) / "receipt.json"
        tool.main(["--receipt", str(fresh_path)])
        fresh = json.loads(fresh_path.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert fresh["transfer"] == committed["transfer"]
    for name in ("TARBALL", "FILESYSTEM"):
        assert (fresh["machines"][name]["distinct_behaviours_in_the_family"]
                == committed["machines"][name]["distinct_behaviours_in_the_family"])
