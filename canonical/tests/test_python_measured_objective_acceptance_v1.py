from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import textwrap
import unittest

from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as m
from canonical.runtime import python_measured_objective_acceptance_v1 as a


class MeasuredObjectiveAcceptanceV1Tests(unittest.TestCase):
    def fixture(self, expected: int):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        proj = root / "proj"
        proj.mkdir()
        (proj / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (proj / "test_m.py").write_text(textwrap.dedent(f"""
            import unittest
            from m import f
            class T(unittest.TestCase):
                def test_f(self): self.assertEqual(f(), {expected})
            if __name__ == "__main__": unittest.main()
        """), encoding="utf-8")
        m.run({
            "source_root": "proj",
            "test_paths": ["test_m.py"],
            "test_argv": [sys.executable, "test_m.py"],
            "output_path": "receipt.json",
            "timeout_s": 5,
        }, root)
        return td, root

    def test_tests_pass_requirement_accepts_only_measured_true(self):
        td, root = self.fixture(1)
        with td:
            out = a.evaluate_from_receipt(
                "tests_pass must be true.",
                measurement_receipt_path="receipt.json",
                root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["measurement_bound"])
            self.assertTrue(out["acceptance_stop_authorized"])

    def test_tests_pass_requirement_rejects_measured_false(self):
        td, root = self.fixture(2)
        with td:
            out = a.evaluate_from_receipt(
                "tests_pass must be true.",
                measurement_receipt_path="receipt.json",
                root=root,
            )
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["acceptance_stop_authorized"])
            self.assertTrue(out["measurement_bound"])

    def test_two_measurement_predicates_compose(self):
        td, root = self.fixture(1)
        with td:
            out = a.evaluate_from_receipt(
                "tests_pass must be true.\npython_parse_ok must be true.",
                measurement_receipt_path="receipt.json",
                root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(
                out["objective_result"]["evaluated_obligation_count"], 2
            )

    def test_semantic_request_still_blocks_even_when_tests_pass(self):
        td, root = self.fixture(1)
        with td:
            out = a.evaluate_from_receipt(
                "Fix the parser bug.",
                measurement_receipt_path="receipt.json",
                root=root,
            )
            self.assertFalse(out["pass"], out)
            self.assertEqual(
                out["objective_result"]["status"],
                "OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS",
            )

    def test_tampered_measurement_receipt_fails_closed(self):
        td, root = self.fixture(2)
        with td:
            path = root / "receipt.json"
            receipt = json.loads(path.read_text())
            receipt["measurements"]["tests_pass"] = True
            path.write_text(json.dumps(receipt), encoding="utf-8")
            out = a.evaluate_from_receipt(
                "tests_pass must be true.",
                measurement_receipt_path="receipt.json",
                root=root,
            )
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["measurement_bound"])
            self.assertIn("MEASUREMENT_RECEIPT_HASH_MISMATCH", out["errors"][0])

    def test_missing_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            out = a.evaluate_from_receipt(
                "tests_pass must be true.",
                measurement_receipt_path="missing.json",
                root=td,
            )
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["acceptance_stop_authorized"])

    def test_zero_external_runtime_cognition(self):
        self.assertEqual(a.MODEL_DEPENDENCY_COUNT, 0)
        self.assertEqual(a.EXTERNAL_MODEL_RUNTIME_CALLS, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
