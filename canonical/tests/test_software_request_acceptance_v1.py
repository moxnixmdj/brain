import importlib.util,pathlib,tempfile,textwrap,unittest,json
BASE="canonical/runtime/bound_capabilities"
def load(name):
 s=importlib.util.spec_from_file_location(name,BASE+"/"+name+".py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
comp=load("software_request_acceptance_compile_v1");exe=load("software_request_acceptance_execute_v1")
class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
  for n,b in files.items():p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(b))
  return td,r
 def test_return_pass(self):
  td,r=self.fixture({"m.py":"def clamp(x):\n return 0 if x < 0 else x\n"})
  with td:
   p=comp.compile_request("The function `clamp(-1)` must return `0`.",r);self.assertTrue(p["admission_ready"],p);o=exe.execute(p,r);self.assertTrue(o["pass"],o)
 def test_return_failure_detected(self):
  td,r=self.fixture({"m.py":"def inc(x): return x+1\n"})
  with td:
   p=comp.compile_request("`inc(2)` must return `9`.",r);o=exe.execute(p,r);self.assertFalse(o["pass"])
 def test_raise_pass(self):
  td,r=self.fixture({"m.py":"def parse(x):\n raise ValueError('bad')\n"})
  with td:
   p=comp.compile_request("`parse('x')` must raise `ValueError`.",r);self.assertTrue(p["admission_ready"]);self.assertTrue(exe.execute(p,r)["pass"])
 def test_file_positive_and_negative(self):
  td,r=self.fixture({"ok.txt":"x","m.py":"def f(): return 1\n"})
  with td:
   p=comp.compile_request("`ok.txt` must exist.\n`debug.log` must not exist.",r);self.assertTrue(p["admission_ready"],p);self.assertEqual(p["requirement_count"],2);self.assertTrue(exe.execute(p,r)["pass"])
 def test_unsupported_normative_text_blocks(self):
  td,r=self.fixture({"m.py":"def parse(x): return x\n"})
  with td:
   p=comp.compile_request("The parser must be fast and correct.",r);self.assertFalse(p["admission_ready"]);self.assertTrue(p["specification_holes"]);self.assertFalse(exe.execute(p,r,existing_test_evidence={"all_tests_pass":True})["pass"])
 def test_duplicate_function_binding_blocks(self):
  td,r=self.fixture({"a.py":"def f(x): return x\n","b.py":"def f(x): return x\n"})
  with td:
   p=comp.compile_request("`f(1)` must return `1`.",r);self.assertFalse(p["admission_ready"]);self.assertIn("CARDINALITY",p["requirements"][0]["unbound_reason"])
 def test_module_hint_disambiguates(self):
  td,r=self.fixture({"a.py":"def f(x): return x\n","b.py":"def f(x): return x+1\n"})
  with td:
   p=comp.compile_request("`b.f(1)` must return `2`.",r);self.assertTrue(p["admission_ready"]);self.assertTrue(exe.execute(p,r)["pass"])
 def test_multiple_obligations_same_line(self):
  td,r=self.fixture({"m.py":"def f(x): return x+1\n"})
  with td:
   p=comp.compile_request("`f(1)` must return `2` and `f(2)` must return `3`.",r);self.assertTrue(p["admission_ready"],p);self.assertEqual(p["requirement_count"],2);self.assertTrue(exe.execute(p,r)["pass"])
 def test_uncovered_second_obligation_blocks(self):
  td,r=self.fixture({"m.py":"def f(x): return x+1\n"})
  with td:
   p=comp.compile_request("`f(1)` must return `2` and it must preserve input type.",r);self.assertFalse(p["admission_ready"]);self.assertTrue(p["specification_holes"])
 def test_path_escape_blocks(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n"})
  with td:
   p=comp.compile_request("`../secret.txt` must exist.",r);self.assertFalse(p["admission_ready"])
 def test_declarative_returns_text_fails_closed(self):
  td,r=self.fixture({"m.py":"def f(x): return x\n"})
  with td:
   p=comp.compile_request("For negative inputs, the function returns zero.",r);self.assertFalse(p["admission_ready"]);self.assertTrue(p["specification_holes"])
 def test_zero_external_cognition(self):
  td,r=self.fixture({"m.py":"def f(): return 1\n"})
  with td:
   p=comp.compile_request("`f()` must return `1`.",r);o=exe.execute(p,r);self.assertEqual((p["model_dependency_count"],p["external_capability_provider_count"],p["incremental_spend_usd"]),(0,0,0));self.assertEqual((o["model_dependency_count"],o["external_capability_provider_count"],o["incremental_spend_usd"]),(0,0,0))
if __name__=="__main__":unittest.main(verbosity=2)
