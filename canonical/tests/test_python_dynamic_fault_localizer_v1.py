import importlib.util,pathlib,tempfile,textwrap,unittest
SPEC=importlib.util.spec_from_file_location("loc","canonical/runtime/bound_capabilities/python_dynamic_fault_localizer_v1.py");loc=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(loc)
class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
  for n,b in files.items():p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(b))
  return td,r
 def runl(self,r,tests,**extra):
  a={"source_root":".","test_paths":tests,"output_path":"loc.json","timeout_s":4,"max_trace_events":50000};a.update(extra);return loc.run(a,r)
 def test_fail_only_symbol_outranks_pass_only(self):
  td,r=self.fixture({"m.py":"""def buggy(x):
 y=x+1
 return y*2
def good(x):
 return x+1
""","test_fail.py":"""from m import buggy
assert buggy(2)==8
""","test_pass.py":"""from m import good
assert good(2)==3
"""})
  with td:
   o=self.runl(r,["test_fail.py","test_pass.py"]);self.assertTrue(o["pass"]);self.assertEqual(o["failing_test_count"],1);self.assertEqual(o["passing_test_count"],1);self.assertEqual(o["ranked_symbols"][0]["symbol"],"buggy")
 def test_backward_def_use_recorded(self):
  td,r=self.fixture({"m.py":"""def f(x):
 y=x+1
 z=y*2
 return z
""","test_fail.py":"""from m import f
assert f(2)==8
"""})
  with td:
   o=self.runl(r,["test_fail.py"]);sym=[x for x in o["ranked_symbols"] if x["symbol"]=="f"][0];names={x["name"] for x in sym["backward_def_use"]};self.assertTrue({"y","z"} & names)
 def test_shared_code_is_penalized_relative_to_fail_only(self):
  td,r=self.fixture({"m.py":"""def shared(x):
 return x+1
def buggy(x):
 return shared(x)*2
def good(x):
 return shared(x)
""","test_fail.py":"""from m import buggy
assert buggy(2)==8
""","test_pass.py":"""from m import good
assert good(2)==3
"""})
  with td:
   o=self.runl(r,["test_fail.py","test_pass.py"]);scores={x["symbol"]:x["score"] for x in o["ranked_symbols"]};self.assertGreater(scores["buggy"],scores["shared"])
 def test_no_failing_test_rejected(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n","test_pass.py":"from m import f\nassert f()==1\n"})
  with td:
   with self.assertRaisesRegex(loc.FaultLocalizerError,"NO_FAILING_TEST"):self.runl(r,["test_pass.py"])
 def test_path_escape(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n","test_fail.py":"assert False\n"})
  with td:
   with self.assertRaisesRegex(loc.FaultLocalizerError,"PATH_OUTSIDE_REPOSITORY"):self.runl(r,["test_fail.py"],source_root="../")
 def test_deterministic(self):
  files={"m.py":"def f(x):\n y=x+1\n return y*2\n","test_fail.py":"from m import f\nassert f(2)==8\n"}
  td,r=self.fixture(files)
  with td:
   a=self.runl(r,["test_fail.py"]);b=self.runl(r,["test_fail.py"]);self.assertEqual(a["ranked_lines"],b["ranked_lines"]);self.assertEqual(a["ranked_symbols"],b["ranked_symbols"])
 def test_zero_external_cognition(self):
  td,r=self.fixture({"m.py":"def f(): return 0\n","test_fail.py":"from m import f\nassert f()==1\n"})
  with td:
   o=self.runl(r,["test_fail.py"]);self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_capability_provider_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
