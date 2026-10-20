#!/usr/bin/env python3
"""Hard, real acceptance tests for the living agent and the living core.

Nothing here is mocked.  Every shell skill runs real processes over real files
on disk, and every table task is checked against an oracle written independently
of the learner on held-out instances drawn from a different random stream than
the demonstration.  A test fails if the exact bytes differ.
"""
from __future__ import annotations

import json
import os
import random
import re
import statistics
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import living_agent_benchmark_v1 as benchmark  # noqa: E402
from canonical.runtime import living_discovery_v1 as discovery  # noqa: E402
from canonical.runtime import shell_synthesis_v1 as synthesis  # noqa: E402
from canonical.runtime.living_agent_v1 import (  # noqa: E402
    AgentError,
    Computer,
    LivingAgent,
    SCHEMA as AGENT_SCHEMA,
)
from canonical.runtime.living_core_v1 import (  # noqa: E402
    LivingCoreError,
    Memory,
    apply_program,
    call,
    eval_expr,
    eval_expr_interpreted,
    induce,
    lit,
    program_to_json,
)

HOLDOUT_CASES = 20


def shell_lines(text: str) -> list[str]:
    """Lines exactly as the shell sees them (split on newline only)."""
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def sorted_text(text: str) -> str:
    return "\n".join(sorted(shell_lines(text), key=lambda line: line.encode())) + "\n"


def _python_unique_word_count(path: Path) -> int:
    return len({word for word in path.read_text(encoding="utf-8").split()})


def _python_line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


class ShellComputerTests(unittest.TestCase):
    """Real POSIX execution, real confinement, real exit codes."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.computer = Computer(self.tmp.name)
        self.computer.write("data.txt", "beta alpha\nbeta gamma\n")

    def test_real_command_matches_independent_python_result(self) -> None:
        result = self.computer.run("wc -l < data.txt")
        self.assertTrue(result.ok, result.stderr)
        self.assertEqual(int(result.stdout.strip()), _python_line_count(Path(self.tmp.name) / "data.txt"))

    def test_absolute_and_escaping_paths_are_refused(self) -> None:
        for command in ("cat /etc/passwd", "cat ../../etc/passwd", "wc -l < /etc/hostname"):
            with self.subTest(command=command):
                with self.assertRaises(AgentError):
                    self.computer.run(command)

    def test_unadmitted_binary_is_refused_before_execution(self) -> None:
        for command in ("curl http://example.com", "rm -rf data.txt", "python3 -c 'print(1)'"):
            with self.subTest(command=command):
                with self.assertRaises(AgentError):
                    self.computer.run(command)
        self.assertTrue(self.computer.exists("data.txt"))

    def test_a_command_substitution_is_not_a_way_around_admission(self) -> None:
        # `$(...)` runs a program the admission check never saw, and a tab --
        # the one character a command cannot carry literally -- is the only
        # substitution allowed.  Both sides are checked against the real shell.
        for command in (
            "cat data.txt | sort -t $(date)",
            "cat data.txt | sort -t `date`",
            "cat data.txt | sort -t \"$(curl example.com)\"",
        ):
            with self.subTest(command=command):
                with self.assertRaises(AgentError) as raised:
                    self.computer.run(command)
                self.assertEqual(str(raised.exception), "COMMAND_SUBSTITUTION_REFUSED")
        self.computer.admit("sort", evidence={"summary": "", "usage": "", "argv": []})
        self.computer.write("t.tsv", "b\t2\na\t1\n")
        result = self.computer.run("cat t.tsv | sort -t \"$(printf '\\t')\" -k 2")
        self.assertTrue(result.ok, result.stderr)
        self.assertEqual(result.stdout, "a\t1\nb\t2\n")

    def test_control_characters_are_refused(self) -> None:
        with self.assertRaises(AgentError):
            self.computer.run("cat data.txt\ncat data.txt")

    def test_oversized_output_is_flagged_not_silently_cut(self) -> None:
        self.computer.write("big.txt", "x" * 4_000_001 + "\n")
        result = self.computer.run("cat big.txt")
        self.assertTrue(result.truncated)
        self.assertFalse(result.ok)

    def test_nonzero_exit_is_reported_with_stderr(self) -> None:
        result = self.computer.run("cat missing.txt")
        self.assertFalse(result.ok)
        self.assertNotEqual(result.code, 0)
        self.assertTrue(result.stderr.strip())


class ChunkingAndWordLearningTests(unittest.TestCase):
    """One demonstration -> a general skill; unknown goals fail closed."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = LivingAgent(self.root)
        self.agent.computer.write("demo.txt", "one\ntwo\nthree\n")
        self.agent.computer.write("held_out.txt", "alpha\nbeta\ngamma\ndelta\nepsilon\n")
        self.agent.computer.write("sorted.txt", "zeta\neta\ntheta\n")
        self.skill = self.agent.learn_shell_skill(
            "count the lines in a file",
            "wc -l < demo.txt",
            {"path": "demo.txt"},
            canary=({"canary.txt": "a\nb\nc\nd\n"}, "4"),
            postcondition=r"^[0-9]+$",
        )

    def test_demonstration_becomes_slot_template(self) -> None:
        self.assertEqual(self.skill.template, "wc -l < {path}")
        self.assertEqual(self.skill.slots, {"path": "demo.txt"})
        self.assertEqual(self.skill.version, 1)

    def test_skill_generalizes_to_unseen_files(self) -> None:
        for name in ("held_out.txt", "sorted.txt"):
            with self.subTest(name=name):
                outcome = self.agent.solve(f"how many lines are in '{name}'")
                self.assertEqual(outcome["status"], "PASS", outcome)
                self.assertEqual(
                    int(outcome["stdout"]), _python_line_count(self.root / name)
                )

    def test_unknown_goal_fails_closed_before_teaching(self) -> None:
        with self.assertRaises(AgentError) as raised:
            self.agent.solve("shred the archive")
        self.assertEqual(str(raised.exception), "GOAL_UNKNOWN_FAIL_CLOSED")

    def test_one_word_teaching_makes_a_new_verb_resolvable(self) -> None:
        taught = self.agent.teach_word("tally", "count the lines in a file")
        self.assertEqual(taught["skill_id"], self.skill.skill_id)
        outcome = self.agent.solve("tally the lines in 'held_out.txt'")
        self.assertEqual(outcome["status"], "PASS")
        self.assertEqual(int(outcome["stdout"]), 5)
        facts = [
            entry
            for entry in self.agent.memory.active()
            if entry.kind == "fact" and entry.payload.get("word") == "tally"
        ]
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].payload["skill_id"], self.skill.skill_id)

    def test_missing_path_argument_is_a_typed_failure(self) -> None:
        with self.assertRaises(AgentError) as raised:
            self.agent.solve("count the lines")
        self.assertEqual(str(raised.exception), "GOAL_PATH_BINDING_REQUIRED")

    def test_a_demonstration_without_a_variable_argument_is_rejected(self) -> None:
        with self.assertRaises(AgentError) as raised:
            self.agent.learn_shell_skill(
                "always print hello",
                "echo hello",
                {},
                canary=({"canary.txt": "x\n"}, "x"),
            )
        self.assertEqual(str(raised.exception), "DEMONSTRATION_HAS_NO_GENERALIZABLE_ARGUMENT")


class DriftRepairTests(unittest.TestCase):
    """A silent environment change is detected and repaired, not ignored."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = LivingAgent(self.root)
        self.agent.computer.write("demo.txt", "a\nb\nc\n")
        self.agent.computer.write("target.txt", "p\nq\n")
        self.skill = self.agent.learn_shell_skill(
            "count the lines in a file",
            "wc -l < demo.txt",
            {"path": "demo.txt"},
            canary=({"canary.txt": "a\nb\nc\n"}, "3"),
            postcondition=r"^[0-9]+$",
        )

    def _install_drifting_tool(self) -> None:
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        shim = bin_dir / "wc"
        shim.write_text('#!/bin/sh\n/usr/bin/wc "$@" | sed "s/$/ lines/"\n', encoding="utf-8")
        shim.chmod(0o755)
        self.agent.computer.bin_dir = bin_dir

    def test_drift_is_detected_and_repaired_preserving_slots(self) -> None:
        self.assertEqual(self.agent.solve("count the lines in 'target.txt'")["status"], "PASS")
        self._install_drifting_tool()
        outcome = self.agent.solve("count the lines in 'target.txt'")
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertTrue(outcome["repaired"])
        self.assertEqual(self.skill.version, 2)
        self.assertIn("{path}", self.skill.template)
        self.assertIn("lines", self.skill.repair_history[0]["observed_before"])
        # the adapted skill keeps working on a different file
        self.agent.computer.write("third.txt", "m\nn\no\np\n")
        again = self.agent.solve("count the lines in 'third.txt'")
        self.assertEqual(again["status"], "PASS")
        self.assertEqual(int(again["stdout"]), 4)

    def test_self_test_finds_a_broken_skill_and_repairs_it(self) -> None:
        self._install_drifting_tool()
        report = self.agent.self_test()
        self.assertEqual(len(report["skills"]), 1)
        self.assertTrue(report["skills"][0]["canary_ok"])
        self.assertTrue(report["skills"][0]["repaired"])

    def test_a_genuinely_absent_input_is_not_papered_over(self) -> None:
        outcome = self.agent.solve("count the lines in 'missing.txt'")
        self.assertEqual(outcome["status"], "FAIL_CLOSED")
        self.assertEqual(self.skill.version, 1)
        self.assertEqual(self.skill.template, "wc -l < {path}")


class IgnoranceTrackingTests(unittest.TestCase):
    """The creature keeps an explicit record of what it does not know."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agent = LivingAgent(Path(self.tmp.name))
        self.agent.computer.write("demo.txt", "a\nb\n")
        self.agent.learn_shell_skill(
            "count the lines in a file",
            "wc -l < demo.txt",
            {"path": "demo.txt"},
            canary=({"canary.txt": "a\nb\n"}, "2"),
            postcondition=r"^[0-9]+$",
        )

    def test_unknown_goal_is_recorded_and_exposed(self) -> None:
        with self.assertRaises(AgentError):
            self.agent.solve("summarize the quarterly revenue")
        self.assertEqual(self.agent.open_questions(), ["summarize the quarterly revenue"])

    def test_teaching_a_word_resolves_the_matching_impasse(self) -> None:
        with self.assertRaises(AgentError):
            self.agent.solve("summarize the quarterly revenue")
        self.agent.teach_word("summarize", "count the lines in a file")
        self.assertEqual(self.agent.open_questions(), [])

    def test_unrelated_impasse_stays_open(self) -> None:
        with self.assertRaises(AgentError):
            self.agent.solve("summarize the quarterly revenue")
        self.agent.computer.write("other.txt", "x\n")
        self.agent.learn_shell_skill(
            "reverse the lines of a file",
            "sort -r other.txt",
            {"path": "other.txt"},
            canary=({"canary_two.txt": "a\nb\n"}, "b\na"),
            postcondition=r"^\S",
        )
        self.assertEqual(self.agent.open_questions(), ["summarize the quarterly revenue"])


class ProbeBudgetTests(unittest.TestCase):
    """A stated query budget is a hard cap, not a suggestion."""

    def test_never_spends_more_queries_than_the_budget(self) -> None:
        oracle = benchmark.guarded_oracle("tax")
        demo = benchmark.covering_instance("tax", random.Random(4))
        result = induce(oracle, [(demo, oracle(demo))], seed=4, max_probes=9, validation_cases=6)
        self.assertLessEqual(result.probes, 9)
        if result.success:
            table = benchmark.generate_instance("tax", random.Random(101))
            produced = apply_program(result.program, table)
            want = oracle(table)
            self.assertEqual(produced.rows, want.rows)


class SelfDirectedPracticeTests(unittest.TestCase):
    """The creature chooses its own practice and learns its own boundary."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = LivingAgent(self.root)
        self.agent.computer.write("demo.txt", "l1\nl2\nl3\n")
        self.agent.computer.write("five.txt", "l1\nl2\nl3\nl4\nl5\n")
        self.skill = self.agent.learn_shell_skill(
            "print the nth line of a file",
            "sed -n '1p' demo.txt",
            {"n": "1", "path": "demo.txt"},
            canary=({"canary_two.txt": "c1\nc2\n"}, "c1"),
            postcondition=r"^\S",
        )

    def test_practice_discovers_the_exact_domain_boundary(self) -> None:
        def make_task(n: int) -> tuple[str, dict[str, str]]:
            return f"print the {n}th line of 'five.txt'", {"n": str(n), "path": "five.txt"}

        report = self.agent.practice(make_task, rounds=7)
        self.assertEqual(report["tested"], [1, 2, 3, 4, 5, 6, 7])
        outcomes = {row["n"]: row["outcome"]["status"] for row in report["log"]}
        self.assertEqual(
            outcomes,
            {1: "PASS", 2: "PASS", 3: "PASS", 4: "PASS", 5: "PASS", 6: "FAIL_CLOSED", 7: "FAIL_CLOSED"},
        )
        self.assertAlmostEqual(report["observed_success_rate"], 5 / 7, places=6)
        self.assertAlmostEqual(report["confidence"], 5 / 7, places=6)

    def test_practice_inputs_cover_contiguous_untested_regions(self) -> None:
        seen: list[int] = []

        def make_task(n: int) -> tuple[str, dict[str, str]]:
            seen.append(n)
            return f"print the {n}th line of 'five.txt'", {"n": str(n), "path": "five.txt"}

        self.agent.practice(make_task, rounds=5)
        self.assertEqual(sorted(seen), [1, 2, 3, 4, 5])


class MemoryTests(unittest.TestCase):
    """Salience is learned; consolidation shrinks bytes without losing skills."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agent = LivingAgent(Path(self.tmp.name))
        self.agent.computer.write("demo.txt", "a\nb\n")
        self.agent.computer.write("data.txt", "x\n")
        self.skill = self.agent.learn_shell_skill(
            "count the lines in a file",
            "wc -l < demo.txt",
            {"path": "demo.txt"},
            canary=({"canary.txt": "a\nb\n"}, "2"),
            postcondition=r"^[0-9]+$",
        )

    def test_retrieval_outcomes_change_the_salience_model(self) -> None:
        before = dict(self.agent.memory.model.weights)
        for _ in range(3):
            self.assertEqual(self.agent.solve("count the lines in 'data.txt'")["status"], "PASS")
        self.assertEqual(self.agent.memory.model.updates, 3)
        self.assertNotEqual(self.agent.memory.model.weights, before)
        self.assertEqual(len(self.agent.memory.retrieval_log), 3)
        self.assertTrue(all(row["success"] for row in self.agent.memory.retrieval_log))

    def test_consolidation_shrinks_repetition_and_keeps_the_skill(self) -> None:
        for _ in range(40):
            self.agent.solve("count the lines in 'data.txt'")
        before = self.agent.memory.payload_bytes()
        stats = self.agent.consolidate()
        after = self.agent.memory.payload_bytes()
        self.assertLess(after, before)
        self.assertGreaterEqual(stats["merged"], 20)
        self.assertLessEqual(after / before, 0.5)
        self.assertIn(self.skill.skill_id, self.agent.skills)
        ranked = self.agent.memory.retrieve("count lines", kind="skill", k=1)
        self.assertEqual(ranked[0][1].payload["skill_id"], self.skill.skill_id)
        retired = [entry for entry in self.agent.memory.entries.values() if entry.retired]
        self.assertTrue(retired)
        self.assertTrue(all("skill_id" in entry.payload for entry in retired))

    def test_snapshot_round_trip_preserves_skills_and_learned_salience(self) -> None:
        self.agent.solve("count the lines in 'data.txt'")
        self.agent.teach_word("tally", "count the lines in a file")
        payload = json.loads(json.dumps(self.agent.snapshot()))
        other = LivingAgent(Path(self.tmp.name))
        other.restore(payload)
        self.assertEqual(other.memory.model.weights, self.agent.memory.model.weights)
        self.assertEqual(other.memory.model.updates, self.agent.memory.model.updates)
        self.assertEqual(other.word_bindings, {"tally": self.skill.skill_id})
        self.assertEqual(other.solve("tally the lines in 'data.txt'")["status"], "PASS")
        with self.assertRaises(AgentError):
            other.restore({"schema": "WRONG"})


class TableInductionTests(unittest.TestCase):
    """Twelve black-box transforms, exact bytes, held-out from a fresh stream."""

    def test_every_family_generalizes_exactly_on_held_out_instances(self) -> None:
        durations = []
        for name in benchmark.FAMILIES:
            with self.subTest(family=name):
                demo_rng = random.Random(7)
                holdout_rng = random.Random(99)
                oracle = benchmark.guarded_oracle(name)
                demo = benchmark.covering_instance(name, demo_rng)
                expected = oracle(demo)
                self.assertIsNotNone(expected, "oracle rejected its own demonstration")
                started = time.perf_counter()
                result = induce(
                    oracle,
                    [(demo, expected)],
                    seed=7,
                    max_probes=24,
                    validation_cases=6,
                )
                elapsed = time.perf_counter() - started
                durations.append(elapsed)
                self.assertTrue(result.success, f"{name}: {result.failure_reason}")
                self.assertGreater(result.probes, 0)
                self.assertGreater(result.validation_cases, 0)
                self.assertEqual(result.model_dependency_count, 0)
                self.assertEqual(result.incremental_spend_usd, 0)
                passed = 0
                for _ in range(HOLDOUT_CASES):
                    table = benchmark.generate_instance(name, holdout_rng)
                    want = oracle(table)
                    got = apply_program(result.program, table)
                    if got.columns == want.columns and got.rows == want.rows:
                        passed += 1
                self.assertEqual(passed, HOLDOUT_CASES, f"{name} passed {passed}/{HOLDOUT_CASES}")
        self.assertLess(max(durations), 10.0)
        self.assertLess(sum(durations), 20.0)

    def test_induced_programs_are_deterministic(self) -> None:
        def run_once() -> str:
            oracle = benchmark.guarded_oracle("tax")
            demo = benchmark.covering_instance("tax", random.Random(3))
            result = induce(oracle, [(demo, oracle(demo))], seed=3, max_probes=24, validation_cases=6)
            self.assertTrue(result.success)
            return json.dumps(program_to_json(result.program), sort_keys=True)

        self.assertEqual(run_once(), run_once())

    def test_holdout_uses_a_stream_that_differs_from_the_demonstration(self) -> None:
        demo = benchmark.covering_instance("concat", random.Random(7))
        holdout = [benchmark.generate_instance("concat", random.Random(99)) for _ in range(20)]
        self.assertNotEqual(
            [row for row in demo.rows],
            [row for row in holdout[0].rows],
        )


class ExpressionCompilerTests(unittest.TestCase):
    """The compiled evaluator must mean exactly what the tree walk means.

    ``eval_expr`` is a closure compiler because induction evaluates the same
    expression millions of times.  Speed is only acceptable if the fast path is
    indistinguishable from the reference interpreter, so both are run side by
    side on every operator, including the error cases.
    """

    ROW = {
        "a": "3",
        "b": "2",
        "c": "  Mixed Case  ",
        "d": "2024-03-09",
        "e": "ann/lee",
        "f": "12.5%",
        "g": "-7",
        "h": "SKU-0042",
    }

    def _expressions(self):
        a = lambda: ("col", "a")
        b = lambda: ("col", "b")
        return [
            call("add", [a(), b()]),
            call("sub", [a(), b()]),
            call("mul", [a(), b()]),
            call("div", [a(), b()]),
            call("mod", [a(), b()]),
            call("min", [a(), b()]),
            call("max", [a(), b()]),
            call("neg", [a()]),
            call("abs", [("col", "g")]),
            call("round", [call("div", [a(), b()])], k=2),
            call("lower", [("col", "c")]),
            call("upper", [("col", "c")]),
            call("title", [("col", "c")]),
            call("strip", [("col", "c")]),
            call("len", [("col", "c")]),
            call("number", [("col", "f")]),
            call("year", [("col", "d")]),
            call("month", [("col", "d")]),
            call("day", [("col", "d")]),
            call("split", [("col", "e")], sep="/", idx=1),
            call("split", [("col", "e")], sep="/", idx=-1),
            call("before", [("col", "e")], sep="/"),
            call("after", [("col", "e")], sep="/"),
            call("strip_prefix", [("col", "h")], s="SKU-"),
            call("strip_suffix", [("col", "h")], s="42"),
            call("slice", [("col", "h")], start=4, end=9),
            call("concat", [("col", "e"), ("col", "h")], sep="|"),
            call("add", [call("mul", [a(), b()]), lit(1.5)]),
        ]

    def test_compiled_and_interpreted_agree_on_every_operator(self) -> None:
        for expr in self._expressions():
            with self.subTest(op=expr[0]):
                self.assertEqual(eval_expr(expr, self.ROW), eval_expr_interpreted(expr, self.ROW))

    def test_missing_cells_behave_the_same(self) -> None:
        empty: dict[str, str] = {}
        for expr in self._expressions():
            with self.subTest(op=expr[0]):
                try:
                    want = eval_expr_interpreted(expr, empty)
                except Exception as error:  # noqa: BLE001 - parity is the point
                    with self.assertRaises(type(error)):
                        eval_expr(expr, empty)
                else:
                    self.assertEqual(eval_expr(expr, empty), want)

    def test_error_cases_are_identical(self) -> None:
        cases = [
            call("div", [("col", "a"), lit(0)]),
            call("mod", [("col", "a"), lit(0)]),
            call("number", [("col", "c")]),
            call("split", [("col", "e")], sep="/", idx=5),
            call("before", [("col", "e")], sep="?"),
            call("after", [("col", "e")], sep="?"),
            call("strip_prefix", [("col", "e")], s="zzz"),
            call("strip_suffix", [("col", "e")], s="zzz"),
            ("unknown_op", (), ()),
        ]
        for expr in cases:
            with self.subTest(op=expr[0]):
                message = None
                try:
                    eval_expr_interpreted(expr, self.ROW)
                except Exception as error:  # noqa: BLE001
                    message = str(error)
                self.assertIsNotNone(message)
                with self.assertRaises(LivingCoreError):
                    eval_expr(expr, self.ROW)
                try:
                    eval_expr(expr, self.ROW)
                except Exception as error:  # noqa: BLE001
                    self.assertEqual(str(error), message)


class ActiveLearningDisciplineTests(unittest.TestCase):
    """How the learner spends questions, and what it refuses to claim.

    These are the failure modes that make a learner look right for the wrong
    reason: stopping after a fixed number of steps, never testing the value
    combination that separates two hypotheses, re-paying for an answer it
    already has, and claiming success on evidence it never gathered.
    """

    def test_a_family_needing_more_than_eight_rounds_is_still_learned(self) -> None:
        # Seed 8 of ``tax`` used to die at a fixed eight-round cap with a
        # correct hypothesis still in the version space.  A step budget is a
        # script; the stopping rule must be knowledge or a stated resource.
        oracle = benchmark.guarded_oracle("tax")
        demo = benchmark.covering_instance("tax", random.Random(8))
        result = induce(oracle, [(demo, oracle(demo))], seed=8, max_probes=24, validation_cases=6)
        self.assertTrue(result.success, result.failure_reason)
        self.assertGreater(result.rounds, 8)
        self.assertGreater(result.validation_cases, 0)
        holdout = random.Random(9008)
        for _ in range(HOLDOUT_CASES):
            table = benchmark.generate_instance("tax", holdout)
            want = oracle(table)
            got = apply_program(result.program, table)
            self.assertEqual(got.columns, want.columns)
            self.assertEqual(got.rows, want.rows)

    def test_the_separating_value_pair_is_actually_tested(self) -> None:
        # Seed 14 of ``unit_price`` has one value pair (qty=6, total=58) whose
        # ratio 9.67 sits between the true threshold 10 and the tempting 9.
        # Independent column sampling almost never visits that cell; a learner
        # that only samples concludes on 9 of the 42 surviving hypotheses.
        oracle = benchmark.guarded_oracle("unit_price")
        demo = benchmark.covering_instance("unit_price", random.Random(14))
        result = induce(oracle, [(demo, oracle(demo))], seed=14, max_probes=24, validation_cases=6)
        self.assertTrue(result.success, result.failure_reason)
        filter_step = result.program[0]
        self.assertEqual(filter_step["op"], "filter")
        self.assertEqual(str(filter_step["value"]), "10")
        holdout = random.Random(9014)
        for _ in range(HOLDOUT_CASES):
            table = benchmark.generate_instance("unit_price", holdout)
            want = oracle(table)
            got = apply_program(result.program, table)
            self.assertEqual(got.columns, want.columns)
            self.assertEqual(got.rows, want.rows)

    def test_no_question_is_answered_twice(self) -> None:
        asked: dict[str, int] = {}

        for name in benchmark.FAMILIES:
            oracle = benchmark.guarded_oracle(name)
            demo = benchmark.covering_instance(name, random.Random(8))

            def query(table, oracle=oracle):
                key = table.to_csv()
                asked[name + "\x00" + key] = asked.get(name + "\x00" + key, 0) + 1
                return oracle(table)

            induce(query, [(demo, oracle(demo))], seed=8, max_probes=24, validation_cases=6)

        repeated = {key: count for key, count in asked.items() if count > 1}
        self.assertEqual(repeated, {}, f"paid twice for {len(repeated)} question(s)")

    def test_a_mixed_identifier_sort_is_a_total_order(self) -> None:
        # An active-row report may legitimately mix numeric and text ids; the
        # oracle must order them deterministically instead of raising.
        oracle = benchmark.FAMILIES["active"]["oracle"]
        table = benchmark.Table(
            ["id", "name", "status"],
            [
                {"id": "x9", "name": "Bo", "status": "active"},
                {"id": "7", "name": "Ann", "status": "active"},
                {"id": "2", "name": "Cy", "status": "inactive"},
            ],
        )
        got = oracle(table)
        self.assertEqual([row["id"] for row in got.rows], ["7", "x9"])

    def test_a_crashing_oracle_is_reported_as_no_answer(self) -> None:
        # The guard must turn a crash into "no answer" so the learner counts
        # the probe and moves on instead of dying mid-query.

        def exploding(table):
            raise TypeError("mixed keys")

        benchmark.FAMILIES["__explodes__"] = {
            "columns": ["id"],
            "spec": {"id": [1, 2]},
            "oracle": exploding,
        }
        self.addCleanup(benchmark.FAMILIES.pop, "__explodes__", None)
        guarded = benchmark.guarded_oracle("__explodes__")
        table = benchmark.Table(["id"], [{"id": "1"}])
        self.assertIsNone(guarded(table))

    def test_ambiguity_is_reported_with_the_number_of_surviving_programs(self) -> None:
        oracle = benchmark.guarded_oracle("tax")
        demo = benchmark.covering_instance("tax", random.Random(8))
        result = induce(oracle, [(demo, oracle(demo))], seed=8, max_probes=24, validation_cases=6)
        self.assertTrue(result.success)
        payload = result.to_dict()
        self.assertEqual(payload["consistent_programs"], result.consistent_programs)
        self.assertGreaterEqual(payload["consistent_programs"], 1)
        self.assertIn("ambiguous", payload)


class VocabularyExtensionTests(unittest.TestCase):
    """The computer surface grows by learning what this machine can really do.

    Nothing here is mocked and no command is supplied by the test: the creature
    reads a goal, finds a mechanism in the machine's own documentation or by
    differential experiment, and is believed only when the real shell produces
    the exact bytes -- on the file and on a probe it designs itself.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = "Delta\nalpha\nCharlie\nbravo\n"
        self.notes = "notes.txt"

    def _agent(self, *, bin_dir: Path | None = None) -> LivingAgent:
        computer = Computer(self.root, bin_dir=bin_dir) if bin_dir is not None else Computer(self.root)
        agent = LivingAgent(self.root, computer=computer)
        if not agent.computer.exists(self.notes):
            agent.computer.write(self.notes, self.source)
        return agent

    @staticmethod
    def _reverse_lines(text: str) -> str:
        return "\n".join(reversed(text.split("\n")[:-1])) + "\n"

    @staticmethod
    def _reverse_characters(text: str) -> str:
        return "\n".join(line[::-1] for line in text.split("\n")[:-1]) + "\n"

    def test_an_unapproved_binary_is_refused_before_it_runs(self) -> None:
        agent = self._agent()
        self.assertNotIn("rev", agent.computer.admitted())
        with self.assertRaises(AgentError) as raised:
            agent.computer.run(f"rev {self.notes}")
        self.assertEqual(str(raised.exception), "BINARY_NOT_ADMITTED:rev")

    def test_reverse_each_line_is_found_by_the_name_the_machine_uses(self) -> None:
        agent = self._agent()
        started = time.perf_counter()
        outcome = agent.fulfil("reverse each line of notes.txt", self.notes)
        elapsed = time.perf_counter() - started
        self.assertEqual(outcome["status"], "PASS")
        self.assertEqual(outcome["tool"], "rev")
        self.assertEqual(outcome["source"], "name")
        self.assertEqual(outcome["stdout"], self._reverse_characters(self.source))
        self.assertIn("rev", agent.computer.admitted())
        self.assertIn("Reverse", outcome["documentation"])
        self.assertEqual(agent.computer.run(outcome["command"]).stdout, outcome["stdout"])
        self.assertLess(elapsed, 2.0)

    def test_reverse_the_lines_is_proved_by_experiment_not_by_a_word(self) -> None:
        agent = self._agent()
        outcome = agent.discover("reverse the lines of notes.txt", self.notes)
        self.assertEqual(outcome["stdout"], self._reverse_lines(self.source))
        self.assertEqual(outcome["tool"], "tac")
        self.assertEqual(outcome["source"], "differential")
        # ``rev`` matched the word "reverse" and was tried first; the shell
        # rejected it, and the record shows the rejection.
        rejected = [row for row in agent.discovery_log if row["tool"] == "rev" and not row["verified"]]
        self.assertTrue(rejected)
        self.assertIn("last line first", outcome["documentation"])

    def test_a_tool_whose_documentation_lies_is_rejected(self) -> None:
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        decoy = bin_dir / "reverse"
        decoy.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "--help" ]; then\n'
            "  echo 'Usage: reverse [FILE]'\n"
            "  echo\n"
            "  echo 'Reverse the lines of the file.'\n"
            "  exit 0\n"
            "fi\n"
            "tr '[:lower:]' '[:upper:]' < \"$1\"\n",
            encoding="utf-8",
        )
        decoy.chmod(0o755)
        agent = self._agent(bin_dir=bin_dir)
        outcome = agent.discover("reverse each line of notes.txt", self.notes)
        self.assertEqual(outcome["tool"], "rev")
        self.assertEqual(outcome["stdout"], self._reverse_characters(self.source))
        rejected = [row for row in agent.discovery_log if row["tool"] == "reverse"]
        self.assertEqual(len(rejected), 1)
        self.assertFalse(rejected[0]["verified"])
        self.assertEqual(rejected[0]["documentation"], "Reverse the lines of the file")
        self.assertNotIn("reverse", agent.computer.admitted())

    def test_number_the_lines_is_numbering_and_number_of_is_counting(self) -> None:
        # The same word, two functions.  "Number the lines" enumerates them;
        # "the number of lines" is a quantity.  Both answers are exact, and
        # they are different answers.
        agent = self._agent()
        agent.computer.write("notes.txt", "delta\nalpha\ncharlie\nbravo\nzulu\n")
        numbered = agent.fulfil("number the lines of notes.txt", "notes.txt")
        self.assertEqual(
            numbered["stdout"],
            "     1\tdelta\n     2\talpha\n     3\tcharlie\n     4\tbravo\n     5\tzulu\n",
        )
        counted = agent.fulfil("the number of lines in notes.txt", "notes.txt")
        self.assertEqual(counted["stdout"], "5\n")
        self.assertNotEqual(numbered["command"], counted["command"])

    def test_blank_lines_get_numbers_from_a_value_the_tool_documents(self) -> None:
        # `nl` leaves empty lines unnumbered; numbering them needs `-b a`, and
        # "a means number all lines" exists only in nl's own help text.  The
        # goal fixes the bytes, so the bare tool is not good enough and the
        # document's enumeration is what closes the gap.
        agent = self._agent()
        agent.computer.write("notes.txt", "alpha\n\nbeta\ngamma\n")
        outcome = agent.fulfil("number the lines of notes.txt", "notes.txt")
        self.assertEqual(outcome["source"], "documentation-options")
        self.assertIn("-b a", outcome["command"])
        self.assertEqual(
            outcome["stdout"], "     1\talpha\n     2\t\n     3\tbeta\n     4\tgamma\n"
        )
        rows = [row for row in agent.discovery_log if row["tool"] == "nl"]
        self.assertTrue(any(row["verified"] and row["argv"] == ["-b", "a"] for row in rows))

    def test_a_one_letter_file_name_does_not_mangle_the_goal(self) -> None:
        # Regression: the file stem was stripped from the goal as a *substring*,
        # so `n.txt` deleted every letter "n" and turned "lines" into "lies" --
        # which made a clear request ambiguous.  Names are words, not patterns.
        agent = self._agent()
        agent.computer.write("n.txt", "delta\nalpha\ncharlie\n")
        outcome = agent.discover("reverse the lines of n.txt", "n.txt")
        self.assertEqual(outcome["tool"], "tac")
        self.assertEqual(outcome["stdout"], "charlie\nalpha\ndelta\n")

    def test_the_second_discovery_does_not_read_the_machine_again(self) -> None:
        agent = self._agent()
        agent.computer.write("n.txt", "delta\nalpha\ncharlie\n")
        agent.discover("reverse the lines of n.txt", "n.txt")
        reads = agent.vocabulary.help_reads
        agent.computer.write("m.txt", "zulu\nyankee\nxray\n")
        started = time.perf_counter()
        outcome = agent.discover("reverse the lines of m.txt", "m.txt")
        elapsed = time.perf_counter() - started
        self.assertEqual(outcome["tool"], "tac")
        self.assertEqual(outcome["stdout"], "xray\nyankee\nzulu\n")
        self.assertEqual(agent.vocabulary.help_reads, reads)
        self.assertLess(elapsed, 1.0)

    def test_a_stranger_tool_is_probed_in_a_throwaway_directory(self) -> None:
        # A real sweep of this machine left seventeen empty `gz*` files in the
        # tree: some installed tool writes beside its input.  A candidate is
        # arbitrary code, so trying one must never be able to touch the
        # creature's files -- nor to blind the trials that come after it.
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        hostile = bin_dir / "scribble"
        hostile.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "--help" ]; then\n'
            "  echo 'Usage: scribble FILE'\n"
            "  echo\n"
            "  echo 'Copy the file, scribble beside it, remove it.'\n"
            "  exit 0\n"
            "fi\n"
            'touch "$PWD/leak.txt" "$HOME/leak.txt"\n'
            'cat "$1"\n'
            'rm -f "$1"\n',
            encoding="utf-8",
        )
        hostile.chmod(0o755)
        agent = self._agent(bin_dir=bin_dir)
        work = self.root / "work"
        work.mkdir()
        (work / "keep.txt").write_text("hello\n", encoding="utf-8")
        before = sorted(path.name for path in work.iterdir())
        self.assertEqual(
            agent.vocabulary.trial("scribble", "keep.txt", cwd=str(work)), "hello\n"
        )
        self.assertEqual(sorted(path.name for path in work.iterdir()), before)
        self.assertEqual(
            sorted(path.name for path in self.root.iterdir()), ["bin", "notes.txt", "work"]
        )
        self.assertEqual(list(Path(tempfile.gettempdir()).glob("brain-trial-*")), [])
        # the hostile tool ate its own copy in its own directory; the honest
        # tool in the same sweep is unaffected
        self.assertEqual(
            agent.vocabulary.sweep("hello\nmoon\n", "moon\nhello\n", names=["scribble", "tac"]),
            ["tac"],
        )

    def test_an_endless_writer_is_stopped_not_read(self) -> None:
        # `yes` never stops.  Reading it without a byte cap is a memory bomb,
        # so a run that is cut short must be reported as cut short.
        self.assertTrue(Path("/usr/bin/yes").is_file())
        code, raw = discovery._run_capped(["/usr/bin/yes"], timeout=0.2, limit=65_536)
        self.assertEqual(code, 137)
        self.assertLessEqual(len(raw), 65_536)

    def test_a_tool_that_closes_then_exits_is_not_killed(self) -> None:
        # Regression: killing the child the instant its pipe drained reported
        # -9 for tools that had answered correctly, so real caps were dropped
        # at random from sweeps.  EOF must be followed by a normal wait.
        for _ in range(25):
            code, raw = discovery._run_capped(["/bin/sh", "-c", "printf 'x\\n'"], timeout=1.0)
            self.assertEqual((code, raw), (0, b"x\n"))

    def test_an_ambiguous_goal_is_refused_instead_of_guessed(self) -> None:
        agent = self._agent()
        with self.assertRaises(AgentError) as raised:
            agent.discover("reverse the file", self.notes)
        message = str(raised.exception)
        self.assertTrue(message.startswith("GOAL_AMBIGUOUS"), message)
        self.assertIn("rev", message)
        self.assertIn("tac", message)
        self.assertIn("reverse the file", agent.open_questions())

    def test_an_unknown_verb_is_an_impasse_and_admits_nothing(self) -> None:
        agent = self._agent()
        before = agent.computer.admitted()
        with self.assertRaises(AgentError) as raised:
            agent.fulfil("frobnicate the file thoroughly", self.notes)
        self.assertEqual(str(raised.exception), "GOAL_NOT_VERIFIABLE")
        self.assertEqual(agent.computer.admitted(), before)
        self.assertIn("frobnicate the file thoroughly", agent.open_questions())
        # State-changing and network tools are not even candidates: extending
        # the reading vocabulary must never extend the creature's authority.
        discoverable = {name for name, _ in agent.vocabulary.executables()}
        self.assertFalse(discoverable & {"rm", "mv", "cp", "curl", "wget", "ssh", "dd", "sh"})

    def test_the_learned_capability_costs_nothing_the_second_time(self) -> None:
        agent = self._agent()
        first = agent.discover("reverse each line of notes.txt", self.notes)
        reads = agent.vocabulary.help_reads
        agent.computer.write("other.txt", "one\nTwo\nthree\n")
        started = time.perf_counter()
        second = agent.discover("reverse each line of other.txt", "other.txt")
        elapsed = time.perf_counter() - started
        self.assertEqual(second["source"], "memory")
        self.assertEqual(second["stdout"], self._reverse_characters("one\nTwo\nthree\n"))
        self.assertEqual(agent.vocabulary.help_reads, reads)
        self.assertLess(elapsed, 0.2)
        self.assertEqual(first["tool"], "rev")
        self.assertEqual([record["tool"] for record in agent.capabilities.values()], ["rev"])

    def test_a_capability_survives_a_snapshot_and_is_re_verified(self) -> None:
        agent = self._agent()
        agent.discover("reverse each line of notes.txt", self.notes)
        payload = json.loads(json.dumps(agent.snapshot()))

        other_root = Path(self.tmp.name) / "clone"
        clone = LivingAgent(other_root)
        clone.restore(payload)
        self.assertIn("rev", clone.computer.admitted())
        clone.computer.write("fresh.txt", "ab\ncd\nef\n")
        started = time.perf_counter()
        outcome = clone.discover("reverse each line of fresh.txt", "fresh.txt")
        elapsed = time.perf_counter() - started
        self.assertEqual(outcome["source"], "memory")
        self.assertEqual(outcome["stdout"], "ba\ndc\nfe\n")
        self.assertLess(elapsed, 0.2)

        # A tampered admission record is not trusted: the hash must match the
        # binary that is actually on this machine.
        forged = json.loads(json.dumps(payload))
        forged["admissions"]["rev"]["sha256"] = "0" * 64
        suspicious = LivingAgent(Path(self.tmp.name) / "suspicious").restore(forged)
        self.assertNotIn("rev", suspicious.computer.admitted())

    def test_a_discovered_stage_composes_with_the_known_grammar(self) -> None:
        agent = self._agent()
        agent.discover("reverse the lines of notes.txt", self.notes)
        # Last three lines of the file, in their original (unsorted) order:
        # only tac followed by a head can produce this, and tac was discovered
        # at runtime rather than written into the grammar.
        text = "b\na\nd\nc\n"
        agent.computer.write("order.txt", text)
        target = "c\nd\na\n"
        examples = [(text, target)]
        stages = synthesis.instantiate(examples) + tuple(agent._stages.values())
        candidates, _stats = synthesis.search(examples, max_length=2, beam=80, stages=stages)
        self.assertTrue(candidates, "the discovered stage was not available to the synthesiser")
        composed = [candidate for candidate in candidates if any(stage.startswith("tac") for stage in candidate)]
        self.assertTrue(composed, candidates[:5])
        command = synthesis.command_for(composed[0]).replace("{path}", "order.txt")
        self.assertEqual(agent.computer.run(command).stdout, target)


class RealFileTreeTests(unittest.TestCase):
    """Learning over the repository's real file tree, verified on unseen dirs."""

    def test_large_file_report_generalizes_to_unseen_directories(self) -> None:
        oracle = benchmark.oracle_large_files
        demo = benchmark.real_tree_table(ROOT / "canonical" / "capabilities")
        self.assertGreater(len(demo.rows), 20)
        result = induce(oracle, [(demo, oracle(demo))], seed=3, max_probes=24, validation_cases=6)
        self.assertTrue(result.success, result.failure_reason)
        filter_step = result.program[0]
        self.assertEqual(filter_step["op"], "filter")
        self.assertEqual(str(filter_step["value"]), "20000")
        for directory in ("canonical/runtime", "execution_guard", "tests"):
            with self.subTest(directory=directory):
                table = benchmark.real_tree_table(ROOT / directory)
                want = oracle(table)
                got = apply_program(result.program, table)
                self.assertEqual(got.columns, want.columns)
                self.assertEqual(got.rows, want.rows)

    def test_bytes_by_extension_generalizes_to_unseen_directories(self) -> None:
        oracle = benchmark.oracle_bytes_by_ext
        demo = benchmark.real_tree_table(ROOT / "canonical" / "capabilities")
        result = induce(oracle, [(demo, oracle(demo))], seed=3, max_probes=24, validation_cases=6)
        self.assertTrue(result.success, result.failure_reason)
        for directory in ("canonical/runtime", "execution_guard", "tests"):
            with self.subTest(directory=directory):
                table = benchmark.real_tree_table(ROOT / directory)
                want = oracle(table)
                got = apply_program(result.program, table)
                self.assertEqual(got.columns, want.columns)
                self.assertEqual(got.rows, want.rows)


class RealRepositoryShellTests(unittest.TestCase):
    """A real computer task on real repository files, exact counts."""

    def test_python_file_count_generalizes_across_real_directories(self) -> None:
        import shutil

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = {
                "guard": ROOT / "execution_guard",
                "laws": ROOT / "canonical" / "laws",
                "ctests": ROOT / "canonical" / "tests",
            }
            for name, source in sources.items():
                shutil.copytree(source, root / name)
            agent = LivingAgent(root)
            skill = agent.learn_shell_skill(
                "count the python files in a directory",
                "find guard -name '*.py' | wc -l",
                {"dir": "guard"},
                canary=({"probe_dir/one.py": "", "probe_dir/two.py": "", "probe_dir/no.txt": ""}, "2"),
                postcondition=r"^[0-9]+$",
            )
            self.assertEqual(skill.template, "find {dir} -name '*.py' | wc -l")
            counts = {name: len(list((root / name).rglob("*.py"))) for name in sources}
            self.assertGreater(counts["ctests"], 50)
            for name, expected in counts.items():
                with self.subTest(directory=name):
                    outcome = agent.solve(f"count the python files in '{name}'")
                    self.assertEqual(outcome["status"], "PASS", outcome)
                    self.assertEqual(int(outcome["stdout"]), expected)


class ProvenanceAndBudgetTests(unittest.TestCase):
    """No model, no network, no spend, no hidden authority."""

    def test_modules_contain_no_model_or_network_client(self) -> None:
        forbidden = ("import socket", "import urllib", "import requests", "http.client", "openai", "anthropic")
        for relative in (
            "canonical/runtime/living_core_v1.py",
            "canonical/runtime/living_agent_v1.py",
            "canonical/runtime/living_agent_benchmark_v1.py",
        ):
            with self.subTest(module=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(token, source)

    def test_snapshot_declares_zero_dependency_and_zero_spend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = LivingAgent(tmp)
            agent.computer.write("demo.txt", "a\n")
            agent.learn_shell_skill(
                "count the lines in a file",
                "wc -l < demo.txt",
                {"path": "demo.txt"},
                canary=({"canary.txt": "a\nb\n"}, "2"),
                postcondition=r"^[0-9]+$",
            )
            payload = agent.snapshot()
            self.assertEqual(payload["schema"], AGENT_SCHEMA)
            self.assertEqual(payload["model_dependency_count"], 0)
            self.assertEqual(payload["network_dependency_count"], 0)
            self.assertEqual(payload["incremental_spend_usd"], 0)


class PipelineSynthesisTests(unittest.TestCase):
    """New computer skills learned from *results*, not from commands.

    Every case uses real repository data written to a real sandbox, and every
    learned skill is executed by the real shell and compared byte for byte on
    files the learner never saw.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = LivingAgent(self.root)
        self.demo_dir = ROOT / "canonical" / "capabilities"
        self.fresh_dirs = [ROOT / "tests", ROOT / "execution_guard"]

    def _write_csv(self, name: str, directory: Path) -> "object":
        table = benchmark.real_tree_table(directory, pattern="*")
        self.agent.computer.write(name, table.to_csv())
        return table

    def _two_demos(self) -> "tuple[object, object]":
        first = self._write_csv("demo.csv", self.demo_dir)
        second = self._write_csv("demo2.csv", self.fresh_dirs[1])
        return first, second

    def test_learns_field_extraction_from_real_tree_data(self) -> None:
        table, second = self._two_demos()
        self.assertGreater(len(table.rows), 50)
        examples = [
            ("demo.csv", "\n".join(row["name"] for row in table.rows) + "\n"),
            ("demo2.csv", "\n".join(row["name"] for row in second.rows) + "\n"),
        ]
        outcome = self.agent.acquire("list the file names in the listing", examples)
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertLessEqual(len(outcome["stages"]), 3)
        self.assertLessEqual(outcome["exact_hypotheses"], 4)
        self.assertLess(outcome["probe_seconds"], 0.5)
        self.assertLess(outcome["seconds"], 2.5)
        self.assertLessEqual(outcome["commands_run"], 8)
        for directory in (ROOT / "canonical" / "governance", ROOT / "canonical" / "laws"):
            with self.subTest(directory=directory.name):
                fresh = self._write_csv("fresh.csv", directory)
                want = "\n".join(row["name"] for row in fresh.rows) + "\n"
                result = self.agent.solve("list the file names in 'fresh.csv'")
                self.assertEqual(result["status"], "PASS", result)
                self.assertEqual(result["stdout"], want)

    def test_learns_numeric_total_from_real_tree_data(self) -> None:
        table, second = self._two_demos()
        examples = [
            ("demo.csv", "%.0f\n" % sum(int(row["size"]) for row in table.rows)),
            ("demo2.csv", "%.0f\n" % sum(int(row["size"]) for row in second.rows)),
        ]
        outcome = self.agent.acquire("total the sizes in the listing", examples)
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertLess(outcome["seconds"], 2.5)
        for directory in (ROOT / "canonical" / "governance", ROOT / "canonical" / "laws"):
            with self.subTest(directory=directory.name):
                fresh = self._write_csv("fresh.csv", directory)
                want = "%.0f\n" % sum(int(row["size"]) for row in fresh.rows)
                result = self.agent.solve("total the sizes in 'fresh.csv'")
                self.assertEqual(result["stdout"], want)

    def test_three_unrelated_skills_coexist_and_route_correctly(self) -> None:
        table, second = self._two_demos()
        def examples(make):
            return [("demo.csv", make(table)), ("demo2.csv", make(second))]
        names = lambda t: "\n".join(row["name"] for row in t.rows) + "\n"
        total = lambda t: "%.0f\n" % sum(int(row["size"]) for row in t.rows)
        extensions = lambda t: "\n".join(sorted({row["ext"] for row in t.rows})) + "\n"
        self.assertEqual(self.agent.acquire("list the file names", examples(names))["status"], "PASS")
        self.assertEqual(self.agent.acquire("total the sizes", examples(total))["status"], "PASS")
        self.assertEqual(self.agent.acquire("list the distinct extensions", examples(extensions))["status"], "PASS")
        self.assertEqual(len(self.agent.skills), 3)
        fresh = self._write_csv("fresh.csv", self.fresh_dirs[0])
        checks = {
            "list the file names in 'fresh.csv'": "\n".join(row["name"] for row in fresh.rows) + "\n",
            "total the sizes in 'fresh.csv'": "%.0f\n" % sum(int(row["size"]) for row in fresh.rows),
            "list the distinct extensions in 'fresh.csv'": "\n".join(sorted({row["ext"] for row in fresh.rows})) + "\n",
        }
        for goal, want in checks.items():
            with self.subTest(goal=goal):
                result = self.agent.solve(goal)
                self.assertEqual(result["status"], "PASS", result)
                self.assertEqual(result["stdout"], want)

    def test_header_handling_survives_an_extension_that_sorts_early(self) -> None:
        """A coincidence that passes two demos must not become a skill.

        The listing's header cell ("ext") sorts before every real extension on
        the demo data, so dropping the *first sorted line* looks correct there.
        The moment a real extension sorts before "ext", only a pipeline that
        drops the header row first survives.
        """
        dirs = []
        for index, names in enumerate(
            (
                ("x.py", "y.md", "z.json", "w.py"),
                ("a.cfg", "b.py", "c.yaml", "d.cfg", "e.txt"),
            )
        ):
            directory = self.root / f"demo_dir{index}"
            directory.mkdir()
            for name in names:
                (directory / name).write_text("payload", encoding="utf-8")
            dirs.append(directory)
        examples = []
        for index, directory in enumerate(dirs):
            table = benchmark.real_tree_table(directory, pattern="*")
            self.agent.computer.write(f"demo{index}.csv", table.to_csv())
            examples.append(
                (f"demo{index}.csv", "\n".join(sorted({r["ext"] for r in table.rows})) + "\n")
            )
        outcome = self.agent.acquire("list the distinct extensions in the listing", examples)
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertIn("tail -n +2", outcome["stages"])
        held = self.root / "held_dir"
        held.mkdir()
        for name in ("a.aaa", "b.py", "c.zzz", "d.aaa"):
            (held / name).write_text("x", encoding="utf-8")
        table = benchmark.real_tree_table(held, pattern="*")
        self.agent.computer.write("held.csv", table.to_csv())
        want = "\n".join(sorted({r["ext"] for r in table.rows})) + "\n"
        result = self.agent.solve("list the distinct extensions in 'held.csv'")
        self.assertEqual(result["stdout"], want)

    def test_behavioural_retrieval_reuses_a_skill_under_new_words(self) -> None:
        table, second = self._two_demos()
        examples = [
            ("demo.csv", "%.0f\n" % sum(int(row["size"]) for row in table.rows)),
            ("demo2.csv", "%.0f\n" % sum(int(row["size"]) for row in second.rows)),
        ]
        self.agent.acquire("total the sizes in the listing", examples)
        before = set(self.agent.skills)
        outcome = self.agent.acquire(
            "what is the aggregate byte weight of this inventory", examples
        )
        self.assertTrue(outcome.get("reused"), outcome)
        self.assertEqual(set(self.agent.skills), before)

    def test_snapshot_restore_solves_without_the_examples(self) -> None:
        table, second = self._two_demos()
        examples = [
            ("demo.csv", "\n".join(row["name"] for row in table.rows) + "\n"),
            ("demo2.csv", "\n".join(row["name"] for row in second.rows) + "\n"),
        ]
        self.agent.acquire("list the file names in the listing", examples)
        payload = json.loads(json.dumps(self.agent.snapshot()))
        other = LivingAgent(self.root)
        other.restore(payload)
        fresh = self._write_csv("fresh.csv", ROOT / "canonical" / "governance")
        want = "\n".join(row["name"] for row in fresh.rows) + "\n"
        result = other.solve("list the file names in 'fresh.csv'")
        self.assertEqual(result["stdout"], want)

    def test_degenerate_examples_are_reported_as_ambiguous(self) -> None:
        content = "b\na\nb\n"
        other = "z\nz\ny\n"
        self.agent.computer.write("degenerate.txt", content)
        self.agent.computer.write("degenerate2.txt", other)
        outcome = self.agent.acquire(
            "return the text unchanged",
            [("degenerate.txt", content), ("degenerate2.txt", other)],
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertGreater(outcome["exact_hypotheses"], 1)
        self.assertEqual(self.agent.solve("return the text unchanged: 'degenerate.txt'")["stdout"], content)

    def test_a_stated_pipeline_length_limit_is_a_hard_failure(self) -> None:
        self.agent.computer.write("words.txt", "one two two three\n")
        self.agent.computer.write("words2.txt", "red blue red green\n")
        with self.assertRaises(AgentError) as raised:
            self.agent.acquire(
                "unique words",
                [("words.txt", "one\nthree\ntwo\n"), ("words2.txt", "blue\ngreen\nred\n")],
                max_length=1,
            )
        self.assertEqual(str(raised.exception), "NO_PIPELINE_WITHIN_BUDGET")

    def test_examples_are_required(self) -> None:
        with self.assertRaises(AgentError) as raised:
            self.agent.acquire("do the thing", [])
        self.assertEqual(str(raised.exception), "EXAMPLES_REQUIRED")

    def test_one_example_is_refused_as_unidentifiable(self) -> None:
        table, _second = self._two_demos()
        with self.assertRaises(AgentError) as raised:
            self.agent.acquire(
                "list the file names", [("demo.csv", "\n".join(r["name"] for r in table.rows) + "\n")]
            )
        self.assertEqual(str(raised.exception), "TOO_FEW_EXAMPLES")

    def test_search_and_real_verification_agree(self) -> None:
        from canonical.runtime import shell_synthesis_v1 as synthesis

        table = self._write_csv("demo.csv", self.demo_dir)
        text = table.to_csv()
        expected = "\n".join(row["name"] for row in table.rows) + "\n"
        candidates, stats = synthesis.search([(text, expected)])
        self.assertGreaterEqual(len(candidates), 1)
        self.assertLessEqual(len(candidates), 4)
        self.assertLess(stats["seconds"], 0.5)
        ok, template, failures = synthesis.verify(
            self.agent.computer.run, candidates[0], [(text, expected)], input_slot_values=["demo.csv"]
        )
        self.assertTrue(ok, failures)
        self.assertIn("{path}", template)


class DocumentedArgumentTests(unittest.TestCase):
    """Capabilities that need an argument, learned from the machine's own help.

    No test here supplies a command, a flag or a value.  A goal and two real
    examples are the whole specification; the tool's ``--help`` supplies the
    space of possible mechanisms; the exact bytes the shell produces decide.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _agent(self, *, bin_dir: Path | None = None) -> LivingAgent:
        computer = Computer(self.root, bin_dir=bin_dir) if bin_dir is not None else Computer(self.root)
        return LivingAgent(self.root, computer=computer)

    def _write(self, agent: LivingAgent, name: str, text: str) -> str:
        agent.computer.write(name, text)
        return text

    @staticmethod
    def _fold(text: str, width: int) -> str:
        """Reference implementation of greedy folding, written for the test."""
        out: list[str] = []
        for line in text.split("\n")[:-1]:
            while len(line) > width:
                out.append(line[:width])
                line = line[width:]
            out.append(line)
        return "\n".join(out) + "\n"

    def test_a_keyed_sort_is_bound_from_the_data_not_from_a_table(self) -> None:
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\n")
        self._write(agent, "two.csv", "kiwi,7\nbanana,3\ncherry,12\n")
        goal = "sort the rows by the second column, comma separated"
        outcome = agent.acquire(
            goal,
            [
                ("one.csv", "fig,1\napple,10\npear,2\n"),
                ("two.csv", "cherry,12\nbanana,3\nkiwi,7\n"),
            ],
        )
        self.assertEqual(outcome["status"], "PASS")
        self.assertEqual(outcome["tool"], "sort")
        # both the key and the separator had to be bound: sorting whole lines
        # gives a different answer on both examples, so a bare `sort` cannot fit
        self.assertIn("-k", outcome["argv"])
        self.assertIn("-t", outcome["argv"])
        self.assertEqual(outcome["stdout"], "fig,1\napple,10\npear,2\n")
        self.assertLessEqual(outcome["commands_run"], 60)
        # a table it has never seen, through memory rather than a new search
        rows = len(agent.discovery_log)
        self._write(agent, "held.csv", "zebra,4\nmule,9\nokapi,0\n")
        again = agent.solve(goal, bindings={"path": "held.csv"})
        self.assertEqual(again["stdout"], "okapi,0\nzebra,4\nmule,9\n")
        self.assertEqual(len(agent.discovery_log), rows)

    def test_a_documented_mechanism_composes_with_the_known_grammar(self) -> None:
        # No stage of `sort -k 2 -t , | head -n 2` is in the fixed grammar: the
        # keyed sort needs a key *and* a delimiter, both bound from the request
        # and the data.  The creature must find it by composing the machine's
        # own documented tool with stages it already knows, and prove it.
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        self._write(agent, "two.csv", "zulu,5\nyankee,3\nxray,9\n")
        goal = "sort the rows by the second column, comma separated, and keep the first two"
        examples = [
            ("one.csv", "fig,1\napple,10\n"),
            ("two.csv", "yankee,3\nzulu,5\n"),
        ]
        outcome = agent.acquire(goal, examples)
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["source"], "composed")
        self.assertEqual(outcome["tool"], "sort")
        self.assertEqual(len(outcome["stages"]), 2)
        self.assertEqual(outcome["stages"][0], "sort -k 2 -t ,")
        self.assertEqual(outcome["stdout"], examples[0][1])
        self.assertLessEqual(outcome["commands_run"], 64)
        self.assertLess(outcome["seconds"], 1.5)
        # a table it has never seen, through memory rather than a new search
        rows = len(agent.discovery_log)
        self._write(agent, "held.csv", "mule,4\nokapi,9\nzebra,1\n")
        started = time.perf_counter()
        again = agent.solve(goal, bindings={"path": "held.csv"})
        self.assertEqual(again["stdout"], "zebra,1\nmule,4\n")
        self.assertEqual(len(agent.discovery_log), rows)
        self.assertLess(time.perf_counter() - started, 0.1)

    def test_a_pipe_separated_table_is_sorted_on_its_column(self) -> None:
        # `|` is a shell operator, so the separator cannot be written into a
        # command unquoted: the bound argument has to survive the pipeline as
        # data.  The third column, not the second, and four rows on the file it
        # has never seen -- so a pipeline that happens to fit the examples by
        # reversing the first two rows is not enough.
        agent = self._agent()
        self._write(agent, "one.psv", "a|zap|9\nb|yank|3\nc|xray|7\n")
        self._write(agent, "two.psv", "k|mike|5\nl|lima|1\n")
        goal = "sort the rows by the third column, pipe separated, and keep the first two"
        outcome = agent.acquire(
            goal,
            [("one.psv", "b|yank|3\nc|xray|7\n"), ("two.psv", "l|lima|1\nk|mike|5\n")],
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["source"], "composed")
        self.assertEqual(outcome["stages"][0], "sort -k 3 -t '|'")
        self.assertEqual(outcome["stdout"], "b|yank|3\nc|xray|7\n")
        self._write(agent, "held.psv", "q|quebec|8\nr|romeo|2\ns|sierra|6\nt|tango|4\n")
        again = agent.solve(goal, bindings={"path": "held.psv"})
        self.assertEqual(again["stdout"], "r|romeo|2\nt|tango|4\n")

    def test_examples_that_contradict_the_named_column_are_not_answered(self) -> None:
        # Column three is 9, 3, 7, so no sort of that column begins "3, 9".
        # `head -n 2 | sort -r` reproduces the stated bytes exactly -- and
        # contradicts every word of the request after the verb.  Two
        # specifications disagree; the creature must say so instead of
        # adopting the pipeline that fits the bytes and ignoring the sentence.
        agent = self._agent()
        self._write(agent, "one.psv", "a|zap|9\nb|yank|3\nc|xray|7\n")
        self._write(agent, "two.psv", "k|mike|5\nl|lima|1\n")
        goal = "sort the rows by the third column, pipe separated, and keep the first two"
        before = set(agent.computer.admitted())
        with self.assertRaises(AgentError) as raised:
            agent.acquire(
                goal,
                [("one.psv", "b|yank|3\na|zap|9\n"), ("two.psv", "l|lima|1\nk|mike|5\n")],
            )
        self.assertIn("EXAMPLES_CONTRADICT_GOAL", str(raised.exception))
        self.assertEqual(agent.skills, {})
        gap = [entry.payload for entry in agent.memory.active() if entry.payload.get("goal") == goal]
        self.assertEqual(gap[0]["reason"], "evidence_conflict")
        # every way the pipeline contradicts the sentence, recorded at once
        self.assertEqual(
            sorted(gap[0]["unexplained"]),
            ["first 2 last", "position 3", "separator |"],
        )
        # The rejected search admitted tools to run them; none may survive it.
        self.assertEqual(set(agent.computer.admitted()), before)

    def test_a_count_must_use_the_column_it_names(self) -> None:
        # `ptx -g 2 -F , | sort -u | wc -l` reproduces "3" on both examples
        # without ever reading a column: -g is a gap width.  The request says
        # the count is over the second column, so two real probes decide it:
        # hold that column constant and a count must move; change the columns
        # the request never mentions and it must not.  Held-out files then
        # answer 2 and 1, not 3.
        agent = self._agent()
        self._write(agent, "one.csv", "x,10\nx,3\ny,7\n")
        self._write(agent, "two.csv", "q,2\nq,9\nr,4\n")
        goal = "count the distinct values in the second column, comma separated"
        outcome = agent.acquire(goal, [("one.csv", "3\n"), ("two.csv", "3\n")])
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["stages"][0], "cut -f 2 -d ,")
        self.assertIn("sort -u", outcome["stages"])
        self.assertIn("wc -l", outcome["stages"])
        self.assertEqual(outcome["stdout"], "3\n")
        for name, text, answer in (
            ("three.csv", "z,5\nz,5\nw,1\n", "2\n"),
            ("four.csv", "a,9\nb,9\nc,9\n", "1\n"),
        ):
            self._write(agent, name, text)
            self.assertEqual(agent.solve(goal, bindings={"path": name})["stdout"], answer)
        self.assertNotIn("ptx", {row["tool"] for row in agent.discovery_log if row.get("verified")})

    def test_a_tab_separated_table_is_sorted_on_its_column(self) -> None:
        # A TAB cannot be written into a command at all -- not literally (it is
        # a control character) and not with a shell escape (dash has none).
        # If that made tab-separated data unreachable, a very large part of a
        # computer would be unreachable too, so the creature has to find the
        # one portable spelling and prove it on real bytes.
        agent = self._agent()
        self._write(agent, "t1.tsv", "a\tzap\t9\nb\tyank\t3\nc\txray\t7\n")
        self._write(agent, "t2.tsv", "k\tmike\t5\nl\tlima\t1\n")
        goal = "sort the rows by the second column, tab separated, and keep the first two"
        outcome = agent.acquire(
            goal,
            [
                ("t1.tsv", "c\txray\t7\nb\tyank\t3\n"),
                ("t2.tsv", "l\tlima\t1\nk\tmike\t5\n"),
            ],
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["stages"][0], 'sort -k 2 -t "$(printf \'\\t\')"')
        self.assertEqual(outcome["argv"], ["-k", "2", "-t", "\t"])
        self._write(agent, "held.tsv", "q\tquebec\t8\nr\tromeo\t2\ns\tsierra\t6\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "held.tsv"})["stdout"],
            "q\tquebec\t8\nr\tromeo\t2\n",
        )

    def test_a_kind_of_request_is_learned_once_and_then_recalled(self) -> None:
        # The first request of a kind costs a real search.  The second one is a
        # different table, a different column, a different separator and a
        # different count -- and the creature should not search again: the
        # *kind* of request was learned, the parameters are bound fresh from the
        # new sentence and the new data, and the new examples still decide.
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        self._write(agent, "two.csv", "zulu,5\nyankee,3\nxray,9\n")
        first = agent.acquire(
            "sort the rows by the second column, comma separated",
            [
                ("one.csv", "fig,1\napple,10\npear,2\nkiwi,7\n"),
                ("two.csv", "yankee,3\nzulu,5\nxray,9\n"),
            ],
        )
        self.assertEqual(first["stages"], ["sort -k 2 -t ,"])
        # it really searched: the point of the memory claim below is that the
        # second request costs less than the first, so the first must have cost
        # something.  Six real commands is a search, not a recall.
        self.assertGreaterEqual(first["commands_run"], 4)

        self._write(agent, "three.csv", "aa;p;9\nbb;q;2\ncc;r;7\ndd;s;4\n")
        self._write(agent, "four.csv", "kk;t;8\nll;u;1\nmm;v;5\n")
        second = agent.acquire(
            "sort the rows by the third column, semicolon separated, and keep the first three",
            [
                ("three.csv", "bb;q;2\ndd;s;4\ncc;r;7\n"),
                ("four.csv", "ll;u;1\nmm;v;5\nkk;t;8\n"),
            ],
        )
        self.assertEqual(second["stages"], ["sort -k 3 -t ';'", "head -n 3"])
        self.assertTrue(second["remembered"], second)
        self.assertLessEqual(second["commands_run"], 8)
        # the second request costs less than the first: that is the whole point
        # of the memory, and the numbers are measured, not estimated.  The
        # margin is small because the first search is now fast, not because the
        # second one searched.
        self.assertLess(second["commands_run"], first["commands_run"])
        self.assertLess(second["seconds"], 0.1)
        # two-digit values in the key, where a numeric reading and the tool's
        # own text order disagree: 1, 10, 2 -- the verified bytes decide, and
        # any mechanism sorting numbers instead of text fails here
        self._write(agent, "held.csv", "m;x;10\nn;y;2\no;z;1\np;w;20\n")
        again = agent.solve(
            "sort the rows by the third column, semicolon separated, and keep the first three",
            bindings={"path": "held.csv"},
        )
        self.assertEqual(again["stdout"], "o;z;1\nm;x;10\nn;y;2\n")

    def test_a_request_that_names_its_tool_finds_it_first(self) -> None:
        # fold's own summary is "Wrap input lines in each FILE, writing to
        # standard output" -- it never says "line", so the sentence and the
        # documentation share one word and the keyword gate used to drop it.
        # But the sentence names the tool, which is the strongest evidence
        # there is, and the mechanism is then one process away.
        agent = self._agent()
        self._write(agent, "f1.txt", "a" * 45 + "\n")
        self._write(agent, "f2.txt", "b" * 45 + "\n")
        outcome = agent.acquire(
            "fold each line at 40 characters",
            [("f1.txt", "a" * 40 + "\n" + "a" * 5 + "\n"),
             ("f2.txt", "b" * 40 + "\n" + "b" * 5 + "\n")],
        )
        self.assertEqual(outcome["tool"], "fold")
        self.assertEqual(outcome["argv"], ["-w", "40"])
        self.assertLessEqual(outcome["commands_run"], 16)
        self._write(agent, "f3.txt", "c" * 50 + "\n")
        self.assertEqual(
            agent.solve("fold each line at 40 characters", bindings={"path": "f3.txt"})["stdout"],
            "c" * 40 + "\n" + "c" * 10 + "\n",
        )

    def test_the_same_sentence_on_different_data_rebinds_its_arguments(self) -> None:
        # The same words, a different table: the separator is no longer a
        # comma, so the mechanism that worked cannot be reused verbatim.  It
        # must be re-armed from the new data and re-proven -- and four
        # processes are enough to do it.
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        self._write(agent, "two.csv", "zulu,5\nyankee,3\nxray,9\n")
        agent.acquire(
            "sort the rows by the second column, comma separated",
            [
                ("one.csv", "fig,1\napple,10\npear,2\nkiwi,7\n"),
                ("two.csv", "yankee,3\nzulu,5\nxray,9\n"),
            ],
        )
        self._write(agent, "s1.txt", "pear 2\napple 10\nfig 1\n")
        self._write(agent, "s2.txt", "zulu 5\nyankee 3\n")
        outcome = agent.acquire(
            "sort the rows by the second column",
            [("s1.txt", "fig 1\napple 10\npear 2\n"), ("s2.txt", "yankee 3\nzulu 5\n")],
        )
        self.assertEqual(outcome["stages"], ["sort -k 2 -t ' '"])
        self.assertTrue(outcome["remembered"], outcome)
        self.assertLessEqual(outcome["commands_run"], 6)
        self._write(agent, "held.txt", "m 4\nb 2\nz 8\n")
        self.assertEqual(
            agent.solve("sort the rows by the second column", bindings={"path": "held.txt"})["stdout"],
            "b 2\nm 4\nz 8\n",
        )

    @staticmethod
    def _sorted_by(text: str, separator: str, position: int) -> str:
        rows = [line.split(separator) for line in text.splitlines()]
        rows.sort(key=lambda row: row[position - 1])
        return "".join(separator.join(row) + "\n" for row in rows)

    def test_a_kind_of_request_learned_once_covers_new_arguments(self) -> None:
        # One demonstration of "sort the rows by a column" is a *kind*, not a
        # single command: the next request names a different column and a
        # different separator, and the creature must find the same mechanism
        # with the new values rather than start from nothing.
        agent = self._agent()
        first = self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        second = self._write(agent, "two.csv", "zulu,5\nyankee,3\n")
        taught = [
            ("one.csv", self._sorted_by(first, ",", 2)),
            ("two.csv", self._sorted_by(second, ",", 2)),
        ]
        self.assertNotEqual(taught[0][1], first)  # the example must show a change
        learned = agent.acquire("sort the rows by the second column, comma separated", taught)
        self.assertEqual(learned["stages"], ["sort -k 2 -t ,"], learned)

        third = self._write(agent, "three.csv", "x;9;s\ny;2;q\nz;5;r\n")
        fourth = self._write(agent, "four.csv", "a;7;f\nb;1;e\n")
        goal = "sort the rows by the third column, semicolon separated"
        new = [
            ("three.csv", self._sorted_by(third, ";", 3)),
            ("four.csv", self._sorted_by(fourth, ";", 3)),
        ]
        self.assertNotEqual(new[0][1], third)
        outcome = agent.acquire(goal, new)
        self.assertTrue(outcome["learned"], outcome)
        self.assertEqual(outcome["stages"], ["sort -k 3 -t ';'"], outcome)
        # Six processes: two fingerprints, two proofs, and the admission run.
        self.assertLessEqual(outcome["commands_run"], 8, outcome)
        held = self._write(agent, "held.csv", "m;3;w\nn;8;u\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "held.csv"})["stdout"],
            self._sorted_by(held, ";", 3),
        )

    def test_the_same_sentence_on_different_data_rebinds_its_arguments(self) -> None:
        # The words are the same; the data is not.  A mechanism memorised for
        # comma-separated rows must be re-armed with the separator this file
        # actually uses -- reusing the old arguments verbatim would sort the
        # whole line instead of the second column.
        agent = self._agent()
        first = self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        second = self._write(agent, "two.csv", "zulu,5\nyankee,3\n")
        agent.acquire(
            "sort the rows by the second column, comma separated",
            [
                ("one.csv", self._sorted_by(first, ",", 2)),
                ("two.csv", self._sorted_by(second, ",", 2)),
            ],
        )
        space_one = self._write(agent, "s1.txt", "pear 2\napple 10\nfig 1\n")
        space_two = self._write(agent, "s2.txt", "zulu 5\nyankee 3\n")
        goal = "sort the rows by the second column"
        outcome = agent.acquire(
            goal,
            [
                ("s1.txt", self._sorted_by(space_one, " ", 2)),
                ("s2.txt", self._sorted_by(space_two, " ", 2)),
            ],
        )
        self.assertEqual(outcome["stages"], ["sort -k 2 -t ' '"], outcome)
        held = self._write(agent, "h.txt", "m 4\nb 2\nz 8\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "h.txt"})["stdout"],
            self._sorted_by(held, " ", 2),
        )
        self.assertLessEqual(outcome["commands_run"], 8, outcome)

    def test_the_rows_the_sentence_selects_are_selected_before_the_ordering(self) -> None:
        # "Take the first four rows, then sort them" is not "sort everything
        # and keep four": the fifth row has the smallest key, so the wrong
        # reading puts it first and the right one never sees it.
        agent = self._agent()
        first = self._write(
            agent, "one.csv", "kiwi,4\napple,2\nfig,3\npear,1\nzebra,0\n"
        )
        second = self._write(agent, "two.csv", "b,3\na,1\nc,2\nd,4\ne,0\n")
        goal = "take the first four rows, sort them by the second column, comma separated"
        prefix = lambda text: self._sorted_by(  # noqa: E731
            "\n".join(text.splitlines()[:4]) + "\n", ",", 2
        )
        self.assertNotEqual(prefix(first), self._sorted_by(first, ",", 2))
        outcome = agent.acquire(goal, [("one.csv", prefix(first)), ("two.csv", prefix(second))])
        self.assertEqual(outcome["stages"], ["head -n 4", "sort -k 2 -t ,"], outcome)
        held = self._write(agent, "held.csv", "m,9\nb,3\nz,8\na,1\nq,0\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "held.csv"})["stdout"], prefix(held)
        )

    def test_an_earned_mechanism_serves_a_new_request_and_survives_a_restart(self) -> None:
        # The stage learned for one request must be part of the vocabulary for
        # the next one, and it must still be there after the process ends.
        # Without the earned stage this request costs a search over the
        # machine's documentation; with it, a handful of processes.
        agent = self._agent()
        first = self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        second = self._write(agent, "two.csv", "zulu,5\nyankee,3\n")
        agent.acquire(
            "sort the rows by the second column, comma separated",
            [
                ("one.csv", self._sorted_by(first, ",", 2)),
                ("two.csv", self._sorted_by(second, ",", 2)),
            ],
        )
        goal = "keep the last two rows of the table sorted by the second column, comma separated"
        third = self._write(agent, "three.csv", "m,4\nb,2\nz,8\na,1\n")
        fourth = self._write(agent, "four.csv", "q,7\nc,3\nr,9\n")
        tail_two = lambda text: "".join(  # noqa: E731
            line + "\n" for line in self._sorted_by(text, ",", 2).splitlines()[-2:]
        )
        self.assertNotEqual(tail_two(third), self._sorted_by(third, ",", 2))
        outcome = agent.acquire(goal, [("three.csv", tail_two(third)), ("four.csv", tail_two(fourth))])
        self.assertEqual(outcome["stages"], ["sort -k 2 -t ,", "tail -n 2"], outcome)
        self.assertLessEqual(outcome["commands_run"], 12, outcome)

        payload = json.loads(json.dumps(agent.snapshot()))
        restarted = self._agent()
        restarted.restore(payload)
        later = "keep the last one row of the table sorted by the second column, comma separated"
        fifth = self._write(restarted, "five.csv", "k,5\nf,2\ns,9\n")
        sixth = self._write(restarted, "six.csv", "d,8\nc,4\n")
        examples = [
            (name, self._sorted_by(text, ",", 2).splitlines()[-1] + "\n")
            for name, text in (("five.csv", fifth), ("six.csv", sixth))
        ]
        self.assertNotEqual(examples[0][1], fifth)
        again = restarted.acquire(later, examples)
        self.assertEqual(again["stdout"], examples[0][1])
        self.assertLessEqual(again["commands_run"], 12, again)

    def test_where_the_selection_happens_is_part_of_the_request(self) -> None:
        # "Take the first four rows, then sort them" and "sort them all, then
        # keep four" agree on five-row files and disagree on the file below.
        # The sentence says which: a take-verb is a prefix, a keep-verb is a
        # suffix.  Both must be verifiable and they must not be interchangeable.
        agent = self._agent()
        self._write(
            agent, "a.csv", "nine,9\nthree,3\nseven,7\ntwo,2\nfive,5\none,1\nfour,4\n"
        )
        self._write(agent, "b.csv", "delta,4\nalpha,1\ncharlie,3\nbravo,2\necho,5\n")
        goal = "take the first four rows, sort them by the second column, comma separated"
        outcome = agent.acquire(
            goal,
            [
                ("a.csv", "two,2\nthree,3\nseven,7\nnine,9\n"),
                ("b.csv", "alpha,1\nbravo,2\ncharlie,3\ndelta,4\n"),
            ],
        )
        self.assertEqual(outcome["prefix"], "head -n 4", outcome)
        self.assertEqual(outcome["stages"], ["head -n 4", "sort -k 2 -t ,"])
        # a file where the two readings give different answers
        self._write(agent, "held.csv", "e,5\nd,4\nc,3\nb,2\na,1\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "held.csv"})["stdout"],
            "b,2\nc,3\nd,4\ne,5\n",  # the first four rows, sorted -- not a,1 ... d,4
        )

    def test_an_earned_stage_serves_a_different_request(self) -> None:
        # Once a documented invocation has been verified, it is a word in the
        # grammar, not a one-off answer.  A request of a different kind can then
        # be composed from it, and the earned word survives a snapshot: the
        # reborn creature rebuilds the stage by asking the machine again.
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        self._write(agent, "two.csv", "zulu,5\nyankee,3\nxray,9\n")
        agent.acquire(
            "sort the rows by the second column, comma separated",
            [
                ("one.csv", "fig,1\napple,10\npear,2\nkiwi,7\n"),
                ("two.csv", "yankee,3\nzulu,5\nxray,9\n"),
            ],
        )
        self.assertIn("sort -k 2 -t ,", agent._learned)

        self._write(agent, "three.csv", "m,4\nb,2\nz,8\n")
        self._write(agent, "four.csv", "t,9\nk,1\np,5\n")
        goal = "keep the last two rows of the table sorted by the second column, comma separated"
        outcome = agent.acquire(
            goal,
            [("three.csv", "m,4\nz,8\n"), ("four.csv", "p,5\nt,9\n")],
        )
        self.assertEqual(outcome["stages"], ["sort -k 2 -t ,", "tail -n 2"])
        self.assertLessEqual(outcome["commands_run"], 12)
        # text order on the key: 1, 3, 7 -- the tool's own semantics, which the
        # examples pinned, not an assumption about numbers
        self._write(agent, "held.csv", "q,7\na,3\nw,1\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "held.csv"})["stdout"], "a,3\nq,7\n"
        )

        payload = json.loads(json.dumps(agent.snapshot()))
        reborn = LivingAgent(self.root)
        reborn.restore(payload)
        self.assertIn("sort -k 2 -t ,", reborn._learned)
        # a kind of request the reborn creature has never answered
        self._write(reborn, "five.csv", "w,6\nc,2\nd,9\n")
        self._write(reborn, "six.csv", "n,3\ne,1\nf,8\n")
        fresh = reborn.acquire(
            "keep the last one row of the table sorted by the second column, comma separated",
            [("five.csv", "d,9\n"), ("six.csv", "f,8\n")],
        )
        self.assertEqual(fresh["stages"], ["sort -k 2 -t ,", "tail -n 1"])
        self.assertLessEqual(fresh["commands_run"], 16)
        self.assertEqual(fresh["stdout"], "d,9\n")

    def test_a_composition_is_kept_across_a_snapshot(self) -> None:
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        self._write(agent, "two.csv", "zulu,5\nyankee,3\nxray,9\n")
        goal = "sort the rows by the second column, comma separated, and keep the first two"
        agent.acquire(
            goal,
            [("one.csv", "fig,1\napple,10\n"), ("two.csv", "yankee,3\nzulu,5\n")],
        )
        payload = json.loads(json.dumps(agent.snapshot()))
        reborn = LivingAgent(self.root)
        reborn.restore(payload)
        self._write(reborn, "fresh.csv", "beta,6\nalpha,2\ngamma,8\n")
        result = reborn.solve(goal, bindings={"path": "fresh.csv"})
        self.assertEqual(result["stdout"], "alpha,2\nbeta,6\n")

    def test_an_overfit_pipeline_is_not_admitted(self) -> None:
        # A pipeline of fixed-count stages can reproduce two examples by luck.
        # The grammar no longer contains magic counts for exactly this reason,
        # and what is admitted must be the mechanism the request names -- here
        # the keyed sort -- which then has to work on a table it never saw.
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\nkiwi,7\n")
        self._write(agent, "two.csv", "zulu,5\nyankee,3\nxray,9\n")
        outcome = agent.acquire(
            "sort the rows by the second column, comma separated, and keep the first two",
            [("one.csv", "fig,1\napple,10\n"), ("two.csv", "yankee,3\nzulu,5\n")],
        )
        self.assertIn("-k", outcome["argv"])
        self.assertNotIn("tail -n +2", outcome["stages"])
        for index, text in enumerate(
            ("mule,4\nokapi,9\nzebra,1\nemu,6\n", "w,2\nv,8\nu,5\nt,1\ns,9\n")
        ):
            self._write(agent, f"held{index}.csv", text)
            rows = [line.split(",") for line in text.strip().split("\n")]
            ordered = [row for row in sorted(rows, key=lambda row: row[1])][:2]
            want = "".join(f"{row[0]},{row[1]}\n" for row in ordered)
            result = agent.solve(
                "sort the rows by the second column, comma separated, and keep the first two",
                bindings={"path": f"held{index}.csv"},
            )
            self.assertEqual(result["stdout"], want)

    def test_a_width_comes_from_the_request_not_from_a_constant(self) -> None:
        narrow = self._agent()
        text = "the quick brown fox jumps over the lazy dog and keeps running far past" + "\n"
        self._write(narrow, "a.txt", text)
        self._write(narrow, "b.txt", "a second line long enough to need wrapping twice over" + "\n")
        first = narrow.acquire(
            "fold each line at 40 characters",
            [("a.txt", self._fold(text, 40)), ("b.txt", self._fold(self._fold_source("b.txt", narrow), 40))],
        )
        self.assertEqual(first["tool"], "fold")
        self.assertEqual(first["argv"], ["-w", "40"])
        self.assertEqual(first["stdout"], self._fold(text, 40))
        # the same creature, a different width in the request, on another file
        self._write(narrow, "c.txt", "short\n")
        second = narrow.acquire(
            "fold each line at 12 characters",
            [("c.txt", self._fold("short\n", 12)), ("a.txt", self._fold(text, 12))],
        )
        self.assertEqual(second["argv"], ["-w", "12"])
        self.assertEqual(second["stdout"], self._fold("short\n", 12))

    def _fold_source(self, name: str, agent: LivingAgent) -> str:
        return agent.computer.read(name)

    def test_numbering_is_learned_and_a_layout_it_cannot_express_is_refused(self) -> None:
        agent = self._agent()
        text = "alpha\nbeta\ngamma\n"
        other = "one\ntwo\nthree\nfour\n"
        self._write(agent, "n1.txt", text)
        self._write(agent, "n2.txt", other)

        def numbered(source: str) -> str:
            return "".join(
                "%6d\t%s\n" % (index, line)
                for index, line in enumerate(source.split(), start=1)
            )

        outcome = agent.acquire(
            "number the lines", [("n1.txt", numbered(text)), ("n2.txt", numbered(other))]
        )
        self.assertEqual(outcome["tool"], "nl")
        self.assertEqual(outcome["stdout"], numbered(text))
        # The layout is part of the reading, so no demonstration is needed for
        # a second creature: the goal alone fixes the bytes and the machine is
        # asked for a mechanism that produces them.
        blind = self._agent()
        self._write(blind, "n1.txt", text)
        found = blind.fulfil("number the lines of n1.txt", "n1.txt")
        self.assertEqual(found["stdout"], numbered(text))
        # What the reading cannot express is refused, not approximated: the
        # same words with "roman numerals" are not answered in Arabic digits.
        for goal in (
            "number the lines of n1.txt in roman numerals",
            "sort the lines of n1.txt in descending order",
        ):
            with self.assertRaises(AgentError) as raised:
                blind.fulfil(goal, "n1.txt")
            self.assertEqual(str(raised.exception), "GOAL_NOT_VERIFIABLE")
        self.assertIn("number the lines of n1.txt in roman numerals", blind.open_questions())

    def test_a_documented_flag_that_is_not_implemented_is_rejected(self) -> None:
        # A tool that documents ``-w, --width=WIDTH`` and ignores it.  It is
        # first on PATH, so it *is* the mechanism the creature would reach for;
        # believing its help text would produce a skill that silently does
        # nothing.  The bytes decide, and the request fails instead.
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        liar = bin_dir / "fold"
        liar.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "--help" ]; then\n'
            "  echo 'Usage: fold [OPTION]... [FILE]...'\n"
            "  echo\n"
            "  echo 'Wrap each line of the file at a given width.'\n"
            "  echo '  -w, --width=WIDTH  wrap at WIDTH columns'\n"
            "  exit 0\n"
            "fi\n"
            'for last; do :; done\n'
            'cat "$last"\n',
            encoding="utf-8",
        )
        liar.chmod(0o755)
        agent = self._agent(bin_dir=bin_dir)
        text = "a line that is definitely longer than forty characters in total" + "\n"
        self._write(agent, "a.txt", text)
        self._write(agent, "b.txt", "another line that also runs past forty characters easily" + "\n")
        with self.assertRaises(AgentError) as raised:
            agent.acquire(
                "fold each line at 40 characters",
                [
                    ("a.txt", self._fold(text, 40)),
                    ("b.txt", self._fold(agent.computer.read("b.txt"), 40)),
                ],
            )
        self.assertIn(
            str(raised.exception), {"NO_PIPELINE_WITHIN_BUDGET", "NO_VERIFIED_PIPELINE"}
        )
        rejected = [row for row in agent.discovery_log if row["tool"] == "fold"]
        self.assertTrue(rejected, "the liar was never even tried")
        self.assertTrue(all(row["verified"] is False for row in rejected))
        self.assertIn(["-w", "40"], [row["argv"] for row in rejected])
        self.assertEqual(agent.skills, {})
        self.assertNotIn("fold", agent.computer.admitted())

    def test_a_rejected_candidate_leaves_no_authority_behind(self) -> None:
        agent = self._agent()
        self._write(agent, "one.csv", "pear,2\napple,10\nfig,1\n")
        self._write(agent, "two.csv", "kiwi,7\nbanana,3\ncherry,12\n")
        before = set(agent.computer.admitted())
        agent.acquire(
            "sort the rows by the second column, comma separated",
            [
                ("one.csv", "fig,1\napple,10\npear,2\n"),
                ("two.csv", "cherry,12\nbanana,3\nkiwi,7\n"),
            ],
        )
        attempted = {row["tool"] for row in agent.discovery_log}
        rejected = {row["tool"] for row in agent.discovery_log if not row["verified"]}
        # The record always names the winner.  Whether anything was rejected
        # before it depends on where the winner sat in evidence order -- the
        # search stops at the first confirmed pipeline -- so the invariant is
        # checked on whatever was rejected rather than assuming there was one.
        self.assertIn("sort", attempted)
        self.assertTrue(rejected <= attempted)
        # a candidate that failed leaves no new authority behind: only what was
        # already admitted before the search can still be admitted after it
        self.assertEqual(rejected & (set(agent.computer.admitted()) - before), set())

    def test_a_documented_value_vocabulary_is_read_not_guessed(self) -> None:
        # `nl` numbers only non-empty lines by default.  Numbering the blank
        # ones needs `-b a`, and the only place on this machine that says "a
        # means number all lines" is nl's own help text.
        agent = self._agent()
        first = "alpha\n\nbeta\ngamma\n"
        second = "one\n\ntwo\n\nthree\n"
        self._write(agent, "b1.txt", first)
        self._write(agent, "b2.txt", second)

        def all_lines(text: str) -> str:
            return "".join(
                "%6d\t%s\n" % (index, line)
                for index, line in enumerate(text.split("\n")[:-1], start=1)
            )

        outcome = agent.acquire(
            "number the lines", [("b1.txt", all_lines(first)), ("b2.txt", all_lines(second))]
        )
        self.assertEqual(outcome["tool"], "nl")
        self.assertEqual(outcome["argv"], ["-b", "a"])
        self.assertEqual(outcome["stdout"], all_lines(first))

    def test_a_translation_learns_its_direction_from_the_sentence(self) -> None:
        # `tr STRING1 STRING2` is not an option and appears nowhere in tr's
        # help except its usage line, so both the mechanism and the *order* of
        # its operands have to be read rather than guessed.  Two requests that
        # differ only in which character comes first must learn opposite
        # commands, and each must be right on a file neither saw.
        forward = self._agent()
        self._write(forward, "f1.txt", "a,b,c\n")
        self._write(forward, "f2.txt", "x,y\n")
        first = forward.acquire(
            "replace every comma with a semicolon",
            [("f1.txt", "a;b;c\n"), ("f2.txt", "x;y\n")],
        )
        self.assertEqual(first["stages"], ["tr , ';'"])
        self.assertLessEqual(first["commands_run"], 6)

        backward = self._agent()
        self._write(backward, "g1.txt", "a;b;c\n")
        self._write(backward, "g2.txt", "x;y\n")
        second = backward.acquire(
            "replace every semicolon with a comma",
            [("g1.txt", "a,b,c\n"), ("g2.txt", "x,y\n")],
        )
        self.assertEqual(second["stages"], ["tr ';' ,"])
        self.assertLessEqual(second["commands_run"], 6)
        self.assertNotEqual(first["stages"], second["stages"])

        # Held out from both searches, and written so that neither answer can
        # be produced by the other command.
        self._write(forward, "h.txt", "p,q;r\n")
        self.assertEqual(
            forward.solve("replace every comma with a semicolon", bindings={"path": "h.txt"})[
                "stdout"
            ],
            "p;q;r\n",
        )
        self._write(backward, "h.txt", "p,q;r\n")
        self.assertEqual(
            backward.solve("replace every semicolon with a comma", bindings={"path": "h.txt"})[
                "stdout"
            ],
            "p,q,r\n",
        )

    def test_a_positional_operand_comes_from_the_usage_line(self) -> None:
        # A filter's pattern is not an option either: `grep [OPTION]... PATTERNS
        # [FILE]...` is the only place on the machine that says grep consumes a
        # pattern, and the sentence is the only place that says which one.  The
        # command must select by the word the request names and nothing else.
        agent = self._agent()
        self._write(agent, "one.txt", "ok\nboom error here\nfine\n")
        self._write(agent, "two.txt", "error\nx\n")
        goal = "show only the lines that contain error"
        outcome = agent.acquire(
            goal, [("one.txt", "boom error here\n"), ("two.txt", "error\n")]
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertLessEqual(outcome["commands_run"], 14)
        self.assertIn("error", " ".join(outcome["stages"]))
        # Held out: the word appears in the middle of a line, and a file with no
        # such line must produce nothing rather than everything.
        self._write(agent, "h1.txt", "fine\nan error at noon\nok\n")
        self._write(agent, "h2.txt", "all good\n")
        self.assertEqual(agent.solve(goal, bindings={"path": "h1.txt"})["stdout"], "an error at noon\n")
        self.assertEqual(agent.solve(goal, bindings={"path": "h2.txt"})["stdout"], "")

    def test_a_selection_must_use_the_word_it_names(self) -> None:
        # `tail -n +2` reproduces both examples because the word happens to sit
        # on the second line of each file.  The sentence says what the answer is
        # for *any* text -- the lines containing that word -- so the claim can
        # be checked on a text the examples never contained, and a positional
        # stand-in is refused.  A second request of the same kind must then be
        # answered from memory in a fraction of the first search.
        agent = self._agent()
        self._write(agent, "g1.txt", "ok\nerror\n")
        self._write(agent, "g2.txt", "fine\nerror\n")
        goal = "show only the lines that contain error"
        first = agent.acquire(goal, [("g1.txt", "error\n"), ("g2.txt", "error\n")])
        self.assertEqual(first["status"], "PASS", first)
        self.assertLessEqual(first["commands_run"], 16)
        self.assertIn("error", " ".join(first["stages"]))
        self.assertNotIn("tail", first["stages"][0])
        self._write(agent, "h1.txt", "early error\nok\nlater error\n")
        self._write(agent, "h2.txt", "nothing at all\n")
        self.assertEqual(
            agent.solve(goal, bindings={"path": "h1.txt"})["stdout"],
            "early error\nlater error\n",
        )
        self.assertEqual(agent.solve(goal, bindings={"path": "h2.txt"})["stdout"], "")

        self._write(agent, "w1.txt", "ok\nwarning here\n")
        self._write(agent, "w2.txt", "warning\n")
        second = agent.acquire(
            "show only the lines that contain warning",
            [("w1.txt", "warning here\n"), ("w2.txt", "warning\n")],
        )
        self.assertIn("warning", " ".join(second["stages"]))
        # The second request is answered immediately -- no more than a handful
        # of real commands, and no slower than the first.  On this family the
        # sentence names the pattern, so the first request is already a
        # shortcut; what the second one must not do is search again.
        self.assertLessEqual(second["commands_run"], 4)
        self.assertLessEqual(second["commands_run"], first["commands_run"])
        self._write(agent, "h3.txt", "a warning first\nok\n")
        self.assertEqual(
            agent.solve("show only the lines that contain warning", bindings={"path": "h3.txt"})[
                "stdout"
            ],
            "a warning first\n",
        )

    def test_the_examples_can_state_the_manner_the_sentence_omits(self) -> None:
        # The sentence says only "by the second column".  The shown answer says
        # 1, 2, 10 -- which no lexical order produces -- so the numeric reading
        # is demonstrated, not assumed.  The opposite demonstration must not
        # inherit it: the same words over the same shape of data with a lexical
        # answer must learn the plain sort.
        numeric = self._agent()
        self._write(numeric, "n1.csv", "a,10\nb,2\nc,1\n")
        self._write(numeric, "n2.csv", "d,20\ne,3\n")
        goal = "sort the rows by the second column"
        learned = numeric.acquire(
            goal, [("n1.csv", "c,1\nb,2\na,10\n"), ("n2.csv", "e,3\nd,20\n")]
        )
        self.assertLessEqual(learned["commands_run"], 18)
        # 100, 9 and 8: numeric order is the reverse of file order and of text
        # order, so only a numeric key produces this answer.
        self._write(numeric, "h.csv", "p,100\nq,9\nr,8\n")
        self.assertEqual(
            numeric.solve(goal, bindings={"path": "h.csv"})["stdout"], "r,8\nq,9\np,100\n"
        )

        lexical = self._agent()
        self._write(lexical, "m1.csv", "a,10\nb,9\nc,8\n")
        self._write(lexical, "m2.csv", "d,7\ne,6\n")
        plain = lexical.acquire(
            goal, [("m1.csv", "a,10\nc,8\nb,9\n"), ("m2.csv", "e,6\nd,7\n")]
        )
        self.assertNotIn("-g", plain["argv"])
        self.assertNotIn("-n", plain["argv"])
        # text order, held out: "20" sorts before "7" lexically and after it
        # numerically, so this answer identifies which reading was kept.
        self._write(lexical, "h.csv", "m,7\nn,20\no,3\n")
        self.assertEqual(
            lexical.solve(goal, bindings={"path": "h.csv"})["stdout"], "n,20\no,3\nm,7\n"
        )

    def test_an_answer_that_depends_on_row_order_is_not_an_ordering(self) -> None:
        # `sort -k 2 -t , | sort -r` reproduces "1, 2, 10" by reversing a
        # lexical sort, and on the two examples that is indistinguishable from
        # the numeric answer.  The question that separates them is what happens
        # when the same values arrive on different rows; a second real command
        # shows the same question answered the other way, so the check is a
        # measurement and not a constant.
        agent = self._agent()
        first = "a,10\nb,2\nc,1\n"
        self._write(agent, "q1.csv", first)
        self._write(agent, "q2.csv", "d,20\ne,3\n")
        examples = [("q1.csv", "c,1\nb,2\na,10\n"), ("q2.csv", "e,3\nd,20\n")]
        goal = "sort the rows by the second column"
        self.assertFalse(agent._order_holds_on_a_fresh_permutation(goal, ["sort -k 2 -t ,", "sort -r"], examples))
        true_sort = agent._order_holds_on_a_fresh_permutation(goal, ["sort -k 2 -t , -g"], examples)
        self.assertIsNot(true_sort, False)

    def test_a_stated_manner_is_implemented_not_merely_not_contradicted(self) -> None:
        # "numerically" is a specification, not decoration.  On these files the
        # lexical order (1, 10, 2) and the numeric order (1, 2, 10) disagree, so
        # a sort that ignores the word answers a different question -- and a
        # search that stopped at the first fitting pipeline used to admit one.
        # The option that implements the word is `-n`, and the only place that
        # connection exists is sort's own help text.
        agent = self._agent()
        first = "a,10\nb,2\nc,1\n"
        second = "d,20\ne,3\n"
        self._write(agent, "n1.csv", first)
        self._write(agent, "n2.csv", second)
        goal = "sort the rows by the second column numerically, comma separated"
        outcome = agent.acquire(
            goal, [("n1.csv", "c,1\nb,2\na,10\n"), ("n2.csv", "e,3\nd,20\n")]
        )
        self.assertNotIn("sort -r", outcome["stages"])
        self.assertLessEqual(outcome["commands_run"], 16)
        # Held-out data the search never saw, with an order that no accidental
        # coincidence can reproduce: 3, 20, 100 is neither the file order nor
        # the lexical order.
        self._write(agent, "n3.csv", "x,100\ny,20\nz,3\n")
        answer = agent.solve(goal, bindings={"path": "n3.csv"})
        self.assertEqual(answer["stdout"], "z,3\ny,20\nx,100\n")
        # The option is load-bearing: remove it and the same command gives the
        # text order, which is exactly what the sentence ruled out.
        bare = answer["command"].replace(" -g", "").replace(" -n", "")
        self.assertNotEqual(agent.computer.run(bare).stdout, answer["stdout"])
        self.assertEqual(agent.computer.run(bare).stdout, "x,100\ny,20\nz,3\n")

        # The same request without the manner adverb must not smuggle the
        # option in: the word is what justified it.
        plain_agent = self._agent()
        self._write(plain_agent, "p1.csv", "a,10\nb,9\nc,8\n")
        self._write(plain_agent, "p2.csv", "d,20\ne,3\n")
        plain = plain_agent.acquire(
            "sort the rows by the second column, comma separated",
            [("p1.csv", "a,10\nc,8\nb,9\n"), ("p2.csv", "d,20\ne,3\n")],
        )
        # text order, which is what the examples show and all the sentence says
        self.assertNotIn("-n", plain["argv"])
        self.assertNotIn("-g", plain["argv"])
        self._write(plain_agent, "p3.csv", "m,7\nn,20\no,3\n")
        self.assertEqual(
            plain_agent.solve(
                "sort the rows by the second column, comma separated",
                bindings={"path": "p3.csv"},
            )["stdout"],
            "n,20\no,3\nm,7\n",
        )

    def test_a_failed_acquisition_is_a_remembered_gap_one_word_closes(self) -> None:
        # Neither the pipeline vocabulary nor anything the machine documents
        # can produce these bytes.  The failure is not a dead end: it records
        # what was asked, what was tried and why it stopped, and a single
        # demonstration is enough to close the gap.
        agent = self._agent()
        self._write(agent, "x.txt", "a\nb\n")
        self._write(agent, "y.txt", "c\nd\n")
        goal = "transmogrify each line into its opposite"
        with self.assertRaises(AgentError) as raised:
            agent.acquire(goal, [("x.txt", "x\ny\n"), ("y.txt", "z\nw\n")])
        self.assertEqual(str(raised.exception), "NO_PIPELINE_WITHIN_BUDGET")
        self.assertIn(goal, agent.open_questions())
        gap = [entry.payload for entry in agent.memory.active() if entry.payload.get("goal") == goal]
        self.assertEqual(gap[0]["reason"], "no_verified_mechanism")
        self.assertEqual(gap[0]["examples"], ["x.txt", "y.txt"])
        self.assertTrue(gap[0]["tools_tried"])
        agent.learn_shell_skill(
            goal,
            "tr 'abcd' 'xyzw' < x.txt",
            {"path": "x.txt"},
            canary=({"x.txt": "a\nb\n"}, "x\ny\n"),
        )
        self.assertNotIn(goal, agent.open_questions())
        self.assertEqual(agent.solve(goal, bindings={"path": "y.txt"})["stdout"], "z\nw\n")

    def test_reading_a_strangers_help_cannot_touch_the_tree(self) -> None:
        # `tool --help` is still running a stranger's code.  A real scan left
        # `gz*` files in the repository root because some installed tool writes
        # beside its working directory even when asked to describe itself.
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        chatty = bin_dir / "chatty"
        chatty.write_text(
            "#!/bin/sh\n"
            'touch "./leak-$PPID.txt" "$HOME/leak-home.txt"\n'
            "echo 'Usage: chatty [FILE]'\n"
            "echo\n"
            "echo 'Copy the file, writing a note beside it.'\n",
            encoding="utf-8",
        )
        chatty.chmod(0o755)
        agent = self._agent(bin_dir=bin_dir)
        before = sorted(path.name for path in self.root.iterdir())
        repo_before = sorted(path.name for path in Path.cwd().iterdir())
        docs = agent.vocabulary.read()
        self.assertTrue(docs)
        self.assertIsNotNone(agent.vocabulary.doc("chatty"))
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), before)
        self.assertEqual(sorted(path.name for path in Path.cwd().iterdir()), repo_before)
        self.assertEqual(list(Path.cwd().glob("leak-*")), [])
        self.assertEqual(list(Path(tempfile.gettempdir()).glob("brain-help-*")), [])

    def test_parsed_options_survive_the_documentation_cache(self) -> None:
        agent = self._agent()
        docs = agent.vocabulary.read()
        self.assertTrue(docs)
        doc = agent.vocabulary.doc("sort")
        self.assertIsNotNone(doc)
        keys = {(option.short, option.argument) for option in doc.options}
        self.assertIn(("-k", "KEYDEF"), keys)
        self.assertIn(("-t", "SEP"), keys)
        again = discovery.ToolDoc.from_dict(json.loads(json.dumps(doc.to_dict())))
        self.assertEqual(again.options, doc.options)


class IntentWithoutExamplesTests(unittest.TestCase):
    """Goals whose success is checkable from the result, with no example."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = LivingAgent(self.root)
        self.real_files = [
            ROOT / "canonical" / "runtime" / "living_core_v1.py",
            ROOT / "canonical" / "runtime" / "living_agent_v1.py",
            ROOT / "canonical" / "governance" / "REPO_INTEGRITY_POLICY_V1.json",
        ]

    def _copy(self, source: Path, name: str) -> str:
        text = source.read_text(encoding="utf-8")
        self.agent.computer.write(name, text)
        return text

    def test_sort_lines_of_a_real_repository_file(self) -> None:
        text = self._copy(self.real_files[0], "doc.txt")
        outcome = self.agent.fulfil("sort the lines of 'doc.txt'", "doc.txt")
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["properties"], ["sorted"])
        self.assertLess(outcome["probe_seconds"], 0.5)
        self.assertLess(outcome["seconds"], 2.0)
        want = sorted_text(text)
        self.assertEqual(outcome["stdout"], want)
        # the same skill, applied to other real files through the goal alone
        for index, source in enumerate(self.real_files[1:], start=1):
            with self.subTest(source=source.name):
                fresh = self._copy(source, f"doc{index}.txt")
                result = self.agent.solve(f"sort the lines of 'doc{index}.txt'")
                self.assertEqual(result["status"], "PASS", result)
                self.assertEqual(result["stdout"], sorted_text(fresh))

    def test_count_lines_of_real_files(self) -> None:
        text = self._copy(self.real_files[1], "doc.txt")
        outcome = self.agent.fulfil("count how many lines are in 'doc.txt'", "doc.txt")
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(int(outcome["stdout"]), len(shell_lines(text)))
        for index, source in enumerate(self.real_files, start=1):
            with self.subTest(source=source.name):
                fresh = self._copy(source, f"lines{index}.txt")
                result = self.agent.solve(f"count how many lines are in 'lines{index}.txt'")
                self.assertEqual(int(result["stdout"]), len(shell_lines(fresh)))

    def test_lowercase_a_real_file(self) -> None:
        text = self._copy(self.real_files[2], "policy.json")
        outcome = self.agent.fulfil("lowercase the text in 'policy.json'", "policy.json")
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["stdout"], text.lower())

    def test_unique_words_on_a_real_policy_file(self) -> None:
        source = self.real_files[2]
        text = self._copy(source, "policy.json")
        self.assertNotIn("\t", text)
        outcome = self.agent.fulfil("list the unique words in 'policy.json'", "policy.json")
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["properties"], ["unique", "words"])
        want = "\n".join(sorted(set(text.split()))) + "\n"
        self.assertEqual(outcome["stdout"], want)
        self.assertLess(outcome["seconds"], 1.5)

    def test_distinct_word_count_on_a_real_policy_file(self) -> None:
        text = self._copy(self.real_files[2], "policy.json")
        self.assertNotIn("\t", text)
        outcome = self.agent.fulfil(
            "count how many distinct words are in 'policy.json'", "policy.json"
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(int(outcome["stdout"]), len(set(text.split())))
        self.assertLessEqual(len(outcome["stages"]), 4)

    def test_unique_words_generalize_as_a_verified_property(self) -> None:
        self._copy(self.real_files[2], "policy.json")
        self.agent.fulfil("list the unique words in 'policy.json'", "policy.json")
        for index, source in enumerate(
            (
                ROOT / "canonical" / "governance" / "REPO_INTEGRITY_POLICY_V1.json",
                ROOT / "canonical" / "CANONICAL_POINTER.json",
            ),
            start=1,
        ):
            text = self._copy(source, f"policy{index}.json")
            self.assertNotIn("\t", text)
            with self.subTest(source=source.name):
                result = self.agent.solve(f"list the unique words in 'policy{index}.json'")
                self.assertEqual(result["status"], "PASS", result)
                produced = result["stdout"].split()
                self.assertEqual(produced, sorted(set(produced)))
                self.assertEqual(set(produced), set(text.split()))

    def test_unverifiable_goal_fails_closed(self) -> None:
        self._copy(self.real_files[0], "doc.txt")
        with self.assertRaises(AgentError) as raised:
            self.agent.fulfil("make 'doc.txt' nicer", "doc.txt")
        self.assertEqual(str(raised.exception), "GOAL_NOT_VERIFIABLE")

    def test_unique_lines_keep_the_first_occurrence_in_place(self) -> None:
        # "remove the duplicates" has an exact answer: first occurrence stays,
        # later repeats go, everything else keeps its position.  Neither
        # `sort -u` (reorders) nor `uniq` (adjacent only) is that function, so
        # the answer has to come from a mechanism that really computes it.
        self._copy(self.real_files[0], "doc.txt")
        source = "gamma\nalpha\ngamma\nbeta\nalpha\ndelta\n"
        self.agent.computer.write("dups.txt", source)
        outcome = self.agent.fulfil("remove the duplicate lines from 'dups.txt'", "dups.txt")
        self.assertEqual(outcome["stdout"], "gamma\nalpha\nbeta\ndelta\n")
        self.assertEqual(outcome["stages"], ["awk '!seen[$0]++'"])
        # a file whose repeats are not adjacent: `uniq` would return it whole
        self.agent.computer.write("other.txt", "z\nq\nz\nz\nm\nq\n")
        result = self.agent.solve("remove the duplicate lines from other.txt")
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["stdout"], "z\nq\nm\n")

    def test_last_occurrence_is_refused_not_approximated(self) -> None:
        # "last occurrence" shares the word 'duplicate' but asks for a
        # different function.  Keeping the first occurrence would be a right
        # answer to the wrong question, so the gap is recorded instead.
        self._copy(self.real_files[0], "doc.txt")
        self.agent.computer.write("dups.txt", "b\na\nb\n")
        goal = "keep the last occurrence of each duplicate line in 'dups.txt'"
        with self.assertRaises(AgentError) as raised:
            self.agent.fulfil(goal, "dups.txt")
        self.assertEqual(str(raised.exception), "GOAL_NOT_VERIFIABLE")
        self.assertIn(goal, self.agent.open_questions())
        recorded = [
            entry.payload
            for entry in self.agent.memory.active()
            if entry.payload.get("goal") == goal
        ]
        # "last" and "occurrence" are exactly what the goal adds beyond
        # "unique lines", and they are what makes the answer different.
        self.assertEqual(recorded[0]["reason"], "unmodelled_qualifier")
        self.assertEqual(recorded[0]["words"], ["last", "occurrence"])
        self.assertEqual(self.agent.computer.read("dups.txt"), "b\na\nb\n")

    def test_property_is_rechecked_at_solve_time(self) -> None:
        self._copy(self.real_files[0], "doc.txt")
        outcome = self.agent.fulfil("sort the lines of 'doc.txt'", "doc.txt")
        skill = self.agent.skills[outcome["skill_id"]]
        self.assertEqual(skill.properties, ["sorted"])
        # sabotage the mechanism while keeping a valid postcondition
        skill.template = "cat {path}"
        sabotaged = self.agent.solve("sort the lines of 'doc.txt'")
        self.assertEqual(sabotaged["status"], "FAIL_CLOSED", sabotaged)


class MemoryScaleTests(unittest.TestCase):
    """Retrieval is exact at scale, and does not scan memory to be exact."""

    @staticmethod
    def _brute_force(memory, query, kind=None, k=5):
        from canonical.runtime.living_core_v1 import _tokens

        tokens = _tokens(query)
        scored = []
        for entry in memory.entries.values():
            if entry.retired:
                continue
            if kind is not None and entry.kind != kind:
                continue
            features = entry.salience_features(memory.clock, tokens, memory.half_life)
            scored.append((memory.model.score(features), entry))
        scored.sort(key=lambda item: (-item[0], item[1].entry_id))
        return scored[:k]

    def _memory(self, size: int, seed: int):
        from canonical.runtime.living_core_v1 import Memory

        rng = random.Random(seed)
        vocabulary = [f"token{i}" for i in range(400)]
        memory = Memory()
        for index in range(size):
            text = " ".join(rng.choice(vocabulary) for _ in range(rng.randint(3, 8)))
            memory.add(
                rng.choice(("skill", "episode", "fact")),
                text,
                {"index": index},
                surprise=rng.random() * 0.6,
                cost_saved=rng.random(),
            )
        for _ in range(size // 20):
            entry = rng.choice(list(memory.entries.values()))
            memory.touch(entry.entry_id, success=rng.random() < 0.8)
        return memory

    def test_ranked_results_equal_a_full_scan(self) -> None:
        memory = self._memory(400, seed=5)
        queries = ["token7 token19 token300", "token1", "token250 token251", "nothing at all"]
        for query in queries:
            for kind in (None, "skill", "episode", "fact"):
                for k in (1, 3, 7):
                    with self.subTest(query=query, kind=kind, k=k):
                        fast = memory.retrieve(query, kind=kind, k=k)
                        slow = self._brute_force(memory, query, kind=kind, k=k)
                        self.assertEqual(
                            [entry.entry_id for _score, entry in fast],
                            [entry.entry_id for _score, entry in slow],
                        )
                        for (fast_score, _), (slow_score, _) in zip(fast, slow):
                            self.assertAlmostEqual(fast_score, slow_score, places=12)

    def test_three_thousand_entries_stay_instant(self) -> None:
        memory = self._memory(3000, seed=6)
        query = "token7 token19 token300 token42"
        memory.retrieve(query, k=8)  # warm the derived index
        started = time.perf_counter()
        for _ in range(300):
            memory.retrieve(query, k=8)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 1.0, f"300 queries took {elapsed:.3f}s")
        self.assertLess(elapsed / 300, 0.0035)

    def test_learned_weights_are_reflected_immediately(self) -> None:
        memory = self._memory(200, seed=7)
        before = [e.entry_id for _s, e in memory.retrieve("token9", k=4)]
        for _ in range(12):
            memory.model.learn(
                {"relevance": 1.0, "recency": 1.0, "surprise": 0.0, "usefulness": 0.5, "cost_saved": 0.0, "bias": 1.0},
                1,
            )
        memory._invalidate()
        after = [e.entry_id for _s, e in memory.retrieve("token9", k=4)]
        self.assertNotEqual(memory.model.weights["relevance"], 1.0)
        self.assertEqual(len(after), len(before))
        self.assertEqual(
            after, [e.entry_id for _s, e in self._brute_force(memory, "token9", k=4)]
        )

    def test_index_is_rebuilt_from_a_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = LivingAgent(Path(tmp))
            agent.computer.write("a.txt", "x\ny\n")
            skill = agent.learn_shell_skill(
                "count the lines in a file",
                "wc -l < a.txt",
                {"path": "a.txt"},
                canary=({"c.txt": "1\n2\n"}, "2"),
                postcondition=r"^[0-9]+$",
            )
            payload = json.loads(json.dumps(agent.snapshot()))
            other = LivingAgent(Path(tmp))
            other.restore(payload)
            ranked = other.memory.retrieve("count lines", kind="skill", k=1)
            self.assertEqual(len(ranked), 1)
            self.assertEqual(ranked[0][1].payload["skill_id"], skill.skill_id)
            self.assertEqual(other.solve("count the lines in 'a.txt'")["status"], "PASS")

    def test_a_restored_solution_is_recalled_in_one_command(self) -> None:
        # Memory is only worth having if it survives the process.  A solution
        # learned by search costs many real commands; the same creature after a
        # restart must recognise the situation and spend exactly one, and its
        # outcome must report the same schema either way -- an instant answer is
        # not allowed to look like an answer that measured nothing.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal = "sort the rows by the second column numerically, comma separated"
            agent = LivingAgent(root)
            agent.computer.write("a1.csv", "a,10\nb,2\nc,1\n")
            agent.computer.write("a2.csv", "d,20\ne,3\n")
            first = agent.acquire(
                goal, [("a1.csv", "c,1\nb,2\na,10\n"), ("a2.csv", "e,3\nd,20\n")]
            )
            self.assertTrue(first["learned"])
            self.assertGreater(first["commands_run"], 1)
            payload = json.loads(json.dumps(agent.snapshot()))

            again = LivingAgent(root)
            again.restore(payload)
            again.computer.write("a3.csv", "x,100\ny,20\nz,3\n")
            again.computer.write("a4.csv", "p,9\nq,8\n")
            second = again.acquire(
                goal, [("a3.csv", "z,3\ny,20\nx,100\n"), ("a4.csv", "q,8\np,9\n")]
            )
            self.assertTrue(second["reused"])
            self.assertFalse(second["learned"])
            self.assertEqual(second["commands_run"], 1)
            self.assertEqual(second["status"], "PASS")
            self.assertEqual(second["stdout"], "z,3\ny,20\nx,100\n")
            self.assertLess(second["commands_run"], first["commands_run"])


def word_soup(seed: int, count: int = 400) -> str:
    vocabulary = (
        "apple banana cherry damson elderberry fig grape honeydew imbe jackfruit kiwi "
        "lemon mango nectarine olive peach quince raspberry satsuma tangerine ugli "
        "vanilla watermelon"
    ).split()
    state = seed
    words = []
    for _ in range(count):
        state = (state * 1103515245 + 12345) % (2**31)
        words.append(vocabulary[state % len(vocabulary)])
    return " ".join(words)


class ParameterisedStageTests(unittest.TestCase):
    """The stage vocabulary is extended by parameters read off the data."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agent = LivingAgent(Path(self.tmp.name))

    def test_pipe_separator_is_discovered_from_the_examples(self) -> None:
        self.agent.computer.write("a.pipe", "alpha|10\nbeta|20\ngamma|30\n")
        self.agent.computer.write("b.pipe", "delta|40\nepsilon|50\n")
        outcome = self.agent.acquire(
            "second column of the pipe report",
            [("a.pipe", "10\n20\n30\n"), ("b.pipe", "40\n50\n")],
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertEqual(outcome["stages"], ["cut -f 2 -d '|'"])
        self.agent.computer.write("fresh.pipe", "zeta|60\neta|70\n")
        result = self.agent.solve("second column of the pipe report: 'fresh.pipe'")
        self.assertEqual(result["stdout"], "60\n70\n")

    def test_line_count_is_discovered_from_the_expected_output(self) -> None:
        source = "\n".join(f"line{i}" for i in range(1, 13)) + "\n"
        other = "\n".join(f"row{i}" for i in range(1, 10)) + "\n"
        self.agent.computer.write("a.txt", source)
        self.agent.computer.write("b.txt", other)
        outcome = self.agent.acquire(
            "the first five lines",
            [("a.txt", "\n".join(source.splitlines()[:5]) + "\n"),
             ("b.txt", "\n".join(other.splitlines()[:5]) + "\n")],
        )
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertIn("head -n 5", outcome["stages"])
        self.agent.computer.write("fresh.txt", "\n".join(f"z{i}" for i in range(1, 9)) + "\n")
        result = self.agent.solve("the first five lines of 'fresh.txt'")
        self.assertEqual(result["stdout"], "z1\nz2\nz3\nz4\nz5\n")

    def test_unknown_separator_is_an_honest_failure(self) -> None:
        self.agent.computer.write("weird.txt", "alpha#10\nbeta#20\n")
        with self.assertRaises(AgentError) as raised:
            self.agent.acquire(
                "second column",
                [("weird.txt", "10\n20\n")],
            )
        self.assertEqual(str(raised.exception), "TOO_FEW_EXAMPLES")


class PolicyLearningTests(unittest.TestCase):
    """The controller that chooses what to do is learned, not written."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.agent = LivingAgent(self.root)
        self.csv_a = benchmark.real_tree_table(ROOT / "canonical" / "laws", pattern="*")
        self.csv_b = benchmark.real_tree_table(ROOT / "canonical" / "capabilities", pattern="*")
        self.agent.computer.write("d1.csv", self.csv_a.to_csv())
        self.agent.computer.write("d2.csv", self.csv_b.to_csv())
        self.agent.computer.write(
            "c1.py", (ROOT / "canonical" / "runtime" / "living_agent_v1.py").read_text(encoding="utf-8")
        )
        self.agent.computer.write(
            "j1.json", (ROOT / "canonical" / "CANONICAL_POINTER.json").read_text(encoding="utf-8")
        )
        self.agent.computer.write("w1.txt", word_soup(1))
        self.agent.computer.write("w2.txt", word_soup(2))

        TOTAL = "total the sizes in '{path}'"
        SORT = "sort the lines of '{path}'"
        WORDS = "count how many distinct words are in '{path}'"

        self.total_goal = TOTAL
        self.sort_goal = SORT
        self.words_goal = WORDS

        self.agent.acquire(
            "total the sizes in the listing",
            [
                ("d1.csv", "%.0f\n" % sum(int(r["size"]) for r in self.csv_a.rows)),
                ("d2.csv", "%.0f\n" % sum(int(r["size"]) for r in self.csv_b.rows)),
            ],
        )
        self.agent.fulfil("sort the lines of 'c1.py'", "c1.py")
        self.agent.fulfil("count how many distinct words are in 'w1.txt'", "w1.txt")

        self.traces = [
            (self.agent.observe("d1.csv"), TOTAL),
            (self.agent.observe("d2.csv"), TOTAL),
            (self.agent.observe("c1.py"), SORT),
            (self.agent.observe("j1.json"), SORT),
            (self.agent.observe("w1.txt"), WORDS),
            (self.agent.observe("w2.txt"), WORDS),
        ]

        held_csv = benchmark.real_tree_table(ROOT / "canonical" / "governance", pattern="*")
        self.agent.computer.write("held.csv", held_csv.to_csv())
        self.held_csv_total = sum(int(r["size"]) for r in held_csv.rows)
        self.agent.computer.write(
            "held.json",
            (ROOT / "canonical" / "verification" / "HONEST_SUITE_BASELINE_20261014_V1.json").read_text(
                encoding="utf-8"
            ),
        )
        self.agent.computer.write("held.py", (ROOT / "canonical" / "runtime" / "living_core_v1.py").read_text(encoding="utf-8"))
        self.agent.computer.write("held.txt", word_soup(9))

    def test_learned_policy_chooses_the_right_action_on_unseen_files(self) -> None:
        policy = self.agent.learn_policy("triage", self.traces)
        self.assertLessEqual(len(policy["rules"]), 3)
        self.assertEqual({rule["action"] for rule in policy["rules"]},
                         {self.total_goal, self.sort_goal, self.words_goal})

        csv_result = self.agent.act(policy["policy_id"], "held.csv")
        self.assertEqual(csv_result["action"], self.total_goal)
        self.assertEqual(csv_result["status"], "PASS", csv_result)
        self.assertEqual(csv_result["stdout"], "%.0f\n" % self.held_csv_total)

        json_text = self.agent.computer.read("held.json")
        json_result = self.agent.act(policy["policy_id"], "held.json")
        self.assertEqual(json_result["action"], self.sort_goal)
        self.assertEqual(json_result["stdout"], sorted_text(json_text))

        words_text = self.agent.computer.read("held.txt")
        words_result = self.agent.act(policy["policy_id"], "held.txt")
        self.assertEqual(words_result["action"], self.words_goal)
        self.assertEqual(int(words_result["stdout"]), len(set(words_text.split())))
        self.assertLess(words_result["seconds"] if "seconds" in words_result else 0.0, 5.0)

    def test_under_taught_policy_flags_the_extrapolation(self) -> None:
        partial = self.agent.learn_policy("partial", self.traces[:4])
        outcome = self.agent.act(partial["policy_id"], "w1.txt")
        self.assertFalse(outcome["covered"])
        self.assertIn("comma", outcome["unseen"])
        self.assertEqual(outcome["unseen"]["comma"], "none")
        self.assertIn("w1.txt", self.agent.open_questions())
        recorded = [
            entry
            for entry in self.agent.memory.active()
            if entry.payload.get("outcome") == "impasse" and entry.payload.get("unseen")
        ]
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0].payload["unseen"]["comma"], "none")
        # one more demonstration closes the gap
        full = self.agent.learn_policy("full", self.traces)
        healed = self.agent.act(full["policy_id"], "held.txt")
        self.assertTrue(healed["covered"], healed)
        self.assertEqual(healed["action"], self.words_goal)

    def test_no_matching_rule_fails_closed(self) -> None:
        from canonical.runtime.living_core_v1 import DecisionList, col, lit

        policy = DecisionList(
            rules=[
                {
                    "action": "never happens",
                    "predicates": [{
                        "op": "filter",
                        "expr": col("comma"),
                        "cmp": "eq",
                        "value": "impossible-value",
                    }],
                }
            ],
            features=["comma"],
        )
        self.agent.policies["D-test"] = policy
        self.agent.policy_evidence["D-test"] = {}
        with self.assertRaises(AgentError) as raised:
            self.agent.act("D-test", "d1.csv")
        self.assertEqual(str(raised.exception), "POLICY_NO_MATCH")

    def test_policy_survives_a_snapshot_round_trip(self) -> None:
        policy = self.agent.learn_policy("triage", self.traces)
        payload = json.loads(json.dumps(self.agent.snapshot()))
        other = LivingAgent(self.root)
        other.restore(payload)
        result = other.act(policy["policy_id"], "held.csv")
        self.assertEqual(result["action"], self.total_goal)
        self.assertEqual(result["stdout"], "%.0f\n" % self.held_csv_total)

    def test_decision_induction_is_deterministic(self) -> None:
        first = self.agent.learn_policy("p1", self.traces)
        second = self.agent.learn_policy("p2", self.traces)
        self.assertEqual(first["rules"], second["rules"])

    def test_under_determined_traces_are_rejected_not_guessed(self) -> None:
        with self.assertRaises(AgentError) as raised:
            self.agent.learn_policy("empty", [])
        self.assertEqual(str(raised.exception), "TRACES_REQUIRED")


class HeldOutBatteryTests(unittest.TestCase):
    """One request per kind, taught on two files, answered on a third.

    Every expected output here is computed by an independent implementation
    written in this file, not by the agent and not by a recorded answer.  The
    file the agent answers on was never shown to it.  This is the check that
    catches a pipeline which fits the two demonstrations and means something
    else: the failure is a wrong byte, not a wrong command line.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _agent(self) -> LivingAgent:
        return LivingAgent(self.root)

    @staticmethod
    def _fields(text: str, separator: str) -> list[list[str]]:
        return [line.split(separator) for line in text.splitlines()]

    @classmethod
    def _sort_rows(cls, text: str, separator: str, position: int, *, numeric: bool = False,
                   descending: bool = False) -> str:
        rows = cls._fields(text, separator)
        key = (lambda row: float(row[position - 1])) if numeric else (lambda row: row[position - 1])
        ordered = sorted(rows, key=key, reverse=descending)
        return "\n".join(separator.join(row) for row in ordered) + "\n"

    def _check(self, goal: str, first: str, second: str, held: str, oracle) -> dict:
        agent = self._agent()
        agent.computer.write("one.dat", first)
        agent.computer.write("two.dat", second)
        outcome = agent.acquire(
            goal, [("one.dat", oracle(first)), ("two.dat", oracle(second))]
        )
        self.assertEqual(outcome["status"], "PASS", (goal, outcome))
        agent.computer.write("held.dat", held)
        answer = agent.solve(goal, bindings={"path": "held.dat"})
        self.assertEqual(answer["status"], "PASS", (goal, answer))
        self.assertEqual(answer["stdout"], oracle(held), goal)
        return outcome

    def test_a_battery_of_requests_is_right_on_files_it_never_saw(self) -> None:
        cases = [
            (
                "show the second field of each line, comma separated",
                "x,10\ny,2\n",
                "p,7\nq,9\n",
                "m,4\nn,100\no,20\n",
                lambda text: "".join(row[1] + "\n" for row in self._fields(text, ",")),
            ),
            (
                "replace every comma with a semicolon",
                "x,10\ny,2\n",
                "p,7\n",
                "a,b,c\nd,e\n",
                lambda text: text.replace(",", ";"),
            ),
            (
                "show only the lines that contain error",
                "ok\nan error\n",
                "error here\nfine\n",
                "no match\nan error late\nsecond error\n",
                lambda text: "".join(line + "\n" for line in text.splitlines() if "error" in line),
            ),
            (
                "the first field of each line, colon separated",
                "x:1\ny:2\n",
                "p:9\n",
                "q:1:2\nw:3\n",
                lambda text: "".join(row[0] + "\n" for row in self._fields(text, ":")),
            ),
            (
                "sort the rows by the second column, comma separated",
                "x,10\ny,9\nz,8\n",
                "p,7\nq,6\n",
                "k,10\nj,9\ni,8\n",
                lambda text: self._sort_rows(text, ",", 2),
            ),
            (
                "sort the rows by the second column numerically, comma separated",
                "x,10\ny,9\nz,8\n",
                "p,7\nq,6\n",
                "k,10\nj,9\ni,8\n",
                lambda text: self._sort_rows(text, ",", 2, numeric=True),
            ),
            (
                "sort the rows by the second column descending, comma separated",
                "x,10\ny,9\nz,8\n",
                "p,7\nq,6\n",
                "k,2\nj,9\ni,8\n",
                lambda text: self._sort_rows(text, ",", 2, descending=True),
            ),
            (
                "show the last two rows sorted by the second column, comma separated",
                "x,4\ny,2\nz,9\nw,1\n",
                "p,5\nq,3\nr,7\n",
                "m,3\nn,8\no,1\np,6\nq,5\n",
                lambda text: "\n".join(self._sort_rows(text, ",", 2).splitlines()[-2:]) + "\n",
            ),
            (
                "show the first character of each line",
                "alpha\nbeta\n",
                "gamma\n",
                "zeta\neta\n",
                lambda text: "".join(line[:1] + "\n" for line in text.splitlines()),
            ),
            (
                "count the lines",
                "a\nb\n",
                "c\nd\ne\n",
                "p\nq\nr\ns\n",
                lambda text: str(len(text.splitlines())) + "\n",
            ),
            (
                "uppercase every letter",
                "ab\ncd\n",
                "ef\n",
                "hi there\n",
                lambda text: text.upper(),
            ),
            (
                "count the distinct values in the second column, comma separated",
                "x,10\nx,3\ny,7\n",
                "q,2\nq,9\nr,4\n",
                "z,5\nz,5\nw,1\nv,1\n",
                lambda text: str(len({row[1] for row in self._fields(text, ",")})) + "\n",
            ),
            (
                "remove the duplicate lines",
                "a\nb\na\nc\n",
                "z\nz\nq\n",
                "r\ns\nr\nt\ns\n",
                self._distinct_lines,
            ),
            (
                # The long line is first on one file and second on the other,
                # and last on the file it is asked about.  A positional
                # stand-in like `tail -n +2` fits the first file only.
                "show the lines longer than 20 characters",
                "x" * 25 + "\nshort\n",
                "ok\n" + "y" * 30 + "\n",
                "tiny\n" + "z" * 22 + "\n",
                lambda text: "".join(line + "\n" for line in text.splitlines()
                                     if len(line) > 20),
            ),
            (
                "show the lines with fewer than 4 characters",
                "abcd\nef\n",
                "ghij\nkl\n",
                "mnop\nqr\nst\n",
                lambda text: "".join(line + "\n" for line in text.splitlines()
                                     if len(line) < 4),
            ),
            (
                # "banana" contains an a; only a line that *starts* with one
                # belongs in the answer, so an unanchored pattern is wrong here.
                "show the lines that start with b",
                "banana\napple\nbrick\n",
                "cab\nbag\n",
                "banana\nabacus\ncherry\n",
                lambda text: "".join(line + "\n" for line in text.splitlines()
                                     if line.startswith("b")),
            ),
            (
                "show the number of characters in each line",
                "abc\nde\n",
                "hello\nhi\n",
                "xy\nxyz\nlonger line here\n",
                lambda text: "".join(str(len(line)) + "\n" for line in text.splitlines()),
            ),
            (
                "keep only the first three characters of each line",
                "abcdef\nxy\n",
                "qrstu\nz\n",
                "hello\nworld\nab\n",
                lambda text: "".join(line[:3] + "\n" for line in text.splitlines()),
            ),
            (
                "show the third character of each line",
                "abcdef\nxy\n",
                "qrstu\nz\n",
                "hello\nworld\nab\n",
                lambda text: "".join(line[2:3] + "\n" for line in text.splitlines()),
            ),
            (
                "show the lines that end with z",
                "buzz\ncat\nfizz\n",
                "zebra\nquiz\n",
                "fizz\nbanana\nzigzag\n",
                lambda text: "".join(line + "\n" for line in text.splitlines()
                                     if line.endswith("z")),
            ),
        ]
        for goal, first, second, held, oracle in cases:
            with self.subTest(goal=goal):
                self._check(goal, first, second, held, oracle)

    @staticmethod
    def _distinct_lines(text: str) -> str:
        seen: set[str] = set()
        out: list[str] = []
        for line in text.splitlines():
            if line not in seen:
                seen.add(line)
                out.append(line)
        return "".join(line + "\n" for line in out)


class EndToEndTests(unittest.TestCase):
    """Two different kinds of knowledge live in one creature."""

    def test_shell_and_table_skills_coexist_and_compose_through_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = LivingAgent(tmp)
            agent.computer.write("demo.txt", "a\nb\n")
            agent.computer.write("report.txt", "x\ny\nz\n")
            agent.learn_shell_skill(
                "count the lines in a file",
                "wc -l < demo.txt",
                {"path": "demo.txt"},
                canary=({"canary.txt": "a\nb\nc\n"}, "3"),
                postcondition=r"^[0-9]+$",
            )
            oracle = benchmark.guarded_oracle("group_sum")
            demo = benchmark.covering_instance("group_sum", random.Random(5))
            payload, result = agent.learn_table_skill(
                "total salary per department", [(demo, oracle(demo))], oracle, seed=5
            )
            self.assertTrue(result.success)
            self.assertEqual(agent.solve("count the lines in 'report.txt'")["status"], "PASS")
            table = benchmark.generate_instance("group_sum", random.Random(11))
            produced = apply_program(
                __import__("canonical.runtime.living_core_v1", fromlist=["program_from_json"]).program_from_json(
                    payload["program"]
                ),
                table,
            )
            want = oracle(table)
            self.assertEqual(produced.rows, want.rows)
            store = agent.snapshot()
            kinds = {entry["kind"] for entry in store["memory"]["entries"]}
            self.assertTrue({"skill", "episode"} <= kinds)


if __name__ == "__main__":
    unittest.main(verbosity=2)
