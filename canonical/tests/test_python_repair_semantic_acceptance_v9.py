from __future__ import annotations

import pathlib
import sys
import tempfile
import textwrap
import unittest

from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement
from canonical.runtime.bound_capabilities import python_request_semantic_acceptance_cells_v1 as cells
from canonical.runtime import python_request_acceptance_union_v1 as union
from canonical.runtime.bound_capabilities import python_repair_semantic_acceptance_controller_v1 as v9


class CodingV9SemanticAcceptanceTests(unittest.TestCase):
    def fixture(self, files):
        td=tempfile.TemporaryDirectory()
        root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(body),encoding="utf-8")
        return td,root

    def simple_files(self):
        return {
            "m.py":"def f(x):\n    return x < 3\n",
            "trace_fail.py":"from m import f\nassert f(3)\n",
            "trace_pass.py":"from m import f\nassert f(2)\n",
            "test_all.py":"from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n",
        }

    def test_semantic_cell_file_content_and_scope_measure_candidate_bytes(self):
        td,base=self.fixture({"m.py":"def f(x):\n    return x < 3\n"})
        with td,tempfile.TemporaryDirectory() as cd:
            cand=pathlib.Path(cd);(cand/"m.py").write_text("def f(x):\n    return x <= 3\n",encoding="utf-8")
            task='File "m.py" must contain "return x <= 3". Only modify "m.py".'
            out=cells.evaluate_cells(task,baseline_root=base,candidate_root=cand)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["changed_paths"],["m.py"])
            self.assertFalse(out["unbound_obligation_ids"])

    def test_semantic_cell_unknown_request_stays_unbound(self):
        td,base=self.fixture({"m.py":"x=1\n"})
        with td,tempfile.TemporaryDirectory() as cd:
            cand=pathlib.Path(cd);(cand/"m.py").write_text("x=1\n",encoding="utf-8")
            out=cells.evaluate_cells("Preserve compatibility with old callers.",baseline_root=base,candidate_root=cand)
            self.assertTrue(out["pass"])
            self.assertTrue(out["unbound_obligation_ids"])

    def test_semantic_cell_candidate_snapshot_mismatch_fails_closed(self):
        td,base=self.fixture({"m.py":"x=1\n"})
        with td,tempfile.TemporaryDirectory() as cd:
            cand=pathlib.Path(cd);(cand/"m.py").write_text("x=2\n",encoding="utf-8")
            out=cells.evaluate_cells('File "m.py" must exist.',baseline_root=base,candidate_root=cand,expected_candidate_snapshot_sha256="0"*64)
            self.assertFalse(out["pass"])
            self.assertIn("CANDIDATE_SNAPSHOT_MISMATCH",out["errors"][0])

    def test_acceptance_union_combines_measured_objective_and_semantic_cell(self):
        td,base=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"from m import f\nassert f()==1\n",
        })
        with td,tempfile.TemporaryDirectory() as td2:
            temp=pathlib.Path(td2);cand=temp/"candidate"
            import shutil;shutil.copytree(base,cand)
            m=measurement.run({"source_root":"candidate","test_paths":["test_m.py"],"test_argv":[sys.executable,"test_m.py"],"output_path":"receipt.json","timeout_s":5},temp)
            _,bsha=measurement._tree_manifest(base,max_files=20000,max_bytes=500_000_000)
            task='tests_pass must be true. File "m.py" must contain "return 1".'
            out=union.evaluate_union(task,measurement_receipt_path="receipt.json",receipt_root=temp,baseline_root=base,candidate_root=cand,expected_baseline_snapshot_sha256=bsha)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["required_obligation_count"],out["passed_obligation_count"])
            self.assertFalse(out["unbound_obligation_ids"])

    def test_acceptance_union_semantic_failure_blocks_objective_success(self):
        td,base=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"from m import f\nassert f()==1\n",
        })
        with td,tempfile.TemporaryDirectory() as td2:
            temp=pathlib.Path(td2);cand=temp/"candidate"
            import shutil;shutil.copytree(base,cand)
            measurement.run({"source_root":"candidate","test_paths":["test_m.py"],"test_argv":[sys.executable,"test_m.py"],"output_path":"receipt.json","timeout_s":5},temp)
            _,bsha=measurement._tree_manifest(base,max_files=20000,max_bytes=500_000_000)
            out=union.evaluate_union('tests_pass must be true. File "m.py" must contain "return 9".',measurement_receipt_path="receipt.json",receipt_root=temp,baseline_root=base,candidate_root=cand,expected_baseline_snapshot_sha256=bsha)
            self.assertFalse(out["pass"])
            self.assertTrue(out["failed_obligation_ids"])

    def test_acceptance_union_unrecognized_semantics_remain_blocking(self):
        td,base=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"from m import f\nassert f()==1\n",
        })
        with td,tempfile.TemporaryDirectory() as td2:
            temp=pathlib.Path(td2);cand=temp/"candidate"
            import shutil;shutil.copytree(base,cand)
            measurement.run({"source_root":"candidate","test_paths":["test_m.py"],"test_argv":[sys.executable,"test_m.py"],"output_path":"receipt.json","timeout_s":5},temp)
            _,bsha=measurement._tree_manifest(base,max_files=20000,max_bytes=500_000_000)
            out=union.evaluate_union("tests_pass must be true. Preserve compatibility with historic clients.",measurement_receipt_path="receipt.json",receipt_root=temp,baseline_root=base,candidate_root=cand,expected_baseline_snapshot_sha256=bsha)
            self.assertFalse(out["pass"])
            self.assertTrue(out["unbound_obligation_ids"])

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
            "max_pair_candidates":100,
            "max_control_files":6,
            "max_control_symbols_per_file":6,
        }
        args.update(extra)
        return v9.run(args,root)

    def test_v9_atomic_repair_requires_objective_plus_semantic_acceptance(self):
        td,root=self.fixture(self.simple_files());original=(root/"m.py").read_bytes()
        with td:
            out=self.runv9(root,'tests_pass must be true. File "m.py" must contain "return x <= 3".')
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertTrue(out["acceptance_stop_authorized"])
            self.assertEqual((root/"m.py").read_bytes(),original)
            self.assertTrue(out["source_restored"])

    def test_v9_scope_only_modify_is_measured_against_pre_repair_baseline(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(root,'tests_pass must be true. Only modify "m.py".')
            self.assertTrue(out["pass"],out)
            self.assertEqual([x["source_path"] for x in out["realized_patches"]],["m.py"])

    def test_v9_negative_scope_blocks_otherwise_valid_repair(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(root,'tests_pass must be true. Must not modify "m.py".')
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertFalse(out["acceptance_stop_authorized"])
            self.assertTrue(out["failed_obligation_ids"])

    def test_v9_unsupported_semantic_request_blocks_after_successful_repair(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(root,"tests_pass must be true. Preserve compatibility with unknown external callers.")
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertFalse(out["acceptance_stop_authorized"])
            self.assertTrue(out["unbound_obligation_ids"])

    def test_v9_semantic_negative_content_can_falsify_repaired_candidate(self):
        td,root=self.fixture(self.simple_files())
        with td:
            out=self.runv9(root,'tests_pass must be true. File "m.py" must not contain "return x <= 3".')
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["repair_pass"])
            self.assertTrue(out["failed_obligation_ids"])

    def test_v9_zero_external_runtime_cognition(self):
        self.assertEqual(cells.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(cells.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(union.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(union.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(v9.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(v9.EXTERNAL_MODEL_RUNTIME_CALLS,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
