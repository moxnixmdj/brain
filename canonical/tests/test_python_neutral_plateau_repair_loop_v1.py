import importlib.util,pathlib,sys,tempfile,textwrap,unittest
SPEC=importlib.util.spec_from_file_location("plat","canonical/runtime/bound_capabilities/python_neutral_plateau_repair_loop_v1.py")
plat=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(plat)

class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
  for n,b in files.items(): (r/n).write_text(textwrap.dedent(b))
  return td,r
 def invoke(self,r,**extra):
  a={"source_root":".","test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"output_path":"result.json","timeout_s":5,"max_rounds":6,"max_files":10,"max_candidates_per_file":60,"max_total_candidates":2500,"max_plateau_depth":3,"max_plateau_states":180,"max_plateau_candidates":1800}
  a.update(extra); return plat.run(a,r)
 def test_two_edit_neutral_plateau(self):
  td,r=self.fixture({
   "f.py":"def f():\n return False\n","g.py":"def g():\n return False\n",
   "combo.py":"from f import f\nfrom g import g\ndef combo():\n return f() and g()\n",
   "test_all.py":"""import unittest
from combo import combo
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(combo(),True)
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.invoke(r); self.assertTrue(o["pass"],o); self.assertEqual(o["accepted_edit_count"],2)
   self.assertEqual(o["rounds"][0]["mode"],"NEUTRAL_PLATEAU"); self.assertEqual(o["rounds"][0]["plateau_depth"],2)
   self.assertTrue(o["source_restored"])
 def test_three_edit_neutral_plateau(self):
  td,r=self.fixture({
   "f.py":"def f():\n return False\n","g.py":"def g():\n return False\n","h.py":"def h():\n return False\n",
   "combo.py":"from f import f\nfrom g import g\nfrom h import h\ndef combo():\n return (f(),g(),h())\n",
   "test_all.py":"""import unittest
from combo import combo
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(combo(),(True,True,True))
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.invoke(r); self.assertTrue(o["pass"],o); self.assertEqual(o["accepted_edit_count"],3)
   self.assertEqual(o["rounds"][0]["plateau_depth"],3); self.assertEqual([x["failure_score"] for x in o["final_verification_replays"]],[0,0])
 def test_depth_two_cannot_solve_three_edit_plateau(self):
  td,r=self.fixture({
   "f.py":"def f():\n return False\n","g.py":"def g():\n return False\n","h.py":"def h():\n return False\n",
   "combo.py":"from f import f\nfrom g import g\nfrom h import h\ndef combo():\n return (f(),g(),h())\n",
   "test_all.py":"""import unittest
from combo import combo
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(combo(),(True,True,True))
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.invoke(r,max_plateau_depth=2); self.assertFalse(o["pass"]); self.assertTrue(o["source_restored"])
 def test_strict_single_preferred(self):
  td,r=self.fixture({"m.py":"def f(x):\n return x < 3\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(f(3),True)
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.invoke(r); self.assertTrue(o["pass"]); self.assertEqual(o["rounds"][0]["mode"],"STRICT_SINGLE")
 def test_mixed_strict_then_plateau(self):
  td,r=self.fixture({
   "n.py":"def n():\n return 4\n","f.py":"def f():\n return False\n","g.py":"def g():\n return False\n",
   "combo.py":"from f import f\nfrom g import g\ndef combo():\n return f() and g()\n",
   "test_all.py":"""import unittest
from n import n
from combo import combo
class X(unittest.TestCase):
 def test_n(self): self.assertEqual(n(),7)
 def test_c(self): self.assertEqual(combo(),True)
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.invoke(r); self.assertTrue(o["pass"],o); self.assertEqual([x["mode"] for x in o["rounds"]],["STRICT_SINGLE","NEUTRAL_PLATEAU"])
 def test_no_solution_fail_closed(self):
  td,r=self.fixture({"m.py":"def f(x):\n return x\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(f(2),9)
if __name__=='__main__': unittest.main()
"""})
  with td:
   b=(r/"m.py").read_bytes(); o=self.invoke(r); self.assertFalse(o["pass"]); self.assertTrue(o["source_restored"]); self.assertEqual((r/"m.py").read_bytes(),b)
 def test_already_passing_rejected(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(f(),1)
if __name__=='__main__': unittest.main()
"""})
  with td:
   with self.assertRaisesRegex(plat.RepairLoopError,"BASELINE_ALREADY_PASSES"): self.invoke(r)
 def test_path_escape_rejected(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n","test_all.py":"raise AssertionError()\n"})
  with td:
   with self.assertRaisesRegex(RuntimeError,"PATH_OUTSIDE_REPOSITORY"): self.invoke(r,source_root="../")
 def test_zero_model_zero_spend(self):
  td,r=self.fixture({"m.py":"def f():\n return False\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(f(),True)
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.invoke(r); self.assertTrue(o["pass"]); self.assertEqual(o["model_dependency_count"],0); self.assertEqual(o["external_capability_provider_count"],0); self.assertEqual(o["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
