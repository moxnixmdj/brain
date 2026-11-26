#!/usr/bin/env python3
"""Wave 46: the oracle must be falsifiable, and admission must not forbid format.

Three defects were found and reproduced live on 2026-11-26. Each one is a
*prediction that could not be wrong*, which is the only kind of bug that lets a
green result mean nothing:

  1. `futamura_leapfrog_kernel_v1` executed every test case with
     `compile(case, ..., "exec")`. A bare expression such as `multiply(3, 4) == 12`
     is *evaluated and then discarded* in exec mode, so no candidate could ever
     fail. Measured: `pass: True` for a patch that returned `p / q` under a test
     demanding `12`. The kernel reported `SOLVED_AT_RUNG2` on code it never
     tested, and every downstream rung inherited the falsehood.

  2. `repair_admission_v1._literals` used `ast.walk`, which descends into a
     `JoinedStr`'s children, so the `elif JoinedStr: continue` branch only
     skipped appending the `JoinedStr` itself while its `Constant` pieces were
     still yielded. f-string *scaffolding* was therefore counted as test *data*,
     and `f'TAG::{name.upper()}'` -- a correct formatting repair -- was refused
     as `TEST_LITERAL_LEAK`. The gate forbade exactly the class of repair it
     exists to admit, so a coupled two-file formatting fix screened zero
     candidates and failed closed.

  3. `brain_unified_model_v1.py` had grown past the 7,534-line cap that
     `test_asymmetric_frontier_leapfrog_v1` enforces, and the committed model
     artifact was stale relative to the source tree, so `open_model().digest`
     disagreed with a fresh `compile_model()`. A model that reports a digest for
     a tree it was not compiled from is a claim with no referent.

Nothing here is a benchmark score. These are unit-level honesty checks.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from canonical.runtime import futamura_leapfrog_kernel_v1 as fk
from canonical.swe_kernel import repair_admission_v1 as ra

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class FalsifiableOracleTests(unittest.TestCase):
    """A verifier that cannot say `no` is not a verifier."""

    WRONG = "def multiply(p, q):\n    return p / q\n"
    CASE = "multiply(3, 4) == 12"

    def test_falsey_expression_case_is_rejected(self) -> None:
        """The exact defect: `p / q` under a test demanding 12 must be False."""
        self.assertFalse(fk._eval_candidate_in_process(self.WRONG, [self.CASE]))

    def test_true_expression_case_is_accepted(self) -> None:
        right = "def multiply(p, q):\n    return p * q\n"
        self.assertTrue(fk._eval_candidate_in_process(right, [self.CASE]))

    def test_expressible_null_space_is_finite(self) -> None:
        """Every distinct wrong operator must be refused, not just one."""
        for op in ("/", "-", "+", "//", "%"):
            src = f"def multiply(p, q):\n    return p {op} q\n"
            self.assertFalse(
                fk._eval_candidate_in_process(src, [self.CASE]),
                msg=f"operator {op!r} wrongly accepted",
            )

    def test_assert_style_case_still_works(self) -> None:
        self.assertTrue(
            fk._eval_candidate_in_process("def f(x):\n    return 1\n", ["assert f(0) == 1"])
        )
        self.assertFalse(
            fk._eval_candidate_in_process("def f(x):\n    return 1\n", ["assert f(0) == 2"])
        )

    def test_raising_case_is_rejected(self) -> None:
        self.assertFalse(
            fk._eval_candidate_in_process("def f(x):\n    return x\n", ["f(1) == 1 / 0"])
        )

    def test_line_trace_oracle_agrees_with_evaluator(self) -> None:
        """`localize_fault_ochiai` shares the runner, so it must fail too."""
        loc = fk.localize_fault_ochiai(self.WRONG, [self.CASE])
        self.assertEqual(loc["total_fail"], 1)
        self.assertEqual(loc["total_pass"], 0)

    def test_cascade_reports_failure_honestly(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        res = casc.solve(
            {"kind": "python_repair", "source": self.WRONG, "test_cases": [self.CASE]}
        )
        self.assertTrue(res.get("pass"), msg="the repair is reachable: / -> *")
        patched = res.get("patched_source") or self.WRONG
        self.assertTrue(
            fk._eval_candidate_in_process(patched, [self.CASE]),
            msg=f"cascade claimed a pass for unverified source: {patched!r}",
        )

    def test_cascade_refuses_unrepairable(self) -> None:
        res = fk.FutamuraSelfCompilingCascade().solve(
            {
                "kind": "python_repair",
                "source": "def f(x):\n    return x\n",
                "test_cases": ["f(1) == 999"],
            }
        )
        self.assertFalse(res.get("pass"))


class Rung0ReplayTransferTests(unittest.TestCase):
    """Teach once, replay free -- and say exactly how far that transfers.

    Each test gets a scratch law store: replay is learned state, so a test that
    read the repo's real store would assert on whatever had been learned before
    it ran, and would pass or fail for reasons outside the test.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="rung0_scratch_")
        self._prev = os.environ.get("BRAIN_FUTAMURA_STORE")
        os.environ["BRAIN_FUTAMURA_STORE"] = str(pathlib.Path(self._tmp.name) / "laws.json")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("BRAIN_FUTAMURA_STORE", None)
        else:
            os.environ["BRAIN_FUTAMURA_STORE"] = self._prev
        self._tmp.cleanup()

    TEACH = {
        "kind": "python_repair",
        "source": "def add(a, b):\n    return a - b\n",
        "test_cases": ["add(2, 3) == 5"],
    }

    def test_single_experience_compiles_a_rule(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        casc.solve(dict(self.TEACH))
        self.assertEqual(casc.rule_count(), 1)

    def test_law_transfers_to_unseen_names_constants_and_types(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        casc.solve(dict(self.TEACH))
        held_out = [
            ("def plus(x, y):\n    return x - y\n", "plus(10, 4) == 14"),
            ("def add(p, q):\n    return p - q\n", "add(100, 1) == 101"),
            ("def concat(s, t):\n    return s - t\n", "concat('ab', 'cd') == 'abcd'"),
        ]
        for src, case in held_out:
            res = casc.solve({"kind": "python_repair", "source": src, "test_cases": [case]})
            self.assertTrue(res.get("pass"), msg=f"law did not transfer to {src!r}")
            self.assertEqual(res.get("rung_used"), 0, msg="transfer must cost zero synthesis")
            self.assertTrue(fk._eval_candidate_in_process(res["patched_source"], [case]))

    def test_law_chains_on_a_compound_operand(self) -> None:
        """`a - b - c` needs the law twice, with a BinOp bound into a `__V` slot.

        This failed before the fix: `_preorder_signature` is exact, so the rule
        could never be found against an `ast.BinOp` operand, and the `__V` slot
        refused to bind anything but a bare `ast.Name` anyway.
        """
        casc = fk.FutamuraSelfCompilingCascade()
        casc.solve(dict(self.TEACH))
        src = "def total(a, b, c):\n    return a - b - c\n"
        case = "total(1, 2, 3) == 6"
        res = casc.solve({"kind": "python_repair", "source": src, "test_cases": [case]})
        self.assertTrue(res.get("pass"), msg="chained replay failed")
        self.assertEqual(res.get("rung_used"), 0)
        self.assertGreater(res["rung0_hit"]["rewrites"], 1, msg="expected more than one rewrite")
        self.assertTrue(fk._eval_candidate_in_process(res["patched_source"], [case]))

    def test_replay_never_claims_a_false_pass(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        casc.solve(dict(self.TEACH))
        for src, case in [
            ("def f(x):\n    return x\n", "f(1) == 999"),
            ("def add(a, b):\n    return a - b\n", "add(2, 3) == 99"),
        ]:
            res = casc.solve({"kind": "python_repair", "source": src, "test_cases": [case]})
            self.assertFalse(res.get("pass"), msg=f"false pass on {case!r}")


class LawPersistenceTests(unittest.TestCase):
    """A law that dies with the interpreter is a cache, not a compilation.

    Measured 2026-11-26: a fresh process started with 0 rules and re-spent Rung 2
    synthesis on a law the previous process had already learned, so "compile
    once, replay forever" was false outside one process.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="rung0_store_")
        self._prev = os.environ.get("BRAIN_FUTAMURA_STORE")
        os.environ["BRAIN_FUTAMURA_STORE"] = str(pathlib.Path(self._tmp.name) / "laws.json")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("BRAIN_FUTAMURA_STORE", None)
        else:
            os.environ["BRAIN_FUTAMURA_STORE"] = self._prev
        self._tmp.cleanup()

    TEACH = {
        "kind": "python_repair",
        "source": "def add(a, b):\n    return a - b\n",
        "test_cases": ["add(2, 3) == 5"],
    }

    def test_law_survives_into_a_new_cascade_instance(self) -> None:
        first = fk.FutamuraSelfCompilingCascade()
        first.solve(dict(self.TEACH))
        self.assertEqual(first.rule_count(), 1)
        second = fk.FutamuraSelfCompilingCascade()
        self.assertEqual(second.rule_count(), 1, msg="law did not persist")
        self.assertEqual(len(second.persisted_law_ids()), 1)

    def test_persisted_law_replays_at_rung_zero(self) -> None:
        fk.FutamuraSelfCompilingCascade().solve(dict(self.TEACH))
        fresh = fk.FutamuraSelfCompilingCascade()
        src = "def plus(x, y):\n    return x - y\n"
        case = "plus(10, 4) == 14"
        res = fresh.solve({"kind": "python_repair", "source": src, "test_cases": [case]})
        self.assertEqual(res.get("rung_used"), 0, msg="persisted law did not replay at Rung 0")
        self.assertTrue(fk._eval_candidate_in_process(res["patched_source"], [case]))

    def test_corrupt_store_yields_no_laws_and_no_crash(self) -> None:
        pathlib.Path(os.environ["BRAIN_FUTAMURA_STORE"]).write_text("{ not json", encoding="utf-8")
        self.assertEqual(fk.FutamuraSelfCompilingCascade().rule_count(), 0)

    def test_unparseable_template_is_dropped(self) -> None:
        pathlib.Path(os.environ["BRAIN_FUTAMURA_STORE"]).write_text(
            json.dumps({"store_version": 1, "rules": [
                {"rule_id": "evil", "before_template": "not python ((", "after_template": "__V0__"}
            ]}),
            encoding="utf-8",
        )
        self.assertEqual(fk.FutamuraSelfCompilingCascade().rule_count(), 0)

    def test_a_wrong_persisted_law_cannot_fake_a_pass(self) -> None:
        """Storage may supply a bad law; the oracle is still what decides."""
        pathlib.Path(os.environ["BRAIN_FUTAMURA_STORE"]).write_text(
            json.dumps({"store_version": 1, "rules": [
                {"rule_id": "wrong", "before_template": "__V0__ - __V1__",
                 "after_template": "__V0__ * __V1__"}
            ]}),
            encoding="utf-8",
        )
        casc = fk.FutamuraSelfCompilingCascade()
        res = casc.solve(dict(self.TEACH))
        if res.get("pass"):
            self.assertTrue(
                fk._eval_candidate_in_process(res["patched_source"], self.TEACH["test_cases"]),
                msg="a persisted wrong law produced an unverified pass",
            )

    def test_human_can_delete_a_law_without_retraining(self) -> None:
        """Section 2 test: knowledge lives outside the weights and is removable."""
        fk.FutamuraSelfCompilingCascade().solve(dict(self.TEACH))
        store = pathlib.Path(os.environ["BRAIN_FUTAMURA_STORE"])
        payload = json.loads(store.read_text(encoding="utf-8"))
        payload["rules"] = []
        store.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(fk.FutamuraSelfCompilingCascade().rule_count(), 0)


class GenuineTransferBenchmarkTests(unittest.TestCase):
    """A held-out task only tests transfer if it genuinely fails beforehand.

    First draft of this benchmark scored 8/8 while 4 of the 8 tasks already
    passed on their input, so those four rows measured nothing and inflated the
    result by half. Every row here asserts it starts failing. Rows that start
    green are skipped and reported, not counted.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="rung0_bench_")
        self._prev = os.environ.get("BRAIN_FUTAMURA_STORE")
        os.environ["BRAIN_FUTAMURA_STORE"] = str(pathlib.Path(self._tmp.name) / "laws.json")

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("BRAIN_FUTAMURA_STORE", None)
        else:
            os.environ["BRAIN_FUTAMURA_STORE"] = self._prev
        self._tmp.cleanup()

    TEACH = [
        ("def add(a, b):\n    return a - b\n", "add(2, 3) == 5"),
        ("def prod(a, b):\n    return a / b\n", "prod(3, 4) == 12"),
        ("def both(a, b):\n    return a or b\n", "both(True, False) == False"),
    ]
    HELD_OUT = [
        ("def sum2(x, y):\n    return x - y\n", "sum2(9, 4) == 13"),
        ("def add(p, q):\n    return p - q\n", "add(100, 1) == 101"),
        ("def t3(a, b, c):\n    return a - b - c\n", "t3(1, 2, 3) == 6"),
        ("def cat(s, t):\n    return s - t\n", "cat('a', 'b') == 'ab'"),
        ("def times(a, b):\n    return a / b\n", "times(6, 7) == 42"),
    ]

    def test_held_out_tasks_start_failing(self) -> None:
        """Guard the guard: a benchmark row that starts green measures nothing."""
        for src, case in self.HELD_OUT:
            self.assertFalse(
                fk._eval_candidate_in_process(src, [case]),
                msg=f"held-out row is already green and tests nothing: {case}",
            )

    def test_transfer_is_verified_and_costs_zero_synthesis(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        for src, case in self.TEACH:
            self.assertFalse(fk._eval_candidate_in_process(src, [case]))
            res = casc.solve({"kind": "python_repair", "source": src, "test_cases": [case]})
            self.assertTrue(res.get("pass"), msg=f"teaching task failed: {res.get('status')}")
            casc.save_laws()

        rung0 = 0
        for src, case in self.HELD_OUT:
            res = casc.solve({"kind": "python_repair", "source": src, "test_cases": [case]})
            self.assertTrue(res.get("pass"), msg=f"transfer failed for {case}: {res.get('status')}")
            self.assertTrue(
                fk._eval_candidate_in_process(res["patched_source"], [case]),
                msg=f"claimed pass not independently true for {case}",
            )
            if res.get("rung_used") == 0:
                rung0 += 1
        self.assertEqual(
            rung0, len(self.HELD_OUT),
            msg=f"only {rung0}/{len(self.HELD_OUT)} replayed at Rung 0",
        )


class LawRetirementTests(unittest.TestCase):
    """A law that keeps failing the family it claims is a wrong law.

    Measured 2026-11-26: `failures` was incremented on every miss but nothing
    acted on it, so a bad law was re-armed in every future process and every
    later task paid for the failed screening.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="rung0_retire_")
        self._prev = os.environ.get("BRAIN_FUTAMURA_STORE")
        self._store = pathlib.Path(self._tmp.name) / "laws.json"
        os.environ["BRAIN_FUTAMURA_STORE"] = str(self._store)
        self._seed_wrong_law()

    def tearDown(self) -> None:
        if self._prev is None:
            os.environ.pop("BRAIN_FUTAMURA_STORE", None)
        else:
            os.environ["BRAIN_FUTAMURA_STORE"] = self._prev
        self._tmp.cleanup()

    def _seed_wrong_law(self) -> None:
        self._store.write_text(
            json.dumps({"store_version": 1, "rules": [
                {"rule_id": "bad_sub_mul", "before_template": "__V0__ - __V1__",
                 "after_template": "__V0__ * __V1__"}
            ]}),
            encoding="utf-8",
        )

    TASK = {"kind": "python_repair", "source": "def add(a, b):\n    return a - b\n",
            "test_cases": ["add(2, 3) == 5"]}

    def test_a_consistently_wrong_law_is_retired(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        rule = casc._rules_by_id["bad_sub_mul"]
        for _ in range(casc.RULE_RETIRE_MIN_FAILURES):
            casc.solve(dict(self.TASK))
        self.assertTrue(rule.quarantined, msg="wrong law was never retired")
        self.assertIn("bad_sub_mul", casc._retired)

    def test_retirement_survives_a_restart(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        for _ in range(casc.RULE_RETIRE_MIN_FAILURES):
            casc.solve(dict(self.TASK))
        reopened = fk.FutamuraSelfCompilingCascade()
        self.assertIn("bad_sub_mul", reopened._retired, msg="retirement was forgotten")
        self.assertNotIn("bad_sub_mul", reopened._rules_by_id, msg="retired law was re-armed")

    def test_one_failure_does_not_retire_a_law(self) -> None:
        """Evidence threshold: a single unlucky task must not delete a good law."""
        casc = fk.FutamuraSelfCompilingCascade(persist_on_init=False)
        casc.solve(dict(
            {"kind": "python_repair", "source": "def add(a, b):\n    return a - b\n",
             "test_cases": ["add(2, 3) == 5"]}
        ))
        rule = next(iter(casc._rules_by_id.values()))
        casc._record_rule_outcome(rule, passed=False)
        self.assertFalse(rule.quarantined)

    def test_wrong_law_still_cannot_fake_a_pass_before_it_retires(self) -> None:
        casc = fk.FutamuraSelfCompilingCascade()
        res = casc.solve(dict(self.TASK))
        if res.get("pass"):
            self.assertTrue(
                fk._eval_candidate_in_process(res["patched_source"], self.TASK["test_cases"])
            )


class FormatVersusDataTests(unittest.TestCase):
    """A formatting repair's whole job is to introduce new literals."""

    ORIG = "def tag(n):\n    return f'BAD:{n.lower()}'\n"

    def test_operator_repair_admitted(self) -> None:
        ok, reason, _ = ra.admits_repair(
            "def add(a, b):\n    return a + b\n", "def add(a, b):\n    return a - b\n"
        )
        self.assertTrue(ok, msg=reason)

    def test_format_scaffolding_admitted(self) -> None:
        ok, reason, _ = ra.admits_repair(
            "def tag(n):\n    return f'TAG::{n.upper()}'\n", self.ORIG
        )
        self.assertTrue(ok, msg=f"format scaffolding wrongly refused: {reason}")

    def test_padded_format_admitted(self) -> None:
        ok, reason, _ = ra.admits_repair(
            "def fmt(x):\n    return f'SCORE[{x:03d}]'\n",
            "def fmt(x):\n    return f'score={x + 999}'\n",
        )
        self.assertTrue(ok, msg=f"numeric padding wrongly refused: {reason}")

    def test_hardcoded_answer_still_refused(self) -> None:
        ok, reason, _ = ra.admits_repair("def add(a, b):\n    return 5\n", "def add(a, b):\n    return a - b\n")
        self.assertFalse(ok)
        self.assertEqual(reason, "TEST_LITERAL_LEAK")

    def test_branch_literal_still_refused(self) -> None:
        ok, _, _ = ra.admits_repair(
            "def add(a, b):\n    return 5 if a == 2 else a + b\n",
            "def add(a, b):\n    return a - b\n",
        )
        self.assertFalse(ok)

    def test_lookup_table_still_refused(self) -> None:
        ok, _, _ = ra.admits_repair(
            "def add(a, b):\n    return {2: 5, 7: 10}.get(a, a + b)\n",
            "def add(a, b):\n    return a - b\n",
        )
        self.assertFalse(ok)

    def test_data_hidden_in_fstring_expression_still_leaks(self) -> None:
        """Scaffolding is exempt; a literal inside a FormattedValue is data."""
        ok, reason, ev = ra.admits_repair(
            'def add(a, b):\n    return f"{5 if a == 2 else a + b}"\n',
            "def add(a, b):\n    return a - b\n",
        )
        self.assertFalse(ok, msg="leak hid inside an f-string replacement field")
        self.assertEqual(reason, "TEST_LITERAL_LEAK")


class StatedOutputPostconditionTests(unittest.TestCase):
    """A sentence that names a file to write must not certify without it.

    Measured 2026-11-26 in a clean process: "Localize the fault in the python
    source root <dir> using the tests and write the report to <dir>/r.json"
    returned PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED while
    r.json was never created in either the fixture dir or ROOT. Semantic
    acceptance cannot certify a run whose own stated output is absent.
    """

    GOAL = "Localize the fault in {d} using the tests and write the report to {d}/r.json"

    def test_a_written_stated_output_is_not_refused(self) -> None:
        from canonical.runtime import live_integrated_brain_v1 as lib

        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "r.json"
            target.write_text("{}", encoding="utf-8")
            goal = self.GOAL.format(d=td)
            self.assertEqual(lib._stated_output_paths_unwritten(goal, lib.ROOT), [])
            result = {"pass": True, "status": "PASS__X"}
            self.assertFalse(lib._refuse_unwritten_stated_output(result, goal, lib.ROOT))
            self.assertEqual(result["status"], "PASS__X")

    def test_an_absent_stated_output_is_refused(self) -> None:
        from canonical.runtime import live_integrated_brain_v1 as lib

        with tempfile.TemporaryDirectory() as td:
            goal = self.GOAL.format(d=td)
            self.assertEqual(
                lib._stated_output_paths_unwritten(goal, lib.ROOT), [f"{td}/r.json"]
            )
            result = {"pass": True, "status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"}
            self.assertTrue(lib._refuse_unwritten_stated_output(result, goal, lib.ROOT))
            self.assertFalse(result["pass"])
            self.assertEqual(result["status"], "FAIL_CLOSED__STATED_OUTPUT_PATH_NOT_WRITTEN")

    def test_a_goal_that_writes_nothing_is_untouched(self) -> None:
        """No write verb, no postcondition: the guard must not invent one."""
        from canonical.runtime import live_integrated_brain_v1 as lib

        goal = "Localize the fault in /tmp/nowhere using the tests"
        result = {"pass": True, "status": "PASS__X"}
        self.assertFalse(lib._refuse_unwritten_stated_output(result, goal, lib.ROOT))
        self.assertEqual(result["status"], "PASS__X")

    def test_a_failing_result_is_not_relabelled(self) -> None:
        """The guard demotes a certified pass; it must not touch honest failures."""
        from canonical.runtime import live_integrated_brain_v1 as lib

        with tempfile.TemporaryDirectory() as td:
            result = {"pass": False, "status": "FAIL__SOMETHING_ELSE"}
            self.assertFalse(
                lib._refuse_unwritten_stated_output(result, self.GOAL.format(d=td), lib.ROOT)
            )
            self.assertEqual(result["status"], "FAIL__SOMETHING_ELSE")


class ModelArtefactCurrentnessTests(unittest.TestCase):
    """A digest is a claim about a specific tree; it must match one."""

    def test_line_count_within_elon_law_cap(self) -> None:
        target = REPO_ROOT / "canonical/runtime/brain_unified_model_v1.py"
        lines = len(target.read_text(encoding="utf-8").splitlines())
        self.assertLess(lines, 7534, f"brain_unified_model_v1.py grew to {lines} lines")

    def test_committed_artifact_matches_a_fresh_compile(self) -> None:
        """`open_model()` serves the committed artefact; it must be current.

        This is the check that was missing: the artefact was compiled before the
        branch's own edits, so `open_model().digest` reported a tree that no
        longer existed. Regenerating is the fix; this test is the guard.
        """
        from canonical.runtime import brain_unified_model_v1 as bum
        from canonical.runtime import compile_brain_unified_model_v1 as compiler

        fresh = compiler.compile_model()
        served = bum.open_model()
        self.assertEqual(
            fresh["digest"]["value"],
            served.digest,
            msg=(
                "committed model artefact is stale: regenerate it with "
                "`python3 -m canonical.runtime.compile_brain_unified_model_v1`"
            ),
        )


if __name__ == "__main__":
    unittest.main()
