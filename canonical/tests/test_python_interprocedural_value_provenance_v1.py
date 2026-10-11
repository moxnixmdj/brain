import importlib.util,pathlib,tempfile,textwrap,unittest
SPEC=importlib.util.spec_from_file_location("prov","canonical/runtime/bound_capabilities/python_interprocedural_value_provenance_v1.py");prov=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(prov)
class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
  for n,b in files.items():p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(b))
  return td,r
 def runp(self,r,tests,**extra):
  a={"source_root":".","test_paths":tests,"output_path":"prov.json","timeout_s":4,"max_trace_events":20000};a.update(extra);return prov.run(a,r)
 def test_fail_only_call_edge_ranked(self):
  td,r=self.fixture({"m.py":"""def helper(x): return x+1
def buggy(x): return helper(x)*2
def good(x): return x+1
""","test_fail.py":"from m import buggy\nassert buggy(2)==8\n","test_pass.py":"from m import good\nassert good(2)==3\n"})
  with td:
   o=self.runp(r,["test_fail.py","test_pass.py"]);self.assertTrue(o["pass"]);self.assertTrue(any(x["callee"]["function"]=="helper" and "FAIL_ONLY_CALL_EDGE" in x["reasons"] for x in o["ranked_call_edges"]))
 def test_value_divergence_observed(self):
  td,r=self.fixture({"m.py":"""def helper(x): return x+1
def f(x): return helper(x)
""","test_fail.py":"from m import f\nassert f(2)==9\n","test_pass.py":"from m import f\nassert f(1)==2\n"})
  with td:
   o=self.runp(r,["test_fail.py","test_pass.py"]);edge=[x for x in o["ranked_call_edges"] if x["callee"]["function"]=="helper"][0];self.assertTrue(edge["argument_observation_differs"]);self.assertTrue(edge["return_observation_differs"])
 def test_static_assignment_binding(self):
  td,r=self.fixture({"m.py":"""def helper(x): return x+1
def f(x):
 y=helper(x)
 return y*2
""","test_fail.py":"from m import f\nassert f(2)==8\n"})
  with td:
   o=self.runp(r,["test_fail.py"]);h=[x for x in o["interprocedural_hypotheses"] if x["callee_symbol"]=="helper"][0];self.assertEqual(h["assigned_to"],["y"]);self.assertIn("x",h["argument_loads"])
 def test_no_failing_rejected(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n","test_pass.py":"from m import f\nassert f()==1\n"})
  with td:
   with self.assertRaisesRegex(prov.ProvenanceError,"NO_FAILING_TEST"):self.runp(r,["test_pass.py"])
 def test_path_escape(self):
  td,r=self.fixture({"m.py":"def f(): return 0\n","test_fail.py":"assert False\n"})
  with td:
   with self.assertRaisesRegex(prov.ProvenanceError,"PATH_OUTSIDE_REPOSITORY"):self.runp(r,["test_fail.py"],source_root="../")
 def test_deterministic(self):
  files={"m.py":"def h(x): return x+1\ndef f(x): return h(x)*2\n","test_fail.py":"from m import f\nassert f(2)==8\n"}
  td,r=self.fixture(files)
  with td:
   a=self.runp(r,["test_fail.py"]);b=self.runp(r,["test_fail.py"]);self.assertEqual(a["ranked_call_edges"],b["ranked_call_edges"]);self.assertEqual(a["interprocedural_hypotheses"],b["interprocedural_hypotheses"])
 def test_zero_external_cognition(self):
  td,r=self.fixture({"m.py":"def h(): return 0\ndef f(): return h()\n","test_fail.py":"from m import f\nassert f()==1\n"})
  with td:
   o=self.runp(r,["test_fail.py"]);self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_capability_provider_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
