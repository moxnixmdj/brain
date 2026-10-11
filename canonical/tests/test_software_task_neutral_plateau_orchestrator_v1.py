import importlib.util,pathlib,sys,tempfile,textwrap,unittest
SPEC=importlib.util.spec_from_file_location("orch","canonical/runtime/bound_capabilities/software_task_neutral_plateau_orchestrator_v1.py")
orch=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(orch)

class T(unittest.TestCase):
 def fixture(self,files,test):
  td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
  for n,b in files.items(): (r/n).write_text(b)
  (r/"test_all.py").write_text(textwrap.dedent(test)); return td,r
 def run_o(self,r,task,**extra):
  a={"task_text":task,"test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"source_root":".","output_path":"result.json","timeout_s":5,"max_rounds":8,"max_files":12,"max_candidates_per_file":80,"max_total_candidates":3000,"max_plateau_depth":3,"max_plateau_states":220,"max_plateau_candidates":2200}
  a.update(extra); return orch.run(a,r)
 def test_two_edit_neutral_end_to_end(self):
  files={"f.py":"def f():\n return False\n","g.py":"def g():\n return False\n","combo.py":"from f import f\nfrom g import g\ndef combo():\n return f() and g()\n"}
  test="""import unittest
from combo import combo
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(combo(),True)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"combo must return true."); self.assertTrue(o["pass"],o)
   self.assertTrue(any(x["mode"]=="NEUTRAL_PLATEAU" for x in o["repair_rounds"])); self.assertTrue(o["source_restored"])
 def test_three_edit_neutral_end_to_end(self):
  files={"f.py":"def f():\n return False\n","g.py":"def g():\n return False\n","h.py":"def h():\n return False\n","combo.py":"from f import f\nfrom g import g\nfrom h import h\ndef combo():\n return all([f(),g(),h()])\n"}
  test="""import unittest
from combo import combo
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(combo(),True)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"combo must return true."); self.assertTrue(o["pass"],o)
   self.assertEqual(o["accepted_edit_count"],3); self.assertEqual(o["repair_rounds"][0]["plateau_depth"],3)
 def test_strict_single_path(self):
  files={"label.py":"def label():\n return 'old'\n"}; test="""import unittest
from label import label
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(label(),'new')
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"label must return 'new'."); self.assertTrue(o["pass"]); self.assertEqual(o["repair_rounds"][0]["mode"],"STRICT_SINGLE")
 def test_incomplete_acceptance_blocks_repair(self):
  files={"m.py":"def value():\n return 1\n"}; test="""import unittest
from m import value
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(value(),2)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"value must return 2 while preserving memory usage."); self.assertFalse(o["pass"]); self.assertFalse(o["repair_executed"]); self.assertFalse(o["acceptance_complete"])
 def test_already_satisfied(self):
  files={"m.py":"def value():\n return 2\n"}; test="""import unittest
from m import value
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(value(),2)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"value must return 2."); self.assertTrue(o["pass"]); self.assertEqual(o["repair_action"],"NO_PATCH_REQUIRED")
 def test_no_solution(self):
  files={"m.py":"def value(x):\n return x\n"}; test="""import unittest
from m import value
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(value(2),11)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"value must return 11."); self.assertFalse(o["pass"]); self.assertTrue(o["repair_executed"]); self.assertTrue(o["source_restored"])
 def test_source_root_escape(self):
  td,r=self.fixture({"m.py":"def value(): return 1\n"},"""import unittest
from m import value
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(value(),2)
""")
  with td:
   with self.assertRaisesRegex(orch.SoftwareTaskRepairError,"SOURCE_ROOT_OUTSIDE_REPOSITORY"): self.run_o(r,"value must return 2.",source_root="../")
 def test_output_escape(self):
  td,r=self.fixture({"m.py":"def value(): return 1\n"},"""import unittest
from m import value
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(value(),2)
""")
  with td:
   with self.assertRaisesRegex(orch.SoftwareTaskRepairError,"OUTPUT_PATH_OUTSIDE_REPOSITORY"): self.run_o(r,"value must return 2.",output_path="../x.json")
 def test_zero_model_zero_spend(self):
  files={"m.py":"def value():\n return False\n"}; test="""import unittest
from m import value
class X(unittest.TestCase):
 def test_x(self): self.assertEqual(value(),True)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"value must return true."); self.assertTrue(o["pass"]); self.assertEqual(o["model_dependency_count"],0); self.assertEqual(o["external_capability_provider_count"],0); self.assertEqual(o["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
