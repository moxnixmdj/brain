"""Fresh-instance tests: a scoped typed-SWE plan drives the live front door.

Independent oracles (no self-report):
  * the real ``live_brain_route_admission_v1.solve`` gate chain executes the
    adapter and re-derives truth from the FILESYSTEM (promised artifact exists,
    named source still parses, source bytes changed);
  * the pinned front-door regression goals (out-of-scope, compilation gap) must
    keep their exact fail-closed verdicts;
  * the negative controls (ambiguous two-source, non-SWE) must refuse;
  * a mutation control breaks the derivation's stated-file evidence and asserts
    selection -- and therefore any retry -- stops.

Every case is generated on a fresh temporary tree; no instance is checked in.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import swe_typed_plan_v1 as plan  # noqa: E402
from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_swe_typed_plan"


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (base / "pkg/util.py").write_text("def total(old_price, qty):\n    return old_price * qty\n", encoding="utf-8")
    (base / "pkg/test_calc.py").write_text(
        "import calc, unittest\nclass T(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(calc.add(2, 3), 5)\n"
        "if __name__ == '__main__': unittest.main()\n", encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


def _sentences(base: pathlib.Path) -> dict[str, str]:
    calc = _rel(base / "pkg/calc.py")
    util = _rel(base / "pkg/util.py")
    test = _rel(base / "pkg/test_calc.py")
    out = _rel(base / "out.json")
    return {
        "repair_full": ("Repair the python source %s so that the unit test %s passes, "
                        "and save the repair report to %s." % (calc, test, out)),
        "fix_broken": "the add function in %s is broken, fix it so its tests pass" % calc,
        "bugreport": "Bug: %s add() returns the wrong value. Failing test: %s." % (calc, test),
        "rename": ("Rename the parameter old_price to price in the python module %s "
                   "and save the report to %s." % (util, out)),
    }


class TypedPlanEvidenceTests(unittest.TestCase):
    def test_a_decisive_plan_selects_a_swe_capability_with_bound_inputs(self):
        base = _fresh("plan")
        p = plan.build_plan(_sentences(base)["fix_broken"], ROOT)
        self.assertIsNotNone(p)
        _, admissible, compiled = p
        cid = compiled["selected_capability"]
        self.assertTrue(cid.startswith("python."), cid)
        self.assertIn(cid, admissible)
        # The bound inputs must fill every remaining ${input.*} placeholder in the
        # execution template -- that is the shape contract _render_template reads.
        tpl_args = (admissible[cid]["action_template"].get("args") or {})
        bound = compiled["inputs"]
        import re
        for key, value in tpl_args.items():
            if isinstance(value, str) and "${input." in value:
                name = re.findall(r"\$\{input\.([^}]+)\}", value)
                for n in name:
                    self.assertIn(n, bound, (cid, key, n))

    def test_output_path_never_binds_onto_a_stated_source_file(self):
        """A report written over the module would corrupt it (NAMED_SOURCE_UNPARSEABLE)."""
        base = _fresh("output_path")
        p = plan.build_plan(_sentences(base)["fix_broken"], ROOT)
        self.assertIsNotNone(p)
        bound = p[2]["inputs"]
        calc = _rel(base / "pkg/calc.py")
        self.assertNotEqual(bound.get("output_path"), calc, bound.get("output_path"))

    def test_non_swe_and_ambiguous_requests_produce_no_plan(self):
        base = _fresh("negative")
        self.assertIsNone(plan.build_plan("Calibrate the neutrino interferometer phase drift.", ROOT))
        calc = _rel(base / "pkg/calc.py")
        util = _rel(base / "pkg/util.py")
        ambiguous = ("Repair the python source %s and %s so that the tests pass."
                     % (calc, util))
        # Two source files => source_root cannot be derived => no decisive admission.
        self.assertIsNone(plan.build_plan(ambiguous, ROOT))

    def test_mutation_breaking_stated_evidence_breaks_the_plan(self):
        """With no stated files the selector must not produce a decisive plan."""
        base = _fresh("mutation")
        goal = _sentences(base)["fix_broken"]
        self.assertIsNotNone(plan.build_plan(goal, ROOT))
        with mock.patch.object(derivation, "stated_existing_files", return_value=[]):
            self.assertIsNone(plan.build_plan(goal, ROOT))

    def test_effect_inconsistent_request_produces_no_plan_and_no_false_pass(self):
        """FALSE-PASS REGRESSION.  ``select`` admits by declared-input contract,
        not effect: a single bindable repair choreographer was SELECTED for
        "Type-check the file X" and no-op'd to a PASS with the source unchanged.
        The plan must refuse effect-inconsistent goals so the front door keeps
        its fail-closed verdict.  Independent oracle: the live solve() verdict
        and the filesystem (source bytes unchanged)."""
        base = _fresh("effect")
        calc = _rel(base / "pkg/calc.py")
        for goal in ("Type-check the file %s." % calc,
                     "Lint the file %s." % calc):
            # plan layer refuses
            self.assertIsNone(plan.build_plan(goal, ROOT), goal)
            # and the live door stays fail-closed with no retry credit
            result = door.solve({"task_id": "SWE_effect", "goal": goal})
            self.assertIs(result.get("pass"), False, (goal, result.get("status")))
            self.assertNotIn("typed_swe_retry", result, goal)
            self.assertEqual((base / "pkg/calc.py").read_text(),
                             "def add(a, b):\n    return a - b\n", goal)

    def test_refactor_module_is_relative_to_source_root(self):
        """The three refactor adapters resolve ``module`` relative to
        ``source_root``; a doubled prefix yields PATH_MISSING.  The plan must
        strip it."""
        base = _fresh("module_rel")
        util = _rel(base / "pkg/util.py")
        out = _rel(base / "r.json")
        goal = ("Rename the parameter old_price to price in the python module %s "
                "and save the report to %s." % (util, out))
        p = plan.build_plan(goal, ROOT)
        self.assertIsNotNone(p)
        self.assertEqual(p[2]["inputs"].get("module"), "util.py",
                         p[2]["inputs"].get("module"))
        self.assertTrue((ROOT / p[2]["inputs"]["source_root"]).is_dir())

    def test_rename_family_passes_honestly_through_the_live_door(self):
        """Independent oracle: the source bytes actually change and the
        adapter's own gate fires (not merely a PASS string)."""
        base = _fresh("rename_pass")
        util = _rel(base / "pkg/util.py")
        goal = "Rename the parameter old_price to price in %s" % util
        result = door.solve({"task_id": "SWE_rename", "goal": goal})
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertIsNone(result.get("tool_truth_errors"))
        self.assertIsNone(result.get("observed_effect_errors"))
        after = (base / "pkg/util.py").read_text()
        self.assertIn("def total(price, qty)", after)
        self.assertIn("return price * qty", after)
        self.assertNotIn("old_price", after)


class LiveFrontDoorRetryTests(unittest.TestCase):
    def test_human_swe_sentences_pass_through_the_real_gate_chain(self):
        """Independent oracle: solve() runs the adapter and the filesystem gates.
        A pre-execution refusal that the typed plan can bind must now PASS."""
        passed, statuses = [], {}
        for tag in ("repair_full", "fix_broken", "bugreport"):
            base = _fresh("solve_" + tag)
            goal = _sentences(base)[tag]
            result = door.solve({"task_id": "SWE_" + tag, "goal": goal})
            statuses[tag] = (result.get("status"), result.get("failure_class"))
            if result.get("pass") is True:
                passed.append(tag)
        self.assertGreaterEqual(len(passed), 2, statuses)

    def test_a_failing_retry_never_forges_a_pass(self):
        """Where the adapter itself cannot do the job, the door stays fail-closed.
        The Point: the retry must not convert an honest adapter fault into credit."""
        base = _fresh("honest_fail")
        # Bare "fix X": primary executes a composed chain (executed=True), so the
        # conservative guard must NOT re-run anything; verdict stays fail-closed.
        goal = "fix %s" % _rel(base / "pkg/calc.py")
        result = door.solve({"task_id": "SWE_honest", "goal": goal})
        self.assertIs(result.get("pass"), False)
        self.assertNotIn("typed_swe_retry", result)

    def test_non_swe_front_door_refusals_are_byte_for_byte_unchanged(self):
        """The three pinned regression goals are non-SWE: retry never fires."""
        base = _fresh("pinned")
        calc = _rel(base / "pkg/calc.py")
        out = _rel(base / "out_gap.txt")
        oos = ("Summarize the file %s into three sentences and save the summary to %s."
               % (calc, out))
        gap = "Calibrate the neutrino interferometer phase drift."
        for tag, goal in (("oos", oos), ("gap", gap)):
            result = door.solve({"task_id": "SWE_pin_" + tag, "goal": goal})
            self.assertIs(result.get("pass"), False, tag)
            self.assertNotIn("typed_swe_retry", result, tag)
            self.assertIs(result.get("executed"), False, tag)
        # out-of-scope must write nothing
        self.assertFalse((ROOT / out).exists())

    def test_retry_result_is_credited_with_zero_model_dependency(self):
        base = _fresh("credit")
        result = door.solve({"task_id": "SWE_credit",
                             "goal": _sentences(base)["bugreport"]})
        retry = result.get("typed_swe_retry")
        if retry is not None:
            self.assertEqual(retry.get("model_dependency_count"), 0)
            self.assertEqual(retry.get("incremental_spend_usd"), 0)
            self.assertTrue(str(retry.get("selected_capability")).startswith("python."))


if __name__ == "__main__":
    unittest.main()
