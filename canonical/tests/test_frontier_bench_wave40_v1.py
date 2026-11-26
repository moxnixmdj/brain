"""Wave 40 verification suite: `FRONTIER_BENCH_V1` — the held-out, oracle-judged benchmark.

Pure stdlib `unittest.TestCase` (runs under `python3 -m unittest` and `pytest`).

The bench exists to answer one question — *can the creature still do, on instances it has
never seen, the six things it claims?* — and to be impossible to satisfy by claiming. These
tests are the bench's own acceptance tests, so they are mostly about the instrument:

  0. instances are generated from a seed (no stored answer key, no fixture reuse)
  1. the oracle is a second implementation, and it fails closed on uninterpretable programs
  2. an honest kernel scores full marks on instances nobody wrote by hand
  3. a liar that always reports success scores zero, and its claims are counted separately
  4. a stub that always refuses does not pass the classes that require action
  5. an exception in the system under test is an ERROR, never a pass
  6. an exception in the oracle is an ERROR too — a broken judge passes nothing
  7. an empty benchmark is not a perfect score
  8. the transfer oracle refutes a plan that misses the goal, and flags the false claim
  9. the repair oracle runs the repository's own tests instead of believing the engine
 10. CLI exit codes and the scorecard document
 11. calibration: honest / liar / stub separate, so the instrument is trustworthy
 12. the bench is reachable from `UnifiedModel` and from the capability federation
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import random
import tempfile
import unittest

from canonical.evaluation import frontier_bench_v1 as bench
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.unified_hidden_capability_federation_v1 import run_federated_engine

CATEGORIES = bench.CATEGORIES


class _RaisingSut(bench.Sut):
    """Every call fails: the bench must record ERROR, never PASS."""

    def __init__(self) -> None:
        def _kernel() -> object:
            raise RuntimeError("BOOM__ENGINE_IS_DEAD")

        def _synth(*_: object, **__: object) -> object:
            raise RuntimeError("BOOM__SYNTHESISER_IS_DEAD")

        super().__init__(kernel=_kernel, synth=_synth)


class _ClaimOnlyRepairSut(bench.Sut):
    """Repairs nothing and says it repaired everything."""

    def __init__(self) -> None:
        class _Kernel:
            class swe_kernel:  # noqa: N801 - mirrors the kernel's attribute layout
                @staticmethod
                def repair_repository(*_: object, **__: object) -> dict[str, object]:
                    return {"pass": True, "status": "PASS__SIBLING_CLOSED_MULTIFILE", "applied_files": []}

        super().__init__(kernel=lambda: _Kernel(), synth=lambda *a, **k: {"pass": False})


class TestFrontierBenchWave40V1(unittest.TestCase):
    def test_00_instances_are_generated_from_a_seed_not_read_from_a_key(self) -> None:
        a = bench.generate_instances(seed=4242, per_category=1)
        b = bench.generate_instances(seed=4242, per_category=1)
        c = bench.generate_instances(seed=4243, per_category=1)
        self.assertEqual([i.instance_id for i in a], [i.instance_id for i in b])
        self.assertEqual(bench.instance_digest(a), bench.instance_digest(b))
        # A different seed is a different instance set: the content, not just the labels, moves.
        self.assertNotEqual([i.notes for i in a], [i.notes for i in c])
        self.assertNotEqual(bench.instance_digest(a), bench.instance_digest(c))
        # Instances carry behaviour (callables), never a stored expected answer.
        for inst in a:
            self.assertTrue(callable(inst.run))
            self.assertTrue(callable(inst.judge))
            self.assertEqual({k for k in vars(inst)}, {"instance_id", "category", "run", "judge", "cleanup", "notes"})

    def test_01_the_oracle_is_a_second_implementation_and_fails_closed(self) -> None:
        # Semantics of the bench's program language, written independently of the synthesiser.
        self.assertEqual(bench.eval_program("affine(3*x + 1)", 10), 31)
        self.assertEqual(bench.eval_program("affine(-2*x + 5)", 3), -1)
        self.assertEqual(bench.eval_program("shift(x + 7)", 1), 8)
        self.assertEqual(bench.eval_program("scale(4*x)", 3), 12)
        self.assertEqual(bench.eval_program("mod(x % 5)", 17), 2)
        self.assertEqual(bench.eval_program("acronym_upper(' ')", "Ada Lovelace"), "AL")
        self.assertEqual(bench.eval_program("extract_between('<', '>')", "id:<bob_42>@org"), "bob_42")
        # An undefined program is not a pass: it raises, and the judge records a failure.
        with self.assertRaises(ValueError):
            bench.eval_program("quantum_entangle(x)", 1)
        self.assertIs(bench.eval_program("extract_between('<', '>')", "no delimiters here"), bench._UNDEFINED)

    def test_02_an_honest_kernel_scores_full_marks_on_unseen_instances(self) -> None:
        scorecard = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=2)
        self.assertEqual(scorecard["instances"], 2 * len(CATEGORIES))
        self.assertEqual(scorecard["errors"], 0)
        self.assertEqual(scorecard["passed"], scorecard["instances"])
        self.assertEqual(scorecard["pass_rate"], 1.0)
        self.assertEqual(scorecard["verdict"], "BENCH_COMPLETE__ALL_INSTANCES_PASS")
        self.assertEqual(scorecard["false_success_claims"], 0)
        self.assertFalse(scorecard["scored_against_engine_claim"])
        self.assertFalse(scorecard["stored_answers_used"])
        self.assertEqual(scorecard["spend_usd"], 0.0)
        self.assertEqual(set(scorecard["by_category"]), set(CATEGORIES))

    def test_03_a_liar_that_always_claims_success_scores_zero(self) -> None:
        scorecard = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=2, sut=bench._LiarSut())
        self.assertEqual(scorecard["passed"], 0)
        self.assertEqual(scorecard["pass_rate"], 0.0)
        self.assertEqual(scorecard["errors"], 0)  # it lies fluently, it does not crash
        self.assertGreater(scorecard["false_success_claims"], 0)
        self.assertEqual(bench.exit_code_for(scorecard), 1)

    def test_04_a_refusal_stub_does_not_pass_the_classes_that_require_action(self) -> None:
        honest = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=2)
        stub = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=2, sut=bench._RefuseEverythingSut())
        self.assertLess(stub["pass_rate"], honest["pass_rate"])
        for category in ("WITNESS_INVERSION_GENERALIZATION", "COMPUTER_USE_GROUNDING",
                         "MULTIFILE_REPAIR", "CROSS_LANGUAGE_RULE_TRANSFER"):
            self.assertEqual(stub["by_category"][category]["passed"], 0, category)

    def test_05_an_engine_exception_is_an_error_not_a_pass(self) -> None:
        scorecard = bench.run_bench(seed=bench.DEFAULT_SEED, per_category=1, sut=_RaisingSut())
        self.assertEqual(scorecard["passed"], 0)
        self.assertEqual(scorecard["errors"], scorecard["instances"])
        self.assertTrue(all(r["stage"] == "SUT" for r in scorecard["records"]))
        self.assertIn("BOOM__ENGINE_IS_DEAD", scorecard["records"][0]["reason"])
        self.assertEqual(scorecard["verdict"], "BENCH_INCOMPLETE__ORACLE_OR_ENGINE_ERROR")
        self.assertEqual(bench.exit_code_for(scorecard), 1)

    def test_06_a_broken_oracle_passes_nothing(self) -> None:
        def _judge(_result: object) -> object:
            raise ZeroDivisionError("ORACLE_BROKEN")

        instances = [
            bench.BenchInstance(
                instance_id="BROKEN#00",
                category="TRANSFER_UNDER_ISOMORPHISM",
                run=lambda: {"pass": True},
                judge=_judge,
            )
        ]
        scorecard = bench.run_bench(instances=instances)
        self.assertEqual(scorecard["passed"], 0)
        self.assertEqual(scorecard["errors"], 1)
        self.assertEqual(scorecard["records"][0]["stage"], "ORACLE")
        self.assertIn("ORACLE_BROKEN", scorecard["records"][0]["reason"])

    def test_07_an_empty_benchmark_is_not_a_perfect_score(self) -> None:
        with self.assertRaises(ValueError):
            bench.generate_instances(seed=1, per_category=0)
        with self.assertRaises(ValueError):
            bench.generate_instances(seed=1, per_category=1, categories=["NOT_A_CATEGORY"])
        empty = bench.run_bench(instances=[])
        self.assertEqual(empty["instances"], 0)
        self.assertEqual(empty["pass_rate"], 0.0)
        self.assertEqual(empty["verdict"], "BENCH_NO_INSTANCES")
        self.assertEqual(bench.exit_code_for(empty), 2)

    def test_08_the_transfer_oracle_refutes_a_plan_that_misses_the_goal(self) -> None:
        instance = bench._build_transfer(random.Random("probe"), 0)
        honest = instance.run()
        wrong = dict(honest)
        transfer = dict(honest["moore_isomorphism_transfer"])
        transfer["mapped_plan"] = ["definitely_not_an_action"]
        wrong["moore_isomorphism_transfer"] = transfer
        verdict = instance.judge(wrong)
        self.assertFalse(verdict.ok)
        self.assertEqual(verdict.reason, "PLAN_NAMES_ABSENT_ACTION")
        self.assertTrue(verdict.sut_claimed)

        # Goal-missing but well-named: refuted by simulation, not by the engine's own report.
        short = dict(honest)
        transfer = dict(honest["moore_isomorphism_transfer"])
        transfer["mapped_plan"] = []
        short["moore_isomorphism_transfer"] = transfer
        missed = instance.judge(short)
        if instance.notes.endswith("goal_reachable=False") or "goal_reachable=False" in instance.notes:
            self.assertTrue(missed.ok)  # refusing is right when no plan exists
        else:
            self.assertFalse(missed.ok)
            self.assertEqual(missed.reason, "PLAN_MISSES_GOAL")

    def test_09_the_repair_oracle_runs_the_repositorys_own_tests(self) -> None:
        instance = bench._build_multifile_repair(random.Random("probe"), 0)
        scorecard = bench.run_bench(instances=[instance], sut=_ClaimOnlyRepairSut())
        record = scorecard["records"][0]
        self.assertEqual(record["status"], "FAIL")
        self.assertEqual(record["reason"], "REPO_TESTS_OR_SIBLINGS_NOT_CLOSED")
        self.assertTrue(record["sut_claimed"])
        self.assertEqual(scorecard["false_success_claims"], 1)
        self.assertEqual(scorecard["passed"], 0)

    def test_10_cli_writes_a_scorecard_and_uses_honest_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "scorecard.json"
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = bench.main(["--per-category", "1", "--seed", "20261126", "--json", str(target), "--quiet"])
            self.assertIn("verdict:", stream.getvalue())
            self.assertEqual(code, 0)
            self.assertTrue(target.exists())
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc["schema"], bench.SCORECARD_SCHEMA)
            self.assertEqual(doc["instances"], len(CATEGORIES))
            self.assertIsInstance(doc["pass_rate"], float)
            self.assertEqual(doc["false_success_claims"], 0)
            self.assertIn("verdict", doc)
            self.assertIn("by_category", doc)
            self.assertEqual(len(doc["records"]), doc["instances"])
            table = bench.format_table(doc)
            self.assertIn("TOTAL", table)
            self.assertIn(doc["verdict"], table)

    def test_11_calibration_separates_honest_liar_and_stub(self) -> None:
        check = bench.bench_self_check(seed=20261126, per_category=2)
        self.assertEqual(check["honest_pass_rate"], 1.0)
        self.assertEqual(check["liar_pass_rate"], 0.0)
        self.assertEqual(check["discrimination"], 1.0)
        self.assertTrue(check["instrument_trustworthy"])
        self.assertGreater(check["liar_false_success_claims"], 0)
        self.assertLess(check["refusal_stub_pass_rate"], check["honest_pass_rate"])

    def test_12_the_bench_is_reachable_from_the_model_and_the_federation(self) -> None:
        model = open_model()
        scorecard = model.frontier_bench(seed=20261126, per_category=1)
        self.assertEqual(scorecard["instances"], len(CATEGORIES))
        self.assertEqual(scorecard["passed"], scorecard["instances"])
        self.assertEqual(scorecard["pass_rate"], 1.0)

        fed = run_federated_engine("LEAPFROG_W40_FRONTIER_BENCH_HARNESS", {"per_category": 1})
        self.assertTrue(fed["pass"])
        self.assertIn("BENCH_COMPLETE", str(fed["status"]))
        self.assertEqual(fed["model_calls"], 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
