import importlib.util, pathlib, sys, tempfile, textwrap, unittest

SPEC=importlib.util.spec_from_file_location("loop","canonical/runtime/bound_capabilities/python_test_guided_repair_loop_v1.py")
loop=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(loop)

class T(unittest.TestCase):
    def fixture(self,files,test):
        td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
        for name,content in files.items(): (r/name).write_text(content)
        (r/"test_app.py").write_text(textwrap.dedent(test))
        return td,r

    def run_loop(self,r,**extra):
        a={"test_paths":["test_app.py"],"test_argv":[sys.executable,"test_app.py"],"output_path":"result.json","max_candidates":800,"beam_width":20,"max_edits":2,"timeout_s":4}
        a.update(extra)
        return loop.run(a,r)

    def test_two_file_two_edit_explicit(self):
        files={"a.py":"def f(x):\n    return x < 3\n","b.py":"def g():\n    return False\n"}
        test="""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(f(3))
 def test_b(self): self.assertTrue(g())
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_loop(r,source_paths=["a.py","b.py"])
            self.assertTrue(out["pass"])
            self.assertEqual(out["winning_edit_count"],2)
            self.assertIn("a.py",out["unified_diff"])
            self.assertIn("b.py",out["unified_diff"])
            self.assertEqual((r/"a.py").read_text(),files["a.py"])
            self.assertEqual((r/"b.py").read_text(),files["b.py"])

    def test_two_file_auto_inference(self):
        files={"a.py":"def f():\n    return 4\n","b.py":"def g():\n    return 'bad'\n"}
        test="""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
 def test_b(self): self.assertEqual(g(),'good')
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_loop(r)
            self.assertTrue(out["pass"])
            self.assertEqual(out["source_selection"],"INFERRED_FROM_TRACEBACK_AND_TEST_IMPORTS")
            self.assertEqual(set(out["source_paths"]),{"a.py","b.py"})

    def test_one_edit(self):
        files={"a.py":"def f():\n    return False\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_loop(r,source_paths=["a.py"])
            self.assertTrue(out["pass"])
            self.assertEqual(out["winning_edit_count"],1)

    def test_no_solution_fail_closed(self):
        files={"a.py":"def f(x):\n    return x\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(2),8)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_loop(r,source_paths=["a.py"],max_candidates=100)
            self.assertFalse(out["pass"])
            self.assertTrue(out["source_restored"])

    def test_baseline_pass_rejected(self):
        files={"a.py":"def f():\n    return 1\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),1)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            with self.assertRaisesRegex(loop.RepairLoopError,"BASELINE_ALREADY_PASSES"):
                self.run_loop(r,source_paths=["a.py"])

    def test_path_escape(self):
        files={"a.py":"def f():\n    return 0\n"}
        test="""import unittest
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(False)
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            with self.assertRaisesRegex(loop.RepairLoopError,"PATH_INVALID"):
                self.run_loop(r,source_paths=["../x.py"])

    def test_deterministic(self):
        files={"a.py":"def f(x):\n    return x > 2\n","b.py":"def g():\n    return False\n"}
        test="""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(f(2))
 def test_b(self): self.assertTrue(g())
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            a=self.run_loop(r,source_paths=["a.py","b.py"])
            b=self.run_loop(r,source_paths=["a.py","b.py"])
            self.assertEqual(a["candidate_state_sha256"],b["candidate_state_sha256"])
            self.assertEqual(a["unified_diff"],b["unified_diff"])

    def test_zero_model_zero_spend(self):
        files={"a.py":"def f():\n    return False\n"}
        test="""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
"""
        td,r=self.fixture(files,test)
        with td:
            out=self.run_loop(r,source_paths=["a.py"])
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_capability_provider_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
