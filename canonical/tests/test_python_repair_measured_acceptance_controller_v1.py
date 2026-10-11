from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import textwrap
import unittest

BASE=pathlib.Path("canonical/runtime/bound_capabilities")
SPEC=importlib.util.spec_from_file_location(
    "v8", BASE/"python_repair_measured_acceptance_controller_v1.py"
)
v8=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v8)


class RepairMeasuredAcceptanceV8Tests(unittest.TestCase):
    def fixture(self, files):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(textwrap.dedent(body),encoding="utf-8")
        return td,root

    def runv8(self,root,task_text="tests_pass must be true.\npython_parse_ok must be true.",**extra):
        args={
            "source_root":".",
            "test_paths":["trace_fail.py","trace_pass.py"],
            "test_argv":[sys.executable,"test_all.py"],
            "task_text":task_text,
            "output_path":"v8.json",
            "timeout_s":4,
            "max_guided_files":1,
            "max_guided_symbols_per_file":3,
            "mutations_per_file":12,
            "max_pair_candidates":100,
            "max_control_files":6,
            "max_control_symbols_per_file":6,
        }
        args.update(extra)
        return v8.run(args,root)

    def simple_files(self):
        return {
            "m.py":"def f(x):\n    return x < 3\n",
            "trace_fail.py":"from m import f\nassert f(3)\n",
            "trace_pass.py":"from m import f\nassert f(2)\n",
            "test_all.py":"from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n",
        }

    def test_atomic_single_repair_realization_measurement_and_acceptance(self):
        files=self.simple_files()
        td,root=self.fixture(files)
        original=(root/"m.py").read_bytes()
        with td:
            out=self.runv8(root)
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["repair_pass"],out)
            self.assertTrue(out["acceptance_stop_authorized"],out)
            self.assertEqual(out["acceptance_status"],"PASS__MEASUREMENT_BOUND_OBJECTIVE_ACCEPTANCE")
            self.assertTrue(out["measured_fields"]["tests_pass"])
            self.assertTrue(out["measured_fields"]["python_parse_ok"])
            self.assertEqual((root/"m.py").read_bytes(),original)
            self.assertTrue(out["source_restored"])
            self.assertTrue(out["candidate_subject_snapshot_sha256"])

    def test_semantic_residual_blocks_stop_even_after_verified_repair(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv8(root,task_text="Fix the parser bug.")
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"],out)
            self.assertFalse(out["acceptance_stop_authorized"],out)
            self.assertEqual(out["acceptance_status"],"OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS")
            self.assertTrue(out["semantic_residual_obligation_ids"])

    def test_objective_false_requirement_falsifies_candidate(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv8(root,task_text="tests_pass must be false.")
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"],out)
            self.assertFalse(out["acceptance_stop_authorized"],out)

    def test_no_repair_in_bounds_does_not_measure_acceptance(self):
        files={
            "m.py":"def f(x): return x\n",
            "trace_fail.py":"from m import f\nassert f(2)==99\n",
            "test_all.py":"from m import f\nassert f(2)==99\n",
        }
        td,root=self.fixture(files)
        with td:
            out=self.runv8(
                root,
                test_paths=["trace_fail.py"],
                max_pair_candidates=10,
                mutations_per_file=4,
            )
            self.assertFalse(out["pass"],out)
            self.assertFalse(out["repair_pass"],out)
            self.assertFalse(out["acceptance_stop_authorized"],out)
            self.assertEqual(out["status"],"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH")

    def test_coupled_cross_file_repair_is_realized_and_measured(self):
        files={
            "a.py":"def a(x):\n    return x < 3\n",
            "b.py":"def b(y):\n    return y > 5\n",
            "trace_fail.py":"from a import a\nfrom b import b\nassert a(3) and b(5)\n",
            "trace_pass.py":"from a import a\nfrom b import b\nassert a(2) and b(6)\n",
            "test_all.py":"from a import a\nfrom b import b\nassert a(3) and b(5)\nassert a(2) and b(6)\nassert not a(4)\nassert not b(4)\n",
        }
        td,root=self.fixture(files)
        a0=(root/"a.py").read_bytes();b0=(root/"b.py").read_bytes()
        with td:
            out=self.runv8(root,max_guided_files=2,max_pair_candidates=300)
            self.assertTrue(out["pass"],out)
            self.assertEqual(len(out["realized_patches"]),2)
            self.assertEqual((root/"a.py").read_bytes(),a0)
            self.assertEqual((root/"b.py").read_bytes(),b0)

    def test_output_is_verified_and_zero_external_cognition(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv8(root)
            self.assertTrue(out["output_verified"])
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)
            self.assertTrue((root/"v8.json").is_file())

    def test_source_root_escape_rejected(self):
        td,root=self.fixture(self.simple_files())
        with td:
            with self.assertRaisesRegex(v8.RepairAcceptanceError,"SOURCE_ROOT_OUTSIDE"):
                self.runv8(root,source_root="../")

    def test_patch_realization_rejects_hash_mismatch(self):
        td,root=self.fixture({"m.py":"x=1\n"})
        with td, tempfile.TemporaryDirectory() as td2:
            candidate=pathlib.Path(td2)/"candidate"
            with self.assertRaisesRegex(v8.RepairAcceptanceError,"PATCH_ORIGINAL_SHA_MISMATCH"):
                v8._realize_candidate(
                    root,root,
                    [{
                        "source_path":"m.py",
                        "original_sha256":"0"*64,
                        "candidate_sha256":"1"*64,
                        "unified_diff":"--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-x=1\n+x=2\n",
                    }],
                    candidate,
                )


if __name__=="__main__":
    unittest.main(verbosity=2)
