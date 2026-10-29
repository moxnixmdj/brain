"""CrossHair must not execute arbitrary input by default or credit empty checks."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import astra_runtime
from canonical.runtime.bound_capabilities import crosshair_contract_oracle as oracle

ROOT = Path(__file__).resolve().parents[2]


class CrossHairIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-crosshair-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root / "program.py"
        self.output = self.root / "result.json"

    def invoke(self, **extra):
        return oracle.run({"target_path": "program.py", "output_path": "result.json", **extra}, self.root)

    def test_untrusted_source_is_not_executed_without_explicit_opt_in(self):
        sentinel = self.root.parent / (self.root.name + "-outside")
        self.addCleanup(sentinel.unlink, missing_ok=True)
        self.target.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n"
                               'def f(x: int) -> int:\n    """post: _ == x"""\n    return x\n')
        result = self.invoke()
        self.assertFalse(sentinel.exists())
        self.assertFalse(result["verified"])
        self.assertTrue(result["output_verified"])
        self.assertEqual(result["status"], "HOST_EXECUTION_NOT_AUTHORIZED")
        action = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())[
            "capabilities"]["python.contract.check.crosshair.v1"]["action_template"]
        with self.assertRaisesRegex(astra_runtime.Blocker, "ACTION_EXPECTATION_FAILED"):
            astra_runtime._verify_action_expectation(action, result)

    def test_no_contract_does_not_execute_source_or_prove_holds(self):
        sentinel = self.root.parent / (self.root.name + "-outside")
        self.addCleanup(sentinel.unlink, missing_ok=True)
        self.target.write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n"
                               "def f(x: int) -> int:\n    return x\n")
        result = self.invoke(allow_unsafe_host_execution=True)
        self.assertEqual(result["status"], "NO_CHECKABLE_CONTRACTS")
        self.assertFalse(result["verified"])
        self.assertFalse(sentinel.exists())
        self.assertFalse(result["proves_absence"])

    def test_clean_analysis_is_not_claimed_as_universal_proof(self):
        self.target.write_text('def f(x: int) -> int:\n    """post: _ == x * 2"""\n    return x * 2\n')
        result = self.invoke(allow_unsafe_host_execution=True)
        self.assertEqual(result["status"], "NO_COUNTEREXAMPLE_FOUND")
        self.assertFalse(result["proves_absence"])
        self.assertGreater(result["checked_conditions"], 0)

    def test_output_must_not_overwrite_target(self):
        self.target.write_text('def f(x: int) -> int:\n    """post: _ == x"""\n    return x\n')
        original = self.target.read_bytes()
        with self.assertRaisesRegex(ValueError, "OUTPUT_OVERLAPS_INPUT"):
            oracle.run({"target_path": "program.py", "output_path": "program.py"}, self.root)
        self.assertEqual(self.target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
