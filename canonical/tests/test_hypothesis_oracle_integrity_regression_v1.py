"""Property checks must exercise the requested contract without executing arbitrary source."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime import astra_runtime
from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as oracle


class HypothesisOracleIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_source(self, source):
        return oracle.run({"source": source, "output_path": "result.json"}, self.root)

    def test_detects_actual_declared_postcondition(self):
        result = self.run_source('def f(x):\n    """post: _ == 0"""\n    return x * x\n')
        self.assertGreater(result["checked"], 0)
        self.assertTrue(result["violations"])
        self.assertFalse(result["verified"])
        self.assertFalse(result["proves_absence"])

    def test_correct_negative_result_is_bounded_and_not_a_proof(self):
        result = self.run_source('def f(x):\n    """post: _ == x * x"""\n    return x * x\n')
        self.assertTrue(result["hypothesis_available"])
        self.assertGreater(result["checked"], 0)
        self.assertFalse(result["violations"])
        self.assertTrue(result["verified"])
        self.assertFalse(result["proves_absence"])

    def test_precondition_is_respected(self):
        result = self.run_source('def f(x):\n    """pre: x != 0\n    post: _ * x == 1"""\n    return 1 / x\n')
        self.assertGreater(result["checked"], 0)
        self.assertFalse(any(row.get("input") == 0 for row in result["violations"]))

    def test_function_exception_is_inconclusive_not_a_contract_witness(self):
        source = ('def f(x):\n    """post: _ == 1 / x\n    raises: ZeroDivisionError"""\n'
                  '    return 1 / x\n')
        result = self.run_source(source)
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "UNSUPPORTED_EVALUATION")
        self.assertEqual(result["violations"], [])

    def test_invalid_or_missing_contract_cannot_verify(self):
        for source in ('def f(:\n', 'def f(x):\n    return x\n', ''):
            with self.subTest(source=source):
                result = self.run_source(source)
                self.assertFalse(result["verified"])
                self.assertEqual(result["checked"], 0)

    def test_source_side_effects_are_never_executed(self):
        sentinel = self.root / "escaped"
        source = (f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n"
                  'def f(x):\n    """post: _ == x"""\n    return x\n')
        result = self.run_source(source)
        self.assertFalse(result["verified"])
        self.assertFalse(sentinel.exists())

    def test_unsupported_annotations_and_shadowed_builtins_do_not_verify(self):
        for source in ('def f(x: missing):\n    """post: _ == x"""\n    return x\n',
                       'def f(abs):\n    """post: _ == abs"""\n    return abs(abs)\n'):
            with self.subTest(source=source):
                self.assertFalse(self.run_source(source)["verified"])

    def test_hypothesis_unavailable_fails_closed(self):
        from unittest.mock import patch
        import builtins
        original = builtins.__import__
        def no_hypothesis(name, *args, **kwargs):
            if name == "hypothesis" or name.startswith("hypothesis."):
                raise ImportError("not installed")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=no_hypothesis):
            result = self.run_source('def f(x):\n    """post: _ == x"""\n    return x\n')
        self.assertFalse(result["hypothesis_available"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["checked"], 0)

    def test_hard_link_or_other_python_output_cannot_corrupt_source(self):
        source = self.root / "program.py"
        source.write_text('def f(x):\n    """post: _ == x"""\n    return x\n')
        before = source.read_bytes()
        alias = self.root / "result.json"
        alias.hardlink_to(source)
        for args in ({"source_path": "program.py", "output_path": "result.json"},
                     {"source": source.read_text(), "output_path": "program.py"}):
            with self.subTest(args=args):
                with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                    oracle.run(args, self.root)
                self.assertEqual(source.read_bytes(), before)

    def test_output_must_not_overwrite_source(self):
        source = self.root / "program.py"
        source.write_text('def f(x):\n    """post: _ == x"""\n    return x\n')
        before = source.read_bytes()
        with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
            oracle.run({"source_path": "program.py", "output_path": "program.py"}, self.root)
        self.assertEqual(source.read_bytes(), before)

    def test_planner_rejects_a_violation_even_when_artifact_was_written(self):
        import json
        registry = Path(__file__).resolve().parents[1] / "runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        action = json.loads(registry.read_text())["capabilities"][oracle.CAPABILITY_ID]["action_template"]
        result = self.run_source('def f(x):\n    """post: _ == 0"""\n    return x * x\n')
        with self.assertRaisesRegex(astra_runtime.Blocker, "ACTION_EXPECTATION_FAILED"):
            astra_runtime._verify_action_expectation(action, result)


if __name__ == "__main__":
    unittest.main()
