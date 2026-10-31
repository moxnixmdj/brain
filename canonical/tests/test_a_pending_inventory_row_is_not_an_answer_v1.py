"""A script's exit code is not an answer: 293 inventory rows were routable, and one of them answered.

Measured 2026-10-29 on this repository, the filesystem and the door's own trace as the oracle::

    "Show the last 3 lines of the file canonical/runtime/declared_input_derivation_v1.py"
      executed  canonical/runtime/professional_quality_declared_system_subject_verify_v1.py.auto.v1
                (a repository verification script sharing the word "declared" with the path)
      status    PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
                semantic_acceptance_complete: true      capability_id: None
      why       that row's entire expectation is returncode == 0

The loader carries two populations and the door could not tell them apart: 293 of 419 rows are
``*.py.auto.v1`` inventory records with ``status: RECEIPT_BACKED_PENDING_PROMOTION``, and **0** of
them declare ``verification.verified: true``.  Discovery is not verification, which is what the
inventory's own docstring says.

The rule is the registry's declaration plus one substring test: a pending row is routable when the
sentence contains its id verbatim (identity, which
test_live_brain_route_admission_v1.py:587 already pins), and never when a ranker guessed it from
words.  The sentences below are the same file read three ways.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import live_integrated_brain_v1 as brain  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_pending_inventory"
REL = WORK.relative_to(ROOT).as_posix()


def _fresh() -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    (WORK / "notes.txt").write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
    return WORK


class TheDeclarationDecidesWhetherARowMayRun(unittest.TestCase):
    def test_a_pending_inventory_row_is_not_verified(self):
        registry = brain.load_verified_registry()
        pending = [cid for cid, entry in registry.items()
                   if str(entry.get("status")) == "RECEIPT_BACKED_PENDING_PROMOTION"]
        self.assertGreater(len(pending), 100)
        for cid in pending[:25]:
            self.assertFalse(brain.is_verified_entry(registry[cid]), cid)
        verified = [cid for cid, entry in registry.items()
                    if str(entry.get("status")) == "VERIFIED_BOUND_CAPABILITY"]
        self.assertGreater(len(verified), 100)
        for cid in verified[:25]:
            self.assertTrue(brain.is_verified_entry(registry[cid]), cid)


class TheSentenceThatReadsThreeLinesRunsTheProgramThatReadsThem(unittest.TestCase):
    def setUp(self):
        _fresh()

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def test_the_verified_command_runner_answers_and_no_inventory_row_does(self):
        result = door.solve({"task_id": "TEST_PENDING_TAIL",
                             "goal": "Show the last 3 lines of the file %s/notes.txt" % REL})
        self.assertTrue(result.get("pass"), result.get("status"))
        route = result.get("composer_route") or {}
        self.assertEqual(route.get("chain"), ["shell.command.run"])
        argv = (route.get("tried") or [{}])[0].get("stated_command_line")
        self.assertEqual(argv, ["tail", "-n", "3", REL + "/notes.txt"])
        for row in result.get("execution") or []:
            self.assertFalse(str(row.get("capability_id") or "").endswith(".auto.v1"),
                             "an inventory row answered a question about a file")

    def test_a_provenance_question_is_refused_rather_than_answered_with_the_files_text(self):
        result = door.solve({"task_id": "TEST_PENDING_BLAME",
                             "goal": "Who last changed line 2 of %s/notes.txt?" % REL})
        self.assertFalse(result.get("pass"), result.get("status"))
        self.assertEqual(result.get("status"), "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED")
        self.assertIn("STATED_PROVENANCE_NOT_ANSWERED_BY_CAPABILITY",
                      " ".join(result.get("stated_answer_errors") or []))


if __name__ == "__main__":
    unittest.main()
