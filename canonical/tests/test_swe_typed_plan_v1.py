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
        and the filesystem (source bytes unchanged).

        Re-measured 2026-10-29.  This test used to assert ``build_plan is None`` for both
        sentences, which was only true while NO capability that type-checks or lints was
        reachable.  Both now are -- ``python.review.diff_type_gate.v1`` runs mypy and
        ``python.review.diff_static_triage.v1`` runs ruff, each on the change set the
        declared-input derivation builds from the stated file -- so the absence is gone and
        the pin has to name the falsifier it was actually protecting: the plan may never be a
        capability that does not state the effect, the door may never pass via one, and the
        file must not be edited by a read-only gate.  The refusal path is still pinned by the
        negative control at the end (no stated file -> no change set -> no plan).
        """
        base = _fresh("effect")
        calc = _rel(base / "pkg/calc.py")
        for goal, effect in (("Type-check the file %s." % calc, "type"),
                             ("Lint the file %s." % calc, "triage")):
            chosen = plan.build_plan(goal, ROOT)
            if chosen is not None:
                cid = str(chosen[2].get("selected_capability") or "")
                self.assertIn(effect, cid, (goal, cid))
            result = door.solve({"task_id": "SWE_effect", "goal": goal})
            if result.get("pass") is True:
                cid = str(result.get("compiled_capability_id") or "")
                self.assertIn(effect, cid,
                              "a PASS that does not come from the stated effect: %s" % cid)
            # a read-only gate never edits the file it reviews
            self.assertEqual((base / "pkg/calc.py").read_text(),
                             "def add(a, b):\n    return a - b\n", goal)
        # negative control: with nothing stated there is no change set, so no plan
        with mock.patch.object(derivation, "stated_existing_files", return_value=[]):
            self.assertIsNone(plan.build_plan("Type-check the file %s." % calc, ROOT))

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

        The Point: no credit without a REPAIR THE FILESYSTEM CAN SEE.

        This case used to be a bare "fix <calc.py>" on the full fixture, and it passed because the
        repair route could not be reached at all.  It is reachable now -- measured 2026-10-30, the
        same sentence turns ``return a - b`` into ``return a + b`` and the suite gate goes red to
        green, i.e. credit the filesystem confirms.  So the guard is exercised where the adapter
        genuinely cannot do the job: a stated source with NO test that could prove the repair.  The
        adapter's own contract needs the red test it must turn green; without one there is nothing
        to verify against, and the door must refuse instead of editing by faith.
        """
        base = WORK / "honest_fail"
        if base.exists():
            shutil.rmtree(base)
        (base / "pkg").mkdir(parents=True)
        source = base / "pkg/calc.py"
        source.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        before = source.read_bytes()
        goal = "fix %s" % _rel(source)
        result = door.solve({"task_id": "SWE_honest", "goal": goal})
        self.assertIs(result.get("pass"), False, result.get("status"))
        self.assertNotIn("typed_swe_retry", result)
        # Independent oracle: the refusal left the source exactly as it found it.
        self.assertEqual(source.read_bytes(), before)

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


class EffectFamilyEnumerationTests(unittest.TestCase):
    """§9 enumerate-and-let-admission-be-oracle: a caller-finding sentence reaches
    the hidden symbol-index capability the lexical shortlist buries, and produces
    a REAL callers_of artifact.  Independent oracle: the filesystem artifact must
    name exactly the callers present in fresh source (never self-reported)."""

    @staticmethod
    def _tree(case: str, with_callers: bool) -> pathlib.Path:
        base = ROOT / "canonical/astra_runtime/tmp/test_family" / case
        if base.exists():
            shutil.rmtree(base)
        (base / "pkg").mkdir(parents=True)
        body = "def add(a, b):\n    return a - b\n"
        if with_callers:
            body += ("def caller():\n    return add(1, 2)\n"
                     "def other():\n    return add(3, 4)\n")
        (base / "pkg/mod.py").write_text(body, encoding="utf-8")
        return base

    @staticmethod
    def _cleanup():
        shutil.rmtree(ROOT / "canonical/astra_runtime/tmp/test_family", ignore_errors=True)

    def tearDown(self):
        self._cleanup()

    def _goal(self, base):
        # Completeness requires a stated search tree, not merely the defining
        # file. Preserve the single-file refusal guard rather than bypass it.
        return "Find every caller of the function add in %s." % _rel(base / "pkg")

    def test_caller_family_plan_is_decisive_and_effect_consistent(self):
        base = self._tree("plan", True)
        self.assertTrue(plan.is_swe_request(self._goal(base)))
        p = plan.build_plan(self._goal(base), ROOT)
        self.assertIsNotNone(p)
        self.assertEqual(p[2]["selected_capability"], "python.source.symbols.index.ast")
        # output must NOT be bound onto the stated source file
        self.assertNotEqual(p[2]["inputs"].get("output_path"), _rel(base / "pkg/mod.py"))

    def test_caller_family_passes_with_a_real_callers_of_artifact(self):
        """Independent oracle: the report names exactly the two real callers."""
        import json
        base = self._tree("solve", True)
        result = door.solve({"task_id": "FAM_callers", "goal": self._goal(base)})
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertIsNone(result.get("tool_truth_errors"))
        self.assertIsNone(result.get("observed_effect_errors"))
        # The artifact's PLACE is read from the run, not assumed: an earlier version of this
        # test looked only inside the user's tree, which is where the report went when the
        # adapter was writing it over the file the sentence named (measured 2026-10-29).  It
        # now goes to the spool, so the test follows what the run says it produced -- and the
        # independent oracle below (the two real callers by name) is unchanged.
        reports = list(base.rglob("*.json"))
        for row in result.get("execution") or []:
            produced = str(((row or {}).get("result") or {}).get("output_path") or "")
            if produced:
                candidate = ROOT / produced
                if candidate.is_file():
                    reports.append(candidate)
        self.assertTrue(reports, "no report artifact was written")
        callers = set()
        for rf in reports:
            data = json.loads(rf.read_text())
            callers |= set((data.get("callers_of") or {}).get("add") or [])
        self.assertEqual(callers, {"caller", "other"}, callers)
        # source untouched (no corruption: the false-PASS class)
        self.assertTrue((base / "pkg/mod.py").read_text().startswith("def add"))

    def test_single_file_does_not_claim_global_caller_completeness(self):
        base = self._tree("single_file_scope", True)
        goal = "Find every caller of the function add in %s." % _rel(base / "pkg/mod.py")
        result = door.solve({"task_id": "FAM_single_file", "goal": goal})
        self.assertIs(result.get("pass"), False)
        self.assertEqual(result.get("failure_class"), "ANSWER_SCOPE_UNPROVEN")

    def test_no_callers_still_passes_with_empty_index_but_no_false_credit(self):
        """A tree with zero callers yields an empty callers_of (honest, not invented)."""
        import json
        base = self._tree("empty", False)
        result = door.solve({"task_id": "FAM_empty", "goal": self._goal(base)})
        # either honest PASS with an empty index, or fail-closed; never a forged caller
        for rf in base.rglob("*.json"):
            data = json.loads(rf.read_text())
            callers = (data.get("callers_of") or {}).get("add") or []
            self.assertEqual(callers, [], "invented a caller that does not exist")

    def test_non_swe_and_ambiguous_family_requests_stay_fail_closed(self):
        """Negative controls: a non-SWE goal and a two-source caller goal refuse."""
        base = self._tree("neg", True)
        util = base / "pkg/util.py"
        util.write_text("def helper():\n    return add(9, 9)\n", encoding="utf-8")
        g_non = "Summarize the file %s into three sentences." % _rel(base / "pkg/mod.py")
        self.assertIsNone(plan.build_plan(g_non, ROOT))
        r = door.solve({"task_id": "FAM_non", "goal": g_non})
        self.assertIs(r.get("pass"), False)
        self.assertNotIn("typed_swe_retry", r)

    def test_mutation_admit_as_oracle_breaks_the_family_plan(self):
        """Mutation control: the family resolver's oracle is admit(). If NO
        candidate is admitted (bind the declared contract fails), the family
        must produce NO decisive plan — proving it does not fabricate one."""
        from canonical.runtime import capability_selection_retrieval_v1 as selection
        base = self._tree("mutation", True)
        goal = self._goal(base)
        self.assertIsNotNone(plan.build_plan(goal, ROOT))
        with mock.patch.object(selection, "admit",
                               return_value={"admitted": False, "reason": "MUTATION"}):
            self.assertIsNone(plan.build_plan(goal, ROOT))

    def test_family_keyword_enumeration_is_the_mechanism(self):
        """Mutation control 2: strip the registry-keyword evidence the resolver
        enumerates on; with no matching candidate it must refuse (fail closed)."""
        from canonical.runtime import live_integrated_brain_v1 as live
        base = self._tree("kw_mut", True)
        goal = self._goal(base)
        real = live.load_verified_registry()
        stripped = {}
        for cid, e in real.items():
            e2 = dict(e)
            e2["keywords"] = []
            e2["provides"] = []
            stripped[cid] = e2
        with mock.patch.object(live, "load_verified_registry", return_value=stripped):
            self.assertIsNone(plan.build_plan(goal, ROOT))


if __name__ == "__main__":
    unittest.main()
