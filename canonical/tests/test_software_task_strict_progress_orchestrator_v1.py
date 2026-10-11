import importlib.util,pathlib,sys,tempfile,textwrap,unittest
SPEC=importlib.util.spec_from_file_location("orch","canonical/runtime/bound_capabilities/software_task_strict_progress_orchestrator_v1.py")
orch=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(orch)

class T(unittest.TestCase):
 def fixture(self,files,test):
  td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
  for n,b in files.items(): (r/n).write_text(b)
  (r/"test_all.py").write_text(textwrap.dedent(test))
  return td,r
 def run_o(self,r,task,**extra):
  a={"task_text":task,"test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"output_path":"result.json","source_root":".","timeout_s":5,"max_rounds":6,"max_files":8,"max_candidates_per_file":80,"max_total_candidates":500}
  a.update(extra); return orch.run(a,r)
 def test_two_failure_strict_progress_end_to_end(self):
  files={"a.py":"def f(x):\n    return x < 3\n","b.py":"def g():\n    return 4\n"}
  test="""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(3),True)
 def test_b(self): self.assertEqual(g(),7)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"f must return true and g must return 7.")
   self.assertTrue(o["pass"],o); self.assertEqual(o["accepted_edit_count"],2)
   self.assertEqual([x["score_after"] for x in o["accepted_edits"]],[1,0])
   self.assertEqual([x["failure_score"] for x in o["verification_replays"]],[0,0])
   self.assertTrue(o["source_restored"])
   self.assertEqual((r/"a.py").read_text(),files["a.py"]); self.assertEqual((r/"b.py").read_text(),files["b.py"])
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
   o=self.run_o(r,"f must return 7 without changing performance.")
   self.assertFalse(o["pass"]); self.assertFalse(o["acceptance_complete"]); self.assertFalse(o["repair_executed"]); self.assertNotIn("patches",o)
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
   o=self.run_o(r,"f must return 7.")
   self.assertTrue(o["pass"]); self.assertEqual(o["repair_action"],"NO_PATCH_REQUIRED")
 def test_auto_localization_string(self):
  files={"label.py":"def label():\n    return 'old'\n"}
  test="""import unittest
from label import label
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(label(),'new')
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"label must return 'new'.")
   self.assertTrue(o["pass"],o); self.assertEqual(o["accepted_edit_count"],1); self.assertIn("label.py",o["patches"][0]["source_path"])
 def test_no_solution_fails_closed(self):
  files={"scale.py":"def double(x):\n    return x\n"}
  test="""import unittest
from scale import double
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(double(3),6)
if __name__=='__main__': unittest.main()
"""
  td,r=self.fixture(files,test)
  with td:
   o=self.run_o(r,"double must return 6.")
   self.assertFalse(o["pass"]); self.assertTrue(o["acceptance_complete"]); self.assertTrue(o["repair_executed"]); self.assertTrue(o["source_restored"])
 def test_source_root_escape(self):
  td,r=self.fixture({"a.py":"def f(): return 1\n"},"""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),2)
""")
  with td:
   with self.assertRaisesRegex(orch.SoftwareTaskRepairError,"SOURCE_ROOT_OUTSIDE_REPOSITORY"): self.run_o(r,"f must return 2.",source_root="../")
 def test_output_escape(self):
  td,r=self.fixture({"a.py":"def f(): return 1\n"},"""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),2)
""")
  with td:
   with self.assertRaisesRegex(orch.SoftwareTaskRepairError,"OUTPUT_PATH_OUTSIDE_REPOSITORY"): self.run_o(r,"f must return 2.",output_path="../r.json")
 def test_zero_model_zero_spend(self):
  td,r=self.fixture({"a.py":"def f():\n    return False\n"},"""import unittest
from a import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),True)
if __name__=='__main__': unittest.main()
""")
  with td:
   o=self.run_o(r,"f must return true.")
   self.assertTrue(o["pass"]); self.assertEqual(o["model_dependency_count"],0); self.assertEqual(o["external_capability_provider_count"],0); self.assertEqual(o["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
