from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import textwrap
import unittest

BASE=pathlib.Path("canonical/runtime/bound_capabilities")
SPEC=importlib.util.spec_from_file_location(
    "v9c", BASE/"python_semantic_repair_acceptance_controller_v1.py"
)
v9c=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v9c)


class PythonSemanticRepairAcceptanceControllerV1Tests(unittest.TestCase):
    def fixture(self,files):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(textwrap.dedent(body),encoding="utf-8")
        return td,root

    def simple_files(self):
        return {
            "m.py":"def f(x):\n    return x < 3\n",
            "trace_fail.py":"from m import f\nassert f(3)\n",
            "trace_pass.py":"from m import f\nassert f(2)\n",
            "test_all.py":"from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n",
        }

    def runv9(self,root,task_text,**extra):
        args={
            "source_root":".",
            "test_paths":["trace_fail.py","trace_pass.py"],
            "test_argv":[sys.executable,"test_all.py"],
            "task_text":task_text,
            "output_path":"v9.json",
            "timeout_s":4,
            "max_guided_files":1,
            "max_guided_symbols_per_file":3,
            "mutations_per_file":12,
            "max_pair_candidates":120,
            "max_control_files":6,
            "max_control_symbols_per_file":6,
        }
        args.update(extra)
        return v9c.run(args,root)

    def test_supported_call_semantic_is_withheld_then_clears_after_repair(self):
        td,root=self.fixture(self.simple_files())
        original=(root/"m.py").read_bytes()
        with td:
            out=self.runv9(
                root,
                "Calling m.f with JSON arguments [3] must be true.",
            )
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertTrue(out["semantic_coverage_complete"])
            self.assertTrue(out["semantic_acceptance_withheld_from_repair_oracle"])
            self.assertTrue(out["measured_fields"]["tests_pass"])
            self.assertEqual(out["semantic_cell_count"],1)
            self.assertEqual((root/"m.py").read_bytes(),original)
            self.assertTrue(out["source_restored"])

    def test_semantic_expectation_can_falsify_regression_repair(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(
                root,
                "Calling m.f with JSON arguments [3] must be false.",
            )
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertFalse(out["acceptance_stop_authorized"])
            self.assertFalse(out["measured_fields"]["tests_pass"])

    def test_unsupported_raw_request_blocks_before_repair(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(root,"Fix the parser bug.")
            self.assertFalse(out["pass"],out)
            self.assertFalse(out["repair_attempted"])
            self.assertFalse(out["semantic_coverage_complete"])
            self.assertTrue(out["semantic_residual_obligation_ids"])

    def test_multiline_semantic_cells_all_must_clear(self):
        td,root=self.fixture(self.simple_files())
        with td:
            task=(
                "Calling m.f with JSON arguments [3] must be true.\n"
                'File "m.py" must contain exact text "return x <= 3".'
            )
            out=self.runv9(root,task)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["semantic_cell_count"],2)

    def test_multiline_one_false_cell_blocks_whole_candidate(self):
        td,root=self.fixture(self.simple_files())
        with td:
            task=(
                "Calling m.f with JSON arguments [3] must be true.\n"
                'File "m.py" must contain exact text "return x == 3".'
            )
            out=self.runv9(root,task)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertFalse(out["measured_fields"]["tests_pass"])

    def test_no_bounded_repair_does_not_run_semantic_acceptance(self):
        files={
            "m.py":"def f(x): return x\n",
            "trace_fail.py":"from m import f\nassert f(2)==99\n",
            "test_all.py":"from m import f\nassert f(2)==99\n",
        }
        td,root=self.fixture(files)
        with td:
            out=self.runv9(
                root,
                "Calling m.f with JSON arguments [2] must equal 99.",
                test_paths=["trace_fail.py"],
                max_pair_candidates=10,
                mutations_per_file=4,
            )
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_attempted"])
            self.assertFalse(out["repair_pass"])
            self.assertFalse(out["acceptance_stop_authorized"])

    def test_injection_shaped_task_blocks_before_repair(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(
                root,
                'Calling __import__("os").system with JSON arguments ["id"] must equal 0.',
            )
            self.assertFalse(out["pass"],out)
            self.assertFalse(out["repair_attempted"])

    def test_zero_external_cognition_and_verified_output(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(
                root,
                "Calling m.f with JSON arguments [3] must be true.",
            )
            self.assertTrue(out["output_verified"])
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)
            self.assertTrue((root/"v9.json").is_file())


if __name__=="__main__":
    unittest.main(verbosity=2)
