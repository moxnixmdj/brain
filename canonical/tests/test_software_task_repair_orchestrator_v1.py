import importlib.util, pathlib, sys, tempfile, textwrap, unittest

SPEC=importlib.util.spec_from_file_location("orch","canonical/runtime/bound_capabilities/software_task_repair_orchestrator_v1.py")
orch=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(orch)

class T(unittest.TestCase):
    def fixture(self,files,test):
        td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
        for name,content in files.items(): (r/name).write_text(content)
        (r/"test_app.py").write_text(textwrap.dedent(test))
        return td,r

    def run_orch(self,r,task,**extra):
        a={"task_text":task,"test_paths":["test_app.py"],"test_argv":[sys.executable,"test_app.py"],"output_path":"result.json","max_candidates":800,"beam_width":20,"max_edits":2,"timeout_s":4}
        a.update(extra)
        return orch.run(a,r)

    def test_two_file_two_edit_end_to_end(self):
        files={"a.py":"def f(x):\n    return x < 3\n","b.py":"def g():\n    return False\n"}
        test="""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(3),True)
 def test_b(self): self.assertEqual(g(),True)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_orch(r,"f must return true and g must return true.",source_paths=["a.py","b.py"])
            self.assertTrue(out["pass"])
            self.assertTrue(out["acceptance_complete"])
            self.assertTrue(out["repair_executed"])
            self.assertEqual(out["winning_edit_count"],2)
            self.assertIn("a.py",out["unified_diff"])
            self.assertIn("b.py",out["unified_diff"])
            self.assertEqual((r/"a.py").read_text(),files["a.py"])
            self.assertEqual((r/"b.py").read_text(),files["b.py"])

    def test_incomplete_acceptance_blocks_repair(self):
        files={"a.py":"def f():\n    return 4\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_orch(r,"f must return 7 without changing api.",source_paths=["a.py"])
            self.assertFalse(out["pass"])
            self.assertFalse(out["acceptance_complete"])
            self.assertFalse(out["repair_executed"])
            self.assertNotIn("unified_diff",out)
            self.assertEqual((r/"a.py").read_text(),files["a.py"])

    def test_already_satisfied(self):
        files={"a.py":"def f():\n    return 7\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_orch(r,"f must return 7.",source_paths=["a.py"])
            self.assertTrue(out["pass"])
            self.assertEqual(out["status"],"PASS__EXPLICIT_TASK_ALREADY_SATISFIED_BY_BOUND_TESTS")
            self.assertEqual(out["repair_action"],"NO_PATCH_REQUIRED")

    def test_auto_source_inference(self):
        files={"a.py":"def f():\n    return 4\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_orch(r,"f must return 7.")
            self.assertTrue(out["pass"])
            self.assertEqual(out["repair_source_selection"],"INFERRED_FROM_TRACEBACK_AND_TEST_IMPORTS")

    def test_bounded_no_candidate(self):
        files={"a.py":"def f(x):\n    return x\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(2),8)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_orch(r,"f must return 8.",source_paths=["a.py"],max_candidates=100)
            self.assertFalse(out["pass"])
            self.assertTrue(out["acceptance_complete"])
            self.assertTrue(out["repair_executed"])
            self.assertEqual(out["status"],"OPEN__EXPLICIT_TASK_BOUND__NO_VERIFIED_CANDIDATE_IN_BOUNDED_REPAIR")

    def test_output_escape_rejected(self):
        files={"a.py":"def f():\n    return 4\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
"""
        td,r=self.fixture(files,test)
        with td:
            with self.assertRaisesRegex(orch.SoftwareTaskRepairError,"OUTPUT_PATH_OUTSIDE_REPOSITORY"):
                self.run_orch(r,"f must return 7.",source_paths=["a.py"],output_path="../result.json")

    def test_source_escape_rejected_downstream(self):
        files={"a.py":"def f():\n    return 4\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
"""
        td,r=self.fixture(files,test)
        with td:
            with self.assertRaisesRegex(RuntimeError,"PATH_INVALID"):
                self.run_orch(r,"f must return 7.",source_paths=["../x.py"])

    def test_zero_model_zero_spend(self):
        files={"a.py":"def f():\n    return 4\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_orch(r,"f must return 7.",source_paths=["a.py"])
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_capability_provider_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
