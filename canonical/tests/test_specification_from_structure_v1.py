"""The instrumentation must not lie in the two directions a verifier lies.

Every test here pins a defect this instrument actually had while it was being built, or a
property that keeps a wrong result from being reported as a right one. No mock, no network,
no fixture fed from history: the code under test is compiled from source written in the test
and executed in the same bounded child the tool uses.

The four defects found during construction, each with its test below:

1. The grid had no absolute path, so `isabs` was a constant `False` and `isabs` looked
   idempotent. A law that holds because the function is constant is a tautology.
2. Symmetry was proposed on heterogeneous operands, so `a + b` failed `COMMUTATIVITY` on
   `"a" + 12` -- a law about Python's type rules, not about the function.
3. `MULTISET_PRESERVED` was proposed for a name that says "deduplicate", where dropping
   duplicates is the point. The law must be the one the name claims.
4. A module's top-level code (`sys.path.insert`, `if __name__ == "__main__"`) ran when the
   module was imported for judging. Only the selected function definitions run now.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import specification_from_structure_v1 as spec
from canonical.tools import specification_from_structure_measure_v1 as measure_tool


def verdicts(rows, kind=None):
    if kind is not None:
        rows = [row for row in rows if row["kind"] == kind]
    return [row["verdict"] for row in rows]


def run(source, variants=(), extra_pools=None):
    derived = spec.derive(source, "subject")
    names = [entry["name"] for entry in derived["functions"]]
    return spec.run_child(
        spec.child_payload(
            module_name="subject",
            baseline_source=spec.reduce_module(source, names),
            derived=derived,
            variants=[
                {
                    "variant_id": name,
                    "operator": "TEST",
                    "function": function,
                    "source": spec.reduce_module(text, names),
                }
                for name, function, text in variants
            ],
            extra_pools=extra_pools,
        )
    )


class LoadingTests(unittest.TestCase):
    def test_a_definition_that_cannot_be_defined_does_not_take_the_module_with_it(self):
        # 43 of 121 modules in this tree failed to load as a reduction because one kept
        # definition needed a name the reduction had dropped. A module that fails to load
        # yields no laws, so that failure was silently removing a third of the corpus.
        source = (
            "from nowhere import Missing\n"
            "class Broken(Missing):\n    pass\n"
            "def fine(a):\n    return a\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            module = spec._load_module(source, "fallback", pathlib.Path(directory))
        self.assertEqual(module.fine(2), 2)
        self.assertTrue(module._BRAIN_SKIPPED_DEFINITIONS)


class DerivationTests(unittest.TestCase):
    def test_a_name_that_says_canonical_form_proposes_a_fixed_point(self):
        derived = spec.derive("def normalize(text):\n    return text\n", "m")
        kinds = [invariant["kind"] for invariant in derived["invariants"]]
        self.assertIn("IDEMPOTENCE", kinds)
        idempotent = [i for i in derived["invariants"]
                      if i["kind"] == "IDEMPOTENCE" and i["function"] == "normalize"][0]
        self.assertIn("canonical form", idempotent["derivation"])

    def test_a_function_whose_body_mentions_a_file_is_declined_not_called(self):
        derived = spec.derive(
            "def read_it(path):\n    return open(path).read()\n"
            "def fine(x):\n    return x\n",
            "m",
        )
        self.assertEqual([entry["name"] for entry in derived["functions"]], ["fine"])
        declined = {entry["name"]: entry["reason"] for entry in derived["declined"]}
        self.assertIn("REACHES_A_SIDE_EFFECTING_NAME", declined["read_it"])
        self.assertIn("open", declined["read_it"])

    def test_reduction_keeps_definitions_and_drops_module_level_effects(self):
        # This test used to assert that an unselected definition was *removed* from the reduced
        # module. That assertion pinned the wrong behaviour and it cost a measurement: a selected
        # function that calls a helper which the reduction had deleted raises `NameError`, and a
        # raising function is reported NOT_APPLICABLE for every law -- silence that reads exactly
        # like "this code has no laws". Kept in full: definitions may stay because a `def`
        # executes nothing but its decorators and defaults; what may not stay is a statement.
        source = (
            "import os\n"
            "import requests\n"
            "sys_path_hack = os.getcwd()\n"
            "TABLE = {1: 2}\n"
            "def keep(a):\n    return helper(a)\n"
            "def helper(a):\n    return a\n"
            "def decorated():\n    return 2\n"
            "decorated = os.getcwd()(decorated)\n"
        )
        reduced = spec.reduce_module(source, ["keep"])
        self.assertIn("def keep", reduced)
        self.assertIn("def helper", reduced)
        self.assertNotIn("requests", reduced)
        self.assertNotIn("sys_path_hack", reduced)
        self.assertNotIn("decorated = os.getcwd()", reduced)
        self.assertIn("TABLE", reduced)

    def test_a_class_whose_body_runs_code_is_not_kept_by_the_reduction(self):
        # Keeping definitions is safe only up to the class body, which is a statement list. A
        # reduction that kept `TABLE = load()` inside a class crashed every child that loaded it,
        # which surfaced as SPECIFICATION_CHILD_FAILED rather than as a wrong number.
        source = (
            "def load():\n    raise SystemExit('must not run')\n"
            "class Inert:\n    TABLE = {1: 2}\n    def f(self):\n        return 1\n"
            "class Live:\n    TABLE = load()\n"
        )
        reduced = spec.reduce_module(source, ["load"])
        self.assertIn("class Inert", reduced)
        self.assertNotIn("class Live", reduced)
        namespace: dict[str, object] = {}
        exec(compile(reduced, "<reduced>", "exec"), namespace)  # noqa: S102 - our own reduction
        self.assertIn("Inert", namespace)

    def test_a_helper_removed_from_the_reduction_is_what_silences_a_law(self):
        # The measurement above is the reason this exists: with the helper kept, `keep` is
        # callable and a law about it can be confirmed; with the helper deleted, the same law is
        # NOT_APPLICABLE and reports nothing. The difference is the reduction, not the code.
        source = "def keep(a):\n    return helper(a)\n\ndef helper(a):\n    return a\n"
        reduced = spec.reduce_module(source, ["keep"])
        namespace: dict[str, object] = {}
        exec(compile(reduced, "<reduced>", "exec"), namespace)  # noqa: S102 - our own reduction
        self.assertEqual(namespace["keep"](3), 3)
        without = "def keep(a):\n    return helper(a)\n"
        namespace = {}
        exec(compile(without, "<reduced>", "exec"), namespace)  # noqa: S102
        with self.assertRaises(NameError):
            namespace["keep"](3)  # type: ignore[operator]

    def test_a_module_whose_top_level_raises_is_still_judgeable(self):
        source = (
            "raise SystemExit('this must never run')\n"
            "def double(x):\n    return x + x\n"
        )
        reduced = spec.reduce_module(source, ["double"])
        self.assertNotIn("SystemExit", reduced)
        result = run(source)
        totality = [row for row in result["confirmations"]
                    if row["kind"] == "TOTALITY" and row["function"] == "double"][0]
        self.assertEqual(totality["verdict"], spec.CONFIRMED)
        self.assertGreater(totality["inputs_defined"], 0)


class ConfirmationTests(unittest.TestCase):
    def test_a_fixed_point_is_confirmed_by_running_the_program(self):
        result = run("def normalize(text):\n"
                     "    return ' '.join(str(text).split()).lower()\n")
        row = [r for r in result["confirmations"] if r["kind"] == "IDEMPOTENCE"][0]
        self.assertEqual(row["verdict"], spec.CONFIRMED)
        self.assertGreater(row["discriminating_inputs"], 0)

    def test_a_law_the_program_breaks_is_refuted_and_reported(self):
        result = run("def normalize(text):\n    return str(text) + '!'\n")
        row = [r for r in result["confirmations"] if r["kind"] == "IDEMPOTENCE"][0]
        self.assertEqual(row["verdict"], spec.REFUTED)
        self.assertIn("first_disagreement", row)

    def test_a_constant_function_makes_the_law_vacuous(self):
        result = run("def is_zero(x):\n    return False\n")
        idempotence = [r for r in result["confirmations"] if r["kind"] == "IDEMPOTENCE"][0]
        self.assertEqual(idempotence["verdict"], spec.VACUOUS)
        self.assertEqual(idempotence["discriminating_inputs"], 0)

    def test_the_grid_contains_a_value_that_can_tell_an_absolute_path_apart(self):
        pool = spec.POOLS["str"]
        self.assertIn("/", pool)
        self.assertTrue(any(value.startswith("/") and value != "/" for value in pool))
        grid = spec.build_grid([{"name": "path", "kind": "str"}])
        args = [entry["args"][0] for entry in grid]
        self.assertTrue(any(value.startswith("/") for value in args))

    def test_real_values_are_tried_before_the_invented_pool(self):
        grid = spec.build_grid(
            [{"name": "path", "kind": "str"}],
            extra_pools={"str": ["canonical/runtime/x.py"]},
        )
        self.assertEqual(grid[0]["args"][0], "canonical/runtime/x.py")

    def test_symmetry_is_not_claimed_on_a_heterogeneous_pair(self):
        def add(left, right):
            return left + right

        outcome = spec._evaluate(
            {"kind": "COMMUTATIVITY", "function": "add"},
            {"add": add},
            ("a", 12),
            0.2,
        )
        self.assertIsNone(outcome["holds"])
        self.assertEqual(outcome["why"], "NOT_A_HOMOGENEOUS_PAIR")

    def test_a_deduplicating_name_is_judged_by_set_preservation(self):
        result = run("def sorted_unique(items):\n    return sorted(set(items))\n")
        table = {(row["kind"], row["verdict"]) for row in result["confirmations"]}
        self.assertIn(("SET_PRESERVED", spec.CONFIRMED), table)
        self.assertIn(("MULTISET_PRESERVED", spec.REFUTED), table)

    def test_the_standard_library_is_the_reference_for_a_name_it_already_defines(self):
        result = run("import math\n\ndef floor(x):\n    return math.floor(x)\n")
        row = [r for r in result["confirmations"] if r["kind"] == "STDLIB_DIFFERENTIAL"][0]
        self.assertEqual(row["verdict"], spec.CONFIRMED)

    def test_a_call_that_never_returns_is_an_observation_not_a_hang(self):
        result = run("def spin(x):\n    while True:\n        pass\n")
        self.assertTrue(result["confirmations"])
        self.assertEqual(
            {row["verdict"] for row in result["confirmations"]},
            {spec.NOT_APPLICABLE},
        )


class JudgementTests(unittest.TestCase):
    BASE = (
        "def normalize(text):\n"
        "    return ' '.join(str(text).split()).lower()\n"
        "\n"
        "def add(a, b):\n"
        "    return a + b\n"
    )

    def test_a_variant_that_breaks_the_confirmed_law_is_rejected_with_a_witness(self):
        broken = self.BASE.replace('.lower()', '.lower() + "!"')
        result = run(self.BASE, [("v1", "normalize", broken)])
        judgement = result["judgements"][0]
        self.assertTrue(judgement["killed_by"])
        self.assertEqual(judgement["counterexample"]["law"], "IDEMPOTENCE")
        self.assertIn("args", judgement["counterexample"])
        self.assertIsNotNone(judgement["counterexample"]["observed"])

    def test_a_variant_no_law_covers_is_reported_as_survived(self):
        # `normalize` with a trailing space still reaches a fixed point and never raises, so
        # nothing this instrument knows can tell it from the real function. It must be
        # reported as the blind spot rather than quietly counted as a pass.
        subtle = self.BASE.replace('.lower()', '.lower() + " "')
        result = run(self.BASE, [("v2", "normalize", subtle)])
        judgement = result["judgements"][0]
        self.assertEqual(judgement["killed_by"], [])
        self.assertIsNone(judgement["counterexample"])

    def test_a_variant_is_judged_only_by_laws_about_the_function_it_changed(self):
        broken_add = self.BASE.replace("return a + b", "return a - b")
        result = run(self.BASE, [("v3", "add", broken_add)])
        judgement = result["judgements"][0]
        self.assertEqual(judgement["function"], "add")
        self.assertTrue(judgement["laws_brought_to_bear"] < 6)

    def test_a_variant_whose_module_cannot_import_is_a_difference_not_a_crash(self):
        unimportable = 'def normalize(text=undefined_name):\n    return text\n'
        result = run(self.BASE, [("v4", "normalize", unimportable)])
        judgement = result["judgements"][0]
        self.assertEqual(judgement["killed_by"], ["IMPORT_FAILED"])

    def test_nothing_is_written_outside_the_temporary_directory(self):
        before = sorted(path.name for path in ROOT.iterdir())
        run(self.BASE, [("v5", "normalize", self.BASE.replace(".lower()", ".upper()"))])
        after = sorted(path.name for path in ROOT.iterdir())
        self.assertEqual(before, after)
        self.assertFalse(list(ROOT.glob("brain_spec_structure_*")))


class MeasurementTests(unittest.TestCase):
    def test_the_measurement_reports_what_it_measured_and_nothing_it_did_not(self):
        report = measure_tool.measure(
            ("canonical/swe_kernel",), max_modules=3, max_mutants=2, call_timeout_s=0.3
        )
        totals = report["totals"]
        self.assertEqual(
            totals["killed_by_a_law"] + totals["killed_by_totality_only"]
            + totals["survived_the_specification"],
            totals["variants"],
        )
        if totals["variants"]:
            self.assertIn("blind_spot_rate", totals)
            self.assertLessEqual(totals["blind_spot_rate"], 1.0)
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["incremental_spend_usd"], 0)
        self.assertGreater(report["files_scanned"], 0)

    def test_the_receipt_says_no_capability_was_claimed(self):
        self.assertEqual(
            measure_tool.AUTHORITY, "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
        )
        committed = ROOT / "canonical/verification/SPECIFICATION_FROM_STRUCTURE_20261116_V1.json"
        if committed.is_file():
            payload = json.loads(committed.read_text(encoding="utf-8"))
            self.assertEqual(payload["authority"], measure_tool.AUTHORITY)
            self.assertEqual(payload["model_calls"], 0)
            self.assertEqual(payload["network_calls"], 0)
            self.assertIn("blind_spot_rate", payload["totals"])


if __name__ == "__main__":
    unittest.main()
