"""The measurement's integrity rules, tested on a corpus built here so they can fail here.

The claim a QuixBugs number makes is only as good as three properties of the harness:
  1. the answer key cannot reach the solver -- `correct_*` is never copied into a task directory;
  2. the verdict is the corpus's own test, re-run by the harness, not the repair loop's own claim;
  3. a bug whose defect does not reproduce is not counted as repaired, and a bug whose tests already
     pass is not counted at all.
These are tested against a miniature corpus with the same layout as the real one, so that a
regression here cannot be hidden behind a network fetch or a real corpus's quirks.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as harness  # noqa: E402
from canonical.tools import quixbugs_one_shot_transfer_measure_v1 as transfer  # noqa: E402


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip())


def make_corpus(root: pathlib.Path, *, defective: str, correct: str) -> None:
    """The same layout jkoppel/QuixBugs uses, including the answer key the solver must not see."""
    write(root / "python_programs" / "add_one.py", defective)
    write(root / "correct_python_programs" / "add_one.py", correct)
    write(root / "python_testcases" / "load_testdata.py", '''
        import json
        from pathlib import Path


        def load_json_testcases(algorithm):
            root = Path(__file__).parent / ".."
            with open(root / f"json_testcases/{algorithm}.json") as handle:
                return [json.loads(line) for line in handle]
    ''')
    write(root / "json_testcases" / "add_one.json", '[[1], 2]\n[[-1], 0]\n')
    write(root / "python_testcases" / "test_add_one.py", '''
        import pytest
        from load_testdata import load_json_testcases

        if pytest.use_correct:
            from correct_python_programs.add_one import add_one
        else:
            from python_programs.add_one import add_one

        testdata = load_json_testcases(add_one.__name__)


        @pytest.mark.parametrize("input_data,expected", testdata)
        def test_add_one(input_data, expected):
            assert add_one(*input_data) == expected
    ''')
    write(root / "conftest.py", '''
        import pytest


        def pytest_addoption(parser):
            parser.addoption("--correct", action="store_true", help="run tests on the correct version")


        def pytest_configure(config):
            pytest.use_correct = config.getoption("--correct")
    ''')


class TheAnswerKeyCannotReachTheSolver(unittest.TestCase):
    def test_build_task_never_copies_correct_programs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "corpus"
            make_corpus(root, defective="def add_one(x):\n    return x - 1\n",
                        correct="def add_one(x):\n    return x + 1\n")
            task = pathlib.Path(tmp) / "task"
            row = harness.build_task(root, "add_one", task)
            self.assertFalse((task / harness.ANSWER_KEY).exists(),
                             "the answer key must never reach a solver-visible directory")
            self.assertFalse((task / "correct_python_programs").exists())
            self.assertTrue((task / "python_programs" / "add_one.py").is_file())
            self.assertTrue((task / "json_testcases" / "add_one.json").is_file(),
                            "the corpus's test data is the oracle, not the answer key")
            self.assertEqual(row["program_path"], "python_programs/add_one.py")

    def test_hashes_record_what_was_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "corpus"
            make_corpus(root, defective="def add_one(x):\n    return x - 1\n",
                        correct="def add_one(x):\n    return x + 1\n")
            row = harness.build_task(root, "add_one", pathlib.Path(tmp) / "task")
            self.assertEqual(len(row["program_sha256"]), 64)
            self.assertEqual(len(row["test_sha256"]), 64)


class TheVerdictIsTheCorpusTest(unittest.TestCase):
    def test_a_failing_program_is_a_failing_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "corpus"
            make_corpus(root, defective="def add_one(x):\n    return x - 1\n",
                        correct="def add_one(x):\n    return x + 1\n")
            task = pathlib.Path(tmp) / "task"
            row = harness.build_task(root, "add_one", task)
            verdict = harness.run_pytest(task, row["test_path"], timeout=120)
            self.assertNotEqual(verdict["returncode"], 0)

    def test_the_correct_program_passes_the_same_test(self):
        """The oracle must be able to say yes, or a repair number means nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "corpus"
            make_corpus(root, defective="def add_one(x):\n    return x - 1\n",
                        correct="def add_one(x):\n    return x + 1\n")
            task = pathlib.Path(tmp) / "task"
            row = harness.build_task(root, "add_one", task)
            (task / row["program_path"]).write_text("def add_one(x):\n    return x + 1\n")
            verdict = harness.run_pytest(task, row["test_path"], timeout=120)
            self.assertEqual(verdict["returncode"], 0, verdict["tail"])

    def test_a_task_whose_defect_does_not_reproduce_is_not_a_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "corpus"
            make_corpus(root, defective="def add_one(x):\n    return x + 1\n",
                        correct="def add_one(x):\n    return x + 1\n")
            row = harness.measure(root, "add_one", wall_budget_s=30, timeout_s=60)
            self.assertEqual(row["stage"], "DEFECT_DOES_NOT_REPRODUCE")
            self.assertNotIn("loop_status", row)


class TheSplitIsResultBlind(unittest.TestCase):
    def test_split_is_deterministic_and_disjoint(self):
        names = [f"bug_{i:02d}" for i in range(40)]
        train, held = transfer.split(names)
        self.assertEqual(len(train), 20)
        self.assertEqual(len(held), 20)
        self.assertEqual(set(train) & set(held), set())
        self.assertEqual(sorted(train + held), sorted(names))
        self.assertEqual(transfer.split(names), (train, held))

    def test_split_does_not_follow_input_order(self):
        names = [f"bug_{i:02d}" for i in range(40)]
        self.assertEqual(transfer.split(names), transfer.split(list(reversed(names))))

    def test_an_out_of_range_split_is_refused(self):
        with self.assertRaises(ValueError):
            transfer.split([f"b{i}" for i in range(10)], train_size=10)


class TheReceiptCountsWhatHappened(unittest.TestCase):
    def test_summarise_folds_stages_instead_of_trusting_them(self):
        rows = [
            {"task": "a", "stage": "REPAIRED__CORPUS_TEST_PASSES",
             "accepted": [{"taught_by": ["other"], "rung": "NODE_SUBSTITUTION", "mutation": "m"}]},
            {"task": "b", "stage": "NOT_REPAIRED__NO_STRICTLY_IMPROVING_CANDIDATE"},
            {"task": "c", "stage": "REPAIRED__CORPUS_TEST_PASSES",
             "accepted": [{"taught_by": ["c"], "rung": "LEAF_SUBSTITUTION", "mutation": "m"}]},
        ]
        summary = transfer.summarise(rows)
        self.assertEqual(summary["held_out_tasks"], 3)
        self.assertEqual(summary["repaired"], 2)
        self.assertEqual(summary["repaired_by_transferred_edit"], 1,
                         "a repair taught by the task itself is not transfer")
        self.assertEqual(summary["by_rung"]["NODE_SUBSTITUTION"], ["a"])
        self.assertEqual(summary["by_rung"]["LEAF_SUBSTITUTION"], ["c"])


if __name__ == "__main__":
    unittest.main()
