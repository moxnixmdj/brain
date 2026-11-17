"""Is one execution enough? Pinned: the receipt. Live: the two mechanisms the claim depends on.

The live half is deliberately the part that can be wrong in a way the receipt cannot see -- whether the
grammar can express "creates a file at a path the state does not contain", and whether the predicted
consequence of a real program is the real consequence. The first was a real bug in this module: without the
mentioned paths the space refused every action that creates a file, which looks exactly like
non-identifiability and is not.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import finite_identifiability as F  # noqa: E402
from canonical.swe_kernel import demonstration_sufficiency_v1 as D  # noqa: E402
from canonical.swe_kernel.computer_use_check_density_v1 import _has  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "DEMONSTRATION_SUFFICIENCY_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# live
# --------------------------------------------------------------------------- #
def test_the_grammar_can_express_a_file_that_does_not_exist_yet() -> None:
    """A space over the state alone cannot say "creates out.dat", and every creating action is refused.

    That is not non-identifiability, it is a vocabulary gap wearing its coat -- measured here so it cannot
    come back.
    """
    state = {"payload.dat": b"b\na\n"}
    without = D.space(state)
    with_mention = D.space(state, extra_paths=["out.dat"])
    assert not any(h.hypothesis_id.endswith(">out.dat") for h in without)
    assert any(h.hypothesis_id == "sort:payload.dat>out.dat" for h in with_mention)
    assert len(with_mention) > len(without)


def test_the_predicted_consequence_is_the_real_one_for_a_real_program(tmp_path: pathlib.Path) -> None:
    """The model of the tool has to be true, or the version space is fiction. Checked against the tool."""
    if not _has("sort"):
        pytest.skip("sort not on PATH")
    state = {"payload.dat": b"zeta\nalpha\nmu\n", "keep.dat": b"untouched\n"}
    observed = D.observe("sort -o out.dat payload.dat", state, tmp_path)
    hypothesis = [h for h in D.space(state, ["out.dat"])
                  if h.hypothesis_id == "sort:payload.dat>out.dat"][0]
    assert D.signature(D._predict(hypothesis, state)) == observed["signature"]


def test_a_single_line_file_cannot_tell_sort_from_copy(tmp_path: pathlib.Path) -> None:
    """The example the whole receipt rests on, at unit scale: one line is invariant under relabelling."""
    if not _has("sort") or not _has("cp"):
        pytest.skip("sort/cp not on PATH")
    state = {"a.dat": b"only one line\n"}
    sorted_out = D.observe("sort a.dat -o out.dat", state, tmp_path)
    copied_out = D.observe("cp a.dat out.dat", state, tmp_path)
    assert sorted_out["signature"] == copied_out["signature"]


def test_the_three_way_rule() -> None:
    assert D.decide({"verdict": "VOCABULARY_INSUFFICIENT"}).startswith("REFUSE")
    assert D.decide({"verdict": "NEEDS_ONE_MORE_EXECUTION", "next_experiment": "x"}) == \
        "LEARN_ONCE_MORE__AT_x"
    assert D.decide({"verdict": "NEEDS_ONE_MORE_EXECUTION", "next_experiment": None}).startswith("REFUSE")


def test_an_observation_no_reading_predicts_is_refused_not_memorised() -> None:
    """`sort -R` on a multi-line file: the vocabulary has no reading for it, and the answer is not a guess."""
    if not _has("sort"):
        pytest.skip("sort not on PATH")
    hypotheses = [F.Hypothesis("identity", {"kind": "identity"}),
                  F.Hypothesis("copy:a>b", {"kind": "copy", "src": "a.dat", "dst": "out.dat"})]
    states = {"s": {"a.dat": b"one\ntwo\n", "out.dat": b""}}
    table = D.experiment_table(hypotheses, states)
    verdict = D.sufficiency(hypotheses, table, {"s": D.signature({"a.dat": b"one\ntwo\n",
                                                                 "out.dat": b"one\ntwo\n"})}, ["s"])
    # neither reading leaves out.dat equal to a.dat: identity does not write it, copy does -- so one fits
    assert verdict["verdict"] in ("IDENTIFIED", "BEHAVIOURALLY_IDENTICAL_IN_THIS_ENVIRONMENT",
                                  "SAFE_FOR_THIS_TASK_ONLY", "NEEDS_ONE_MORE_EXECUTION")
    impossible = D.sufficiency(hypotheses, table,
                               {"s": D.signature({"a.dat": b"one\ntwo\n", "out.dat": b"neither\n"})}, ["s"])
    assert impossible["verdict"] == "VOCABULARY_INSUFFICIENT"


# --------------------------------------------------------------------------- #
# pinned
# --------------------------------------------------------------------------- #
def test_the_receipt_numbers(report: dict) -> None:
    assert report["chains"] == 7
    assert set(report["hypothesis_space_sizes"].values()) == {343}
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert report["verdicts_after_one_execution"] == {"ACT": 5, "LEARN_ONCE_MORE": 2}
    assert report["refusals"] == ["nondeterministic_action_looks_identified"]


def test_one_execution_leaves_two_readings_that_differ_only_off_the_task(report: dict) -> None:
    """The crown case: `sort` and `sort -u` are the same action on a duplicate-free list."""
    assert report["task_safe_but_not_environment_safe"] == [
        "sort_versus_sort_unique", "sort_unique_versus_sort"]
    for chain in ("sort_versus_sort_unique", "sort_unique_versus_sort"):
        entry = [c for c in report["per_chain"] if c["chain"] == chain][0]
        assert entry["final_survivor_readings"] == ["sort:payload.dat>out.dat",
                                                    "sort_unique:payload.dat>out.dat"]
        assert entry["permanence"].startswith("TASK_SCOPED")
        assert entry["executions_to_settle"] == 1
    assert report["naive_one_shot_wrong_outside_the_task"]["sort_unique_versus_sort"] == [
        "payload_duplicates"]


def test_keeping_the_first_survivor_is_wrong_where_it_cannot_be_seen(report: dict) -> None:
    wrong = report["naive_one_shot_wrong_outside_the_task"]
    assert sum(len(v) for v in wrong.values()) >= 5
    # and the actions that ARE identified keep exactly one reading
    for chain in ("prefix_length", "reverse_versus_sort", "digest_versus_copy"):
        entry = [c for c in report["per_chain"] if c["chain"] == chain][0]
        assert entry["final_survivors"] == 1 and entry["permanence"].startswith("PERMANENT")


def test_repeating_the_same_execution_never_helped(report: dict) -> None:
    """Doing it again is informationally null: the outcome is a column already spent."""
    assert report["repeating_the_same_execution_ever_helped"] == []


def test_the_nondeterministic_action_looked_identified_first(report: dict) -> None:
    entry = [c for c in report["per_chain"]
             if c["chain"] == "nondeterministic_action_looks_identified"][0]
    assert entry["survivors_after_one_execution"] == 7          # looked perfectly learnable
    assert entry["executions_to_settle"] == 2
    assert entry["final_verdict"] == "VOCABULARY_INSUFFICIENT"
    assert entry["permanence"].startswith("REFUSED")


def test_the_receipt_is_history_not_a_declaration(report: dict) -> None:
    text = RECEIPT.read_text(encoding="utf-8")
    assert '"command"' not in text
    assert '"argv":' not in text
    for entry in report["per_chain"]:
        assert entry["invocation"]
        assert entry["goal"]["invocation"]
