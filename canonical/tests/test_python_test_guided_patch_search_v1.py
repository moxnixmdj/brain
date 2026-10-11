import importlib.util, pathlib, sys, tempfile, textwrap, unittest
SPEC=importlib.util.spec_from_file_location("ptg","canonical/runtime/bound_capabilities/python_test_guided_patch_search_v1.py")
ptg=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ptg)
class T(unittest.TestCase):
 def fixture(self,source,test):
  td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
  (r/"m.py").write_text(source); (r/"test_m.py").write_text(textwrap.dedent(test))
  return td,r
 def run_search(self,r,**extra):
  a={"source_path":"m.py","test_paths":["test_m.py"],"test_argv":[sys.executable,"test_m.py"],"output_path":"result.json","max_candidates":300,"timeout_s":4}; a.update(extra); return ptg.run(a,r)
 def test_boundary(self):
  s="def f(x):\n    return x < 3\n"; td,r=self.fixture(s,"""import unittest
from m import f
class X(unittest.TestCase):
 def test_boundary(self): self.assertTrue(f(3)); self.assertFalse(f(4))
if __name__=='__main__': unittest.main()
""")
  with td:
   o=self.run_search(r); self.assertTrue(o["pass"]); self.assertEqual(o["winning_mutation"]["kind"],"COMPARE_SWAP"); self.assertEqual((r/"m.py").read_text(),s)
 def test_bool(self):
  td,r=self.fixture("def f():\n    return False\n","""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
""")
  with td: self.assertIn("return True",self.run_search(r)["unified_diff"])
 def test_num(self):
  td,r=self.fixture("def f():\n    return 4\n","""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),7)
if __name__=='__main__': unittest.main()
""")
  with td:
   o=self.run_search(r); self.assertTrue(o["pass"]); self.assertEqual(o["model_dependency_count"],0); self.assertIn("return 7",o["unified_diff"])
 def test_string(self):
  td,r=self.fixture("def f():\n    return 'bad'\n","""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),'good')
if __name__=='__main__': unittest.main()
""")
  with td: self.assertIn("return 'good'",self.run_search(r)["unified_diff"])
 def test_no_solution(self):
  s="def f(x):\n    return x\n"; td,r=self.fixture(s,"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(2),4)
if __name__=='__main__': unittest.main()
""")
  with td:
   o=self.run_search(r); self.assertFalse(o["pass"]); self.assertTrue(o["source_restored"]); self.assertEqual((r/"m.py").read_text(),s)
 def test_baseline_pass_rejected(self):
  td,r=self.fixture("def f():\n    return 1\n","""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),1)
if __name__=='__main__': unittest.main()
""")
  with td:
   with self.assertRaisesRegex(ptg.PatchSearchError,"BASELINE_ALREADY_PASSES"): self.run_search(r)
 def test_path_escape(self):
  td,r=self.fixture("def f():\n    return 0\n","""import unittest
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(False)
if __name__=='__main__': unittest.main()
""")
  with td:
   with self.assertRaisesRegex(ptg.PatchSearchError,"PATH_INVALID"): self.run_search(r,source_path="../x.py")
 def test_deterministic(self):
  td,r=self.fixture("def f(x):\n    return x > 2\n","""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f(2)); self.assertFalse(f(1))
if __name__=='__main__': unittest.main()
""")
  with td:
   a=self.run_search(r); b=self.run_search(r); self.assertEqual(a["candidate_source_sha256"],b["candidate_source_sha256"]); self.assertEqual(a["unified_diff"],b["unified_diff"])
if __name__=="__main__": unittest.main(verbosity=2)
