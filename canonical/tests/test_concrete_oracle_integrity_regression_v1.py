"""Concrete witnesses must be task-bound, nonvacuous, and safe on untrusted source."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import astra_runtime
from canonical.runtime.bound_capabilities import concrete_execution_oracle as concrete
from canonical.runtime.bound_capabilities import evidence_oracle_concrete_v1 as adapter

ROOT = Path(__file__).resolve().parents[2]


class ConcreteOracleIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-concrete-oracle-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()

    def test_exec_side_effect_outside_project_is_never_executed(self):
        sentinel = self.root.parent / "outside_project"
        sources = [
            f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\ndef f(x):\n    \"\"\"post: _ == x\"\"\"\n    return x\n",
            f"def f(x):\n    \"\"\"post: _ == x\"\"\"\n    return __import__('pathlib').Path({str(sentinel)!r}).write_text('bad')\n",
        ]
        for source in sources:
            with self.subTest(source=source):
                result = concrete.check_source(source)
                self.assertEqual(result["status"], "UNSUPPORTED_SOURCE")
                self.assertEqual(result["checked"], 0)
                self.assertFalse(sentinel.exists())

    def test_broken_and_correct_contracts_are_not_conflated(self):
        bad = 'def f(x: int) -> int:\n    """post: _ == x * 2"""\n    return x + 2\n'
        good = 'def f(x: int) -> int:\n    """post: _ == x * 2"""\n    return x * 2\n'
        broken = concrete.check_source(bad)
        clean = concrete.check_source(good)
        self.assertEqual(broken["status"], "CONTRACT_VIOLATION_FOUND")
        self.assertGreater(len(broken["violations"]), 0)
        self.assertEqual(clean["status"], "NO_COUNTEREXAMPLE_IN_SAMPLE")
        self.assertEqual(clean["checked"], 13)
        self.assertFalse(clean["violations"])
        self.assertFalse(clean["proves_absence"])

    def test_preconditions_and_invalid_contracts_fail_closed(self):
        src = 'def f(x):\n    """pre: x != 0\n    post: _ * x == 1"""\n    return 1 / x\n'
        result = concrete.check_source(src, [0, 1, -1])
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["violations"], [])
        for bad in ("def f(:\n", "def f(x):\n    return x\n", ""):
            with self.subTest(source=bad):
                result = concrete.check_source(bad)
                self.assertNotEqual(result["status"], "CONTRACT_VIOLATION_FOUND")
                self.assertEqual(result["checked"], 0)

    def test_an_exception_does_not_prove_a_postcondition_violation(self):
        source = ('def f(x):\n    """post: _ >= 0\n    raises: ZeroDivisionError"""\n'
                  '    return 1 / x\n')
        result = concrete.check_source(source, [0])
        self.assertEqual(result["status"], "UNSUPPORTED_EVALUATION")
        self.assertEqual(result["violations"], [])
        adapter_result = adapter.run({"source": source, "sample": [0], "output_path": "result.json"}, self.root)
        self.assertFalse(adapter_result["verified"])

    def test_adapter_requires_real_violation_for_planner_effect(self):
        registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        action = registry["capabilities"][adapter.CAPABILITY_ID]["action_template"]
        clean = 'def f(x):\n    """post: _ == x"""\n    return x\n'
        for source in (None, clean, 'def f(x):\n    return x\n'):
            with self.subTest(source=source):
                args = {"output_path": "result.json"}
                if source is not None:
                    args["source"] = source
                result = adapter.run(args, self.root)
                self.assertTrue(result["output_verified"])
                self.assertFalse(result["verified"])
                with self.assertRaisesRegex(astra_runtime.Blocker, "ACTION_EXPECTATION_FAILED"):
                    astra_runtime._verify_action_expectation(action, result)
        broken = adapter.run({"source": 'def f(x):\n    """post: _ == 0"""\n    return x\n',
                              "output_path": "result.json"}, self.root)
        self.assertTrue(broken["verified"])
        astra_runtime._verify_action_expectation(action, broken)

    def test_adapter_refuses_hard_link_output_to_source(self):
        source = self.root / "f.py"
        source.write_text('def f(x):\n    """post: _ == x"""\n    return x\n')
        original = source.read_bytes()
        alias = self.root / "result.json"
        alias.hardlink_to(source)
        with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
            adapter.run({"source_path": "f.py", "output_path": "result.json"}, self.root)
        self.assertEqual(source.read_bytes(), original)

    def test_adapter_refuses_to_overwrite_source(self):
        path = self.root / "f.py"
        path.write_text('def f(x):\n    """post: _ == x"""\n    return x\n')
        before = path.read_bytes()
        with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
            adapter.run({"source_path": "f.py", "output_path": "f.py"}, self.root)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
