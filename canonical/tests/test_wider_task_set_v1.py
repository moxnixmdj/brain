"""The wider task set, and the shrinkage it exposed.

V35 reported 3 solved of 8. The same operators, on 28 mined tasks never used to design them, solve 0. These
tests lock both numbers in so neither can be quietly dropped from the record later.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools import mine_fail_to_pass_v1 as miner  # noqa: E402

CORPUS = REPO / "canonical" / "corpus" / "fail_to_pass_tasks_20261124_V1.json"
RECEIPT = REPO / "canonical" / "corpus" / "wider_task_set_20261124_V1.json"


def test_added_test_functions_are_read_from_the_diff():
    diff = (
        "+    @pytest.mark.parametrize('x', [1])\n"
        "+    def test_something(self):\n"
        "+        assert True\n"
        "-    def test_removed(self):\n"
    )
    assert miner.added_tests(diff) == ["test_something"]


def test_the_wider_set_is_at_least_twenty_eight_genuine_tasks():
    corpus = json.loads(CORPUS.read_text())
    assert len(corpus["tasks"]) == 28
    for task in corpus["tasks"]:
        assert task["test"].startswith("tests/")
        assert task["failed_nodes"] and "::" in task["failed_nodes"][0]
        # a class-based node keeps its test name; splitting on spaces used to lose it
        node = task["failed_nodes"][0]
        assert node.count("::") >= 1
        assert node.rsplit("::", 1)[-1].strip(), node


def test_no_mined_node_is_truncated_to_a_class_name():
    """A parametrized node legitimately contains spaces; a node truncated at a space ends at a ClassName."""
    corpus = json.loads(CORPUS.read_text())
    for task in corpus["tasks"]:
        leaf = task["failed_nodes"][0].rsplit("::", 1)[-1]
        assert leaf, task["sha"]
        if " " in leaf:
            # pytest only permits spaces inside [...] parameters, never before them
            assert "[" in leaf, f"{task['sha']} lost its test name: {leaf!r}"


def test_the_shrinkage_is_recorded_and_not_hidden():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["generation_on_28"]["solved"] == 0
    assert receipt["generation_on_28"]["denominator"] == 28
    assert receipt["the_shrinkage"]["v35_reported"] == "3 solved of 8"
    assert "fit to the tasks it was built on" in receipt["the_shrinkage"]["honest_statement"]


def test_localisation_survives_the_wider_set():
    receipt = json.loads(RECEIPT.read_text())
    localisation = receipt["localisation_on_28"]
    assert localisation["combined_top1"] >= 17
    assert localisation["combined_within_five"] >= 27
    assert localisation["combined_top1"] > localisation["frames_top1"]


def test_the_change_kind_distribution_sums_to_the_set():
    receipt = json.loads(RECEIPT.read_text())
    kinds = receipt["what_kind_of_change_the_28_need"]
    total = sum(value for key, value in kinds.items() if key != "reading")
    assert total == 28


def test_no_benchmark_score_is_claimed():
    receipt = json.loads(RECEIPT.read_text())
    text = json.dumps(receipt).lower()
    for forbidden in ("pass@1", "resolved_rate", "swe-bench score"):
        assert forbidden not in text
