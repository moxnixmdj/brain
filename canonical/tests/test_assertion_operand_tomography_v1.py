"""Value capture must not change the assertion it observes."""
import ast
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import assertion_operand_tomography_v1 as tomography  # noqa: E402


class TomographyTests(unittest.TestCase):
    def test_instrumentation_records_both_operands(self):
        source = "def test_case():\n    assert 1 + 1 == 3\n"
        rewritten, keys = tomography.instrument(source)
        self.assertEqual(len(keys), 2)
        self.assertIn("_brain_record", rewritten)

    def test_instrumented_assertion_keeps_the_same_verdict(self):
        source = "def f(x):\n    return x + 1\n\ndef test_case():\n    assert f(1) == 3\n"
        rewritten, _ = tomography.instrument(source)
        namespace = {"_brain_record": lambda key, value: value}
        body = "\n".join(rewritten.splitlines()[1:])
        exec(compile(body, "rewritten", "exec"), namespace)
        with self.assertRaises(AssertionError):
            namespace["test_case"]()

    def test_capture_reads_values_from_a_real_failure(self):
        with tempfile.TemporaryDirectory() as where:
            root = pathlib.Path(where)
            (root / "mod.py").write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
            test_file = root / "test_mod.py"
            original = "from mod import f\n\ndef test_case():\n    assert f(1) == 3\n"
            test_file.write_text(original, encoding="utf-8")
            result = tomography.capture(root, "test_mod.py", "test_mod.py::test_case", 20)
            self.assertEqual(result["outcome"], "CAPTURED")
            self.assertIn("2", result["values"].values())
            self.assertIn("3", result["values"].values())
            self.assertEqual(test_file.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
