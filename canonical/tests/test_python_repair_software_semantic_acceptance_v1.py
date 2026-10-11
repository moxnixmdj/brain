from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import textwrap
import unittest

BASE = pathlib.Path("canonical/runtime/bound_capabilities")
SPEC = importlib.util.spec_from_file_location(
    "v9", BASE / "python_repair_software_semantic_acceptance_v1.py"
)
v9 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v9)


class RepairSoftwareSemanticAcceptanceV9Tests(unittest.TestCase):
    def fixture(self, files):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        for name, body in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(body), encoding="utf-8")
        return td, root

    def simple_files(self):
        return {
            "m.py": "def f(x):\n    return x < 3\n",
            "trace_fail.py": "from m import f\nassert f(3)\n",
            "trace_pass.py": "from m import f\nassert f(2)\n",
            "test_all.py": "from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n",
        }

    def runv9(self, root, task_text, **extra):
        args = {
            "source_root": ".",
            "test_paths": ["trace_fail.py", "trace_pass.py"],
            "test_argv": [sys.executable, "test_all.py"],
            "task_text": task_text,
            "output_path": "v9.json",
            "timeout_s": 4,
            "max_guided_files": 1,
            "max_guided_symbols_per_file": 3,
            "mutations_per_file": 12,
            "max_pair_candidates": 100,
            "max_control_files": 6,
            "max_control_symbols_per_file": 6,
        }
        args.update(extra)
        return v9.run(args, root)

    def test_natural_tests_pass_postcondition_clears_v8_semantic_residual(self):
        td, root = self.fixture(self.simple_files())
        original = (root / "m.py").read_bytes()
        with td:
            out = self.runv9(root, "Make all tests pass.")
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["acceptance_stop_authorized"], out)
            self.assertEqual(out["acceptance_route"], "BOUNDED_SOFTWARE_REQUEST_CELLS_V1")
            self.assertTrue(out["measured_fields"]["tests_pass"])
            self.assertEqual((root / "m.py").read_bytes(), original)
            self.assertTrue(out["source_restored"])

    def test_multisegment_natural_postconditions_pass(self):
        td, root = self.fixture(self.simple_files())
        with td:
            out = self.runv9(
                root,
                "Make all tests pass. Ensure the Python code parses.",
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(
                out["software_semantic_result"]["required_obligation_count"], 2
            )

    def test_vague_parser_bug_language_remains_open(self):
        td, root = self.fixture(self.simple_files())
        with td:
            out = self.runv9(root, "Fix the parser bug.")
            self.assertFalse(out["pass"], out)
            self.assertTrue(out["repair_pass"], out)
            self.assertFalse(out["acceptance_stop_authorized"])
            self.assertTrue(
                out["software_semantic_result"]["semantic_residual_obligation_ids"]
            )

    def test_existing_v8_objective_grammar_is_preserved(self):
        td, root = self.fixture(self.simple_files())
        with td:
            out = self.runv9(
                root,
                "tests_pass must be true. python_parse_ok must be true.",
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["acceptance_route"], "V8_EXISTING_OBJECTIVE_ACCEPTANCE")

    def test_no_repair_in_bounds_remains_open(self):
        files = {
            "m.py": "def f(x): return x\n",
            "trace_fail.py": "from m import f\nassert f(2)==99\n",
            "test_all.py": "from m import f\nassert f(2)==99\n",
        }
        td, root = self.fixture(files)
        with td:
            out = self.runv9(
                root,
                "Make all tests pass.",
                test_paths=["trace_fail.py"],
                max_pair_candidates=10,
                mutations_per_file=4,
            )
            self.assertFalse(out["pass"], out)
            self.assertFalse(out["repair_pass"], out)
            self.assertFalse(out["acceptance_stop_authorized"])

    def test_zero_external_cognition_and_output_bound(self):
        td, root = self.fixture(self.simple_files())
        with td:
            out = self.runv9(root, "Make all tests pass.")
            self.assertEqual(out["model_dependency_count"], 0)
            self.assertEqual(
                out["external_general_purpose_model_runtime_dependency_count"], 0
            )
            self.assertEqual(out["incremental_spend_usd"], 0)
            self.assertTrue(out["output_verified"])
            self.assertTrue((root / "v9.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
