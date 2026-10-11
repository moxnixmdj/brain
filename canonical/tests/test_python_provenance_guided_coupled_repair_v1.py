import importlib.util,pathlib,sys,tempfile,textwrap,unittest
BASE="canonical/runtime/bound_capabilities"
SPEC=importlib.util.spec_from_file_location("guided",BASE+"/python_provenance_guided_coupled_repair_v1.py");guided=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(guided)
class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
  for n,b in files.items():p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(b))
  return td,r
 def runr(self,r,traces,oracle="test_all.py",**extra):
  a={"source_root":".","test_paths":traces,"test_argv":[sys.executable,oracle],"output_path":"guided.json","timeout_s":4,"max_guided_files":2,"max_guided_symbols_per_file":3,"mutations_per_file":12,"max_pair_candidates":300,"max_control_files":12,"max_control_symbols_per_file":12};a.update(extra);return guided.run(a,r)
 def test_guided_cross_file_nonmonotonic_repair(self):
  files={"a.py":"def a(x):\n    return x < 3\n","b.py":"def b(y):\n    return y > 5\n","noise1.py":"def n1(x): return x < 100\n","noise2.py":"def n2(x): return x > -100\n","trace_fail.py":"from a import a\nfrom b import b\nassert a(3) and b(5)\n","trace_pass.py":"from a import a\nfrom b import b\nassert a(2) and b(6)\n","test_all.py":"from a import a\nfrom b import b\nassert a(3) and b(5)\nassert a(2) and b(6)\nassert not a(4)\nassert not b(4)\n"}
  td,r=self.fixture(files)
  with td:
   o=self.runr(r,["trace_fail.py","trace_pass.py"]);self.assertTrue(o["pass"],o);self.assertEqual(o["winner_mode"],"COUPLED_PAIR_GUIDED");self.assertEqual({p["source_path"] for p in o["patches"]},{"a.py","b.py"});self.assertTrue(o["source_restored"]);self.assertTrue(o["crossed_nonmonotonic_valley"])
 def test_guidance_reduces_control_space(self):
  noise={f"noise{i}.py":f"def noise{i}(x):\n return x < {100+i}\n" for i in range(8)}
  files={**noise,"m.py":"def helper(x): return x < 3\ndef f(x): return helper(x)\n","trace_fail.py":"from m import f\nassert f(3)\n","trace_pass.py":"from m import f\nassert f(2)\n","test_all.py":"from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n"}
  td,r=self.fixture(files)
  with td:
   o=self.runr(r,["trace_fail.py","trace_pass.py"],max_guided_files=1,max_control_files=12);self.assertTrue(o["pass"],o);self.assertEqual(o["winner_mode"],"SINGLE_GUIDED");self.assertTrue(o["guidance"]["guidance_reduced_candidate_items"],o["guidance"]);self.assertTrue(o["guidance"]["guidance_reduced_pair_space"],o["guidance"])
 def test_provenance_present(self):
  td,r=self.fixture({"m.py":"def h(x): return x < 3\ndef f(x): return h(x)\n","trace_fail.py":"from m import f\nassert f(3)\n","trace_pass.py":"from m import f\nassert f(2)\n","test_all.py":"from m import f\nassert f(3)\n"})
  with td:
   o=self.runr(r,["trace_fail.py","trace_pass.py"],max_guided_files=1);self.assertGreater(o["provenance_hypothesis_count"],0)
 def test_no_solution_fails_closed(self):
  src="def f(x): return x\n";td,r=self.fixture({"m.py":src,"trace_fail.py":"from m import f\nassert f(2)==99\n","test_all.py":"from m import f\nassert f(2)==99\n"})
  with td:
   o=self.runr(r,["trace_fail.py"],max_pair_candidates=20,mutations_per_file=5);self.assertFalse(o["pass"]);self.assertTrue(o["source_restored"]);self.assertEqual((r/"m.py").read_text(),src)
 def test_path_escape(self):
  td,r=self.fixture({"m.py":"def f(): return 0\n","trace_fail.py":"assert False\n","test_all.py":"assert False\n"})
  with td:
   with self.assertRaisesRegex(guided.GuidedRepairError,"PATH_OUTSIDE_REPOSITORY"):self.runr(r,["trace_fail.py"],source_root="../")
 def test_deterministic(self):
  files={"m.py":"def h(x): return x < 3\ndef f(x): return h(x)\n","trace_fail.py":"from m import f\nassert f(3)\n","trace_pass.py":"from m import f\nassert f(2)\n","test_all.py":"from m import f\nassert f(3)\nassert not f(4)\n"}
  td,r=self.fixture(files)
  with td:
   a=self.runr(r,["trace_fail.py","trace_pass.py"],max_guided_files=1);b=self.runr(r,["trace_fail.py","trace_pass.py"],max_guided_files=1);self.assertEqual(a["patches"],b["patches"]);self.assertEqual(a["guided_localization"],b["guided_localization"])
 def test_zero_external_cognition(self):
  td,r=self.fixture({"m.py":"def f(x): return x < 3\n","trace_fail.py":"from m import f\nassert f(3)\n","test_all.py":"from m import f\nassert f(3)\n"})
  with td:
   o=self.runr(r,["trace_fail.py"],max_guided_files=1);self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_capability_provider_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
