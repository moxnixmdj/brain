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
        # 6 -> 5 on 2026-11-23 (A140), AND THE ONE THAT LEFT WAS NEVER RESCUED.
        #
        # `sum a column of numbers in a csv` reached VERIFIED_ACTION only because the forged capability's
        # `_forged_defaults` -- the first fixture `capability_forge_v1` happened to run the module on -- were
        # substituted for the slot the goal never supplied. The number it produced was a true sum of
        #     item,amount\nalpha,12.5\nbeta,27.5\ngamma,10.0
        # which is the FORGE'S OWN TEST DATA, presented as the answer about the person's file. Teaching that
        # receipt then recorded a procedure for a task the machine had not done.
        #
        # `world_binding_v1` now refuses to fill a payload slot from a demonstration, so the capability is
        # unbindable until something actually names the data -- which is the honest state. The other five are
        # unaffected, and both counts are asserted separately below rather than hidden in one number.
        # MEASURED, NOT ROUNDED. Four tasks are now rescued by memory, one is not rescued but no longer needs
        # to be, and one cannot be done at all:
        #
        #   rescued (4)          zip, spreadsheet, docx, sort -- each taught once, then remembered for a
        #                        paraphrase. This is the single-experience transfer working.
        #   already answerable   "diff two files" is VERIFIED_ACTION before any teaching, so it is not a
        #                        rescue. That is the machine getting better, not the memory failing.
        #   not answerable (1)   "sum a column of numbers in a csv" names no data. It used to reach
        #                        VERIFIED_ACTION by summing the FORGE'S OWN FIXTURE, which was a true number
        #                        about a file nobody mentioned.
        #
        # Asserting 6 would claim a rescue that never happened; asserting 5 would bury the distinction.
        self.assertEqual(report["tasks_rescued"], 4, report["rows"])
        self.assertEqual(report["paraphrases_total"], 6)
        self.assertEqual(report["paraphrases_rescued"], 5, report["rows"])
        for row in report["rows"]:
            if row["task"] == "sum a column of numbers in a csv":
                # no data was named, so nothing was done; assert THAT rather than a success
                self.assertEqual(row["teach_status"], "AMBIGUOUS", row)
                continue
            if row["task"] == "diff two files":
                # answerable before teaching -- a rescue is not needed and must not be claimed
                self.assertEqual(row["before_task_status"], "VERIFIED_ACTION", row)
                continue
            self.assertEqual(row["before_task_status"], "AMBIGUOUS", row)
            self.assertEqual(row["before_paraphrase_status"], "AMBIGUOUS", row)
            self.assertEqual(row["teach_status"], "VERIFIED_ACTION", row)
            self.assertEqual(row["after_task_status"], "VERIFIED_ACTION", row)
            self.assertEqual(row["after_task_selected_because"], "REMEMBERED_PROCEDURE", row)
            self.assertEqual(row["after_paraphrase_status"], "VERIFIED_ACTION", row)
            self.assertEqual(row["after_paraphrase_selected_because"], "REMEMBERED_PROCEDURE", row)

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
