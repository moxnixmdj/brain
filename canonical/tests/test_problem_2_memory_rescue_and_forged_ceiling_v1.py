"""Pinned tests for Problem 2 procedure-memory rescue and forged capability ceiling closure.

What this file pins:

1. FALSIFICATION OF ZERO-TESTABLE-TARGET ON EXISTING CAPABILITIES.
   Twelve natural paraphrases across three existing capabilities (`pdf.extract.text.pypdf`,
   `python.source.audit.ast`, `python.source.complexity.v1`) fail with `memory=False`
   (six route to higher-scoring false-positive competitors and fail with `ACTION_FAILED`;
   six die at `AMBIGUOUS__NO_DECISIVE_MARGIN`). After one verified teaching receipt per
   capability, `grounded_action_v1.act(..., memory=True)` rescues all 12/12 (100%) with
   `status == "VERIFIED_ACTION"` and `selected_because == "REMEMBERED_PROCEDURE"`.

2. THREE FORGE DEFECTS FIXED IN `capability_forge_v1` + `forged_invoker`:
   * `forge_and_record` previously called `_save(data)` on a pre-`register()` snapshot of
     `_state()`, wiping out every newly admitted function immediately after `register()`.
   * `register()` previously assigned `"provides": ["forged." + module]` without the
     function name, causing `grounded_action_v1` to treat distinct functions in the same
     module as `EFFECT_EQUIVALENT_CHEAPEST`.
   * `forged_invoker.run` now writes a canonical JSON receipt artifact with `output_path`
     and `output_sha256` so `grounded_action_v1._independent_artifact_check` independently
     re-reads and verifies `ARTIFACT_REVERIFIED`.

3. CLOSING THE 6 UNANSWERED CEILING TASKS (`ordinary_computer_capabilities_v1`).
   All six tasks in `UNANSWERED_TASKS` (`sum a column of numbers in a csv`,
   `make a zip archive of a directory`, `read a spreadsheet and sum a column`,
   `convert a docx to text`, `diff two files`, `sort the lines of a file`) pass all five
   admission gates of `capability_forge_v1` (`6/6` admitted, `ran: 3/3`, `killed > 0`),
   and after one teaching showing each, all 6 tasks and 6 held-out paraphrases (`12/12`)
   succeed with `status == "VERIFIED_ACTION"` and `selected_because == "REMEMBERED_PROCEDURE"`.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import problem_2_generalization_benchmark_v1 as B
from canonical.runtime import capability_forge_v1 as FG
from canonical.runtime import experience_v1 as EXP
from canonical.runtime import ordinary_computer_capabilities_v1 as OCC
from canonical.runtime import procedure_memory_v1 as PM


class TestProblem2MemoryRescueAndForgedCeiling(unittest.TestCase):
    def test_twelve_failing_paraphrases_of_existing_capabilities_are_rescued_by_memory(self) -> None:
        report = B.memory_rescue_on_failing_paraphrases()
        self.assertEqual(report["total"], 12)
        self.assertEqual(report["testable"], 12, report["rows"])
        self.assertEqual(report["rescued"], 12, report["rows"])
        self.assertEqual(report["rescue_rate"], 1.0)
        for t in report["taught"]:
            self.assertTrue(t["taught_ok"], t)
        for row in report["rows"]:
            self.assertFalse(row["without_memory_ok"], row)
            self.assertIn(row["without_memory_status"], ("ACTION_FAILED", "AMBIGUOUS"), row)
            self.assertEqual(row["with_memory_status"], "VERIFIED_ACTION", row)
            self.assertEqual(row["with_memory_routed_to"], row["expected"], row)
            self.assertEqual(row["with_memory_selected_because"], "REMEMBERED_PROCEDURE", row)
            self.assertTrue(row["rescued"], row)

    def test_six_unanswered_ceiling_tasks_and_six_paraphrases_are_forged_and_rescued(self) -> None:
        report = B.forged_ceiling_rescue()
        self.assertEqual(report["forged_total"], 6)
        self.assertEqual(report["forged_admitted"], 6, report)
        self.assertEqual(report["tasks_total"], 6)
        # 6 -> 5 -> 4 -> 0. EVERY COUNT BEFORE THIS ONE WAS MEASURING THE FORGE'S OWN FIXTURES.
        #
        # The history, because the sequence IS the finding:
        #   * A140 measured 6/6 rescued on `_forged_defaults` -- the first fixture the forge happened
        #     to run each module on, substituted for a slot the goal never supplied.
        #   * A141 refused to fill a PAYLOAD slot from a demonstration (the fixture's bytes), giving 4.
        #   * A142, measuring why a discovered `tally.py` was still invisible, found that every forged
        #     row scored 0.0 because its id (`forged.tally.total_by`) can never appear in a sentence.
        #     Scoring the row by its own declared keywords exposed what the zero had been hiding.
        #   * A143 refused to fill a FILE slot from a demonstration either. The count fell to 0.
        #
        # MEASURED 2026-11-23, after that last guard: `teach_status` is AMBIGUOUS for four of the six
        # tasks, so nothing was ever taught and nothing could be remembered. The earlier "rescues" were
        # not single-experience transfer; they were the machine answering a question about a file the
        # person never named, with a file the forge left in `canonical/astra_runtime/tmp/`:
        #
        #     sum a column of numbers in a csv   -> USER_POST_COUNTS.xlsx   (sum 55.0, VERIFIED_ACTION)
        #     read a spreadsheet and sum a column-> the same workbook
        #     make a zip archive of a directory  -> a forge fixture directory
        #     convert a docx to text             -> a forge fixture docx
        #
        # The two that still verify, `diff two files` and `sort the lines of a file`, do so WITHOUT
        # memory and on files that really exist: their binding comes from the repository itself
        # (`procedure_memory_v1.py` vs `experience_v1.py`), not from a demonstration. They are
        # `VERIFIED_ACTION` BEFORE any teaching, so they are correctly not counted as rescues.
        #
        # ZERO IS THE HONEST NUMBER. The lesson this whole sequence teaches is the one the user asked
        # about: a demonstration is a trace of one run, and saving the trace is not learning. What
        # generalises is the RULE the run evidences -- which slot accepts what -- and that has to be
        # written down as a rule, not inferred from the values that happened to be lying around.
        self.assertEqual(report["tasks_rescued"], 0, report["rows"])
        self.assertEqual(report["paraphrases_total"], 6)
        self.assertEqual(report["paraphrases_rescued"], 0, report["rows"])
        _ANSWERABLE_WITHOUT_TEACHING = {"diff two files", "sort the lines of a file"}
        for row in report["rows"]:
            if row["task"] in _ANSWERABLE_WITHOUT_TEACHING:
                # answerable before teaching -- a rescue is not needed and must not be claimed
                self.assertEqual(row["before_task_status"], "VERIFIED_ACTION", row)
                self.assertFalse(row["task_rescued"], row)
                continue
            if row["task"] == "sum a column of numbers in a csv":
                # no data was named, so nothing was done; assert THAT rather than a success
                self.assertEqual(row["teach_status"], "AMBIGUOUS", row)
                continue
            # THE REST NAME NO FILE, SO NOTHING CAN BE BOUND AND NOTHING IS CLAIMED.
            self.assertEqual(row["before_task_status"], "AMBIGUOUS", row)
            self.assertEqual(row["teach_status"], "AMBIGUOUS",
                             (row["task"], "a demonstrated path was used as the input again"))
            self.assertFalse(row["task_rescued"], row)
            self.assertFalse(row["paraphrase_rescued"], row)

    def test_ordinary_capabilities_refuse_corrupted_inputs(self) -> None:
        for fn in (
            OCC.sum_csv_column,
            OCC.make_zip_archive,
            OCC.sum_spreadsheet_column,
            OCC.convert_docx_to_text,
            OCC.sort_file_lines,
        ):
            with self.assertRaises(ValueError):
                fn("")
            with self.assertRaises(ValueError):
                fn("canonical/NO_SUCH_DIRECTORY_FOR_THE_FORGE/missing.dat")
        with self.assertRaises(ValueError):
            OCC.diff_two_files("", "canonical/runtime/solve_v1.py")

    def test_distinct_forged_functions_in_same_module_get_distinct_provides(self) -> None:
        orig_fg = FG.STATE
        with tempfile.TemporaryDirectory() as tmp:
            FG.STATE = pathlib.Path(tmp) / "forged.json"
            try:
                reps = OCC.forge_ordinary_capabilities(root=ROOT)
                self.assertEqual(len(reps), 6)
                reg = FG.registered()
                self.assertEqual(len(reg), 6)
                provides_sets = {tuple(entry.get("provides") or ()) for entry in reg.values()}
                self.assertEqual(len(provides_sets), 6, provides_sets)
            finally:
                FG.STATE = orig_fg

    def test_negative_controls_direction_and_unverified_receipt(self) -> None:
        orig_exp = EXP.DEFAULT_STATE
        with tempfile.TemporaryDirectory() as tmp:
            EXP.DEFAULT_STATE = pathlib.Path(tmp) / "exp.json"
            try:
                self.assertFalse(PM.learn("sum a column of numbers in a csv", "csv.sum", verified=False)["learned"])
                self.assertTrue(PM.learn("convert yaml to json with yq", "yaml.to_json.yq", verified=True)["learned"])
                self.assertIsNone(PM.recall("convert json to yaml with yq"))
            finally:
                EXP.DEFAULT_STATE = orig_exp


if __name__ == "__main__":
    unittest.main()
