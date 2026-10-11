import importlib.util,pathlib,sys,tempfile,textwrap,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
PATH=ROOT/"canonical/runtime/bound_capabilities/python_coupled_software_repair_loop_v1.py"
SPEC=importlib.util.spec_from_file_location("coupled",PATH); repair=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(repair)
class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
  for n,b in files.items():p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(b))
  return td,r
 def runr(self,r,tests,**extra):
  a={"source_root":".","test_paths":tests,"test_argv":[sys.executable,tests[0]],"output_path":"result.json","timeout_s":4,"max_files":6,"max_symbols_per_file":8,"mutations_per_file":16,"max_pair_candidates":500,"max_strict_rounds":2,"max_strict_candidates_per_file":40,"max_strict_total_candidates":120}
  a.update(extra);return repair.run(a,r)
 def test_same_file_nonmonotonic_pair(self):
  src="def f(x,y):\n    return x < 3 and y > 5\n"
  td,r=self.fixture({"m.py":src,"test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self):
  self.assertTrue(f(3,5)); self.assertTrue(f(2,6))
  self.assertFalse(f(4,5)); self.assertFalse(f(3,4))
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.runr(r,["test_all.py"])
   self.assertTrue(o["pass"],o);self.assertEqual(o["route"],"COUPLED_PAIR");self.assertTrue(o["crossed_nonmonotonic_valley"]);self.assertEqual(len(o["patches"]),1);self.assertTrue(o["source_restored"]);self.assertEqual((r/"m.py").read_text(),src)
 def test_cross_file_nonmonotonic_pair(self):
  a="def a(x):\n    return x < 3\n";b="def b(y):\n    return y > 5\n"
  td,r=self.fixture({"a.py":a,"b.py":b,"test_all.py":"""import unittest
from a import a
from b import b
class X(unittest.TestCase):
 def test_v(self):
  self.assertTrue(a(3) and b(5))
  self.assertFalse(a(4)); self.assertFalse(b(4))
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.runr(r,["test_all.py"])
   self.assertTrue(o["pass"],o);self.assertTrue(o["crossed_nonmonotonic_valley"]);self.assertEqual({x["source_path"] for x in o["patches"]},{"a.py","b.py"});self.assertEqual((r/"a.py").read_text(),a);self.assertEqual((r/"b.py").read_text(),b)
 def test_symbol_level_localization(self):
  td,r=self.fixture({"pkg/core.py":"def wanted(x):\n    return x < 3\n\ndef irrelevant(x):\n    return x*99\n","pkg/noise.py":"def noise(x):\n    return x < 100\n","test_all.py":"""import unittest
from pkg.core import wanted
class X(unittest.TestCase):
 def test_wanted(self): self.assertTrue(wanted(3))
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.runr(r,["test_all.py"])
   self.assertTrue(o["pass"],o);rows=o["localization_candidates"]
   if rows:
    self.assertEqual(rows[0]["path"],"pkg/core.py");names=[x["name"] for x in rows[0]["symbols"]];self.assertIn("wanted",names)
    wanted=[x for x in rows[0]["symbols"] if x["name"]=="wanted"][0];self.assertIn("TEST_IMPORTED_SYMBOL",wanted["reasons"])
 def test_strict_progress_route_reused(self):
  td,r=self.fixture({"m.py":"def f(x):\n    return x < 3\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f(3)); self.assertFalse(f(4))
if __name__=='__main__': unittest.main()
"""})
  with td:
   o=self.runr(r,["test_all.py"]);self.assertTrue(o["pass"]);self.assertEqual(o["route"],"STRICT_PROGRESS");self.assertTrue(o["source_restored"])
 def test_no_solution_fails_closed(self):
  src="def f(x):\n    return x\n"
  td,r=self.fixture({"m.py":src,"test_all.py":"""from m import f
assert f(2)==99
"""})
  with td:
   o=self.runr(r,["test_all.py"],max_pair_candidates=30,mutations_per_file=6);self.assertFalse(o["pass"]);self.assertTrue(o["source_restored"]);self.assertEqual((r/"m.py").read_text(),src)
 def test_path_escape(self):
  td,r=self.fixture({"m.py":"def f(): return False\n","test_all.py":"assert False\n"})
  with td:
   with self.assertRaisesRegex(repair.RepairLoopError,"PATH_OUTSIDE_REPOSITORY"):self.runr(r,["test_all.py"],source_root="../")
 def test_deterministic(self):
  files={"m.py":"def f(x,y):\n    return x < 3 and y > 5\n","test_all.py":"""from m import f
assert f(3,5)
assert f(2,6)
assert not f(4,5)
assert not f(3,4)
"""}
  td,r=self.fixture(files)
  with td:
   a=self.runr(r,["test_all.py"]);b=self.runr(r,["test_all.py"]);self.assertEqual(a["patches"],b["patches"]);self.assertEqual(a["localization_candidates"],b["localization_candidates"])
 def test_zero_external_cognition(self):
  td,r=self.fixture({"m.py":"def f(x): return x < 3\n","test_all.py":"""from m import f
assert f(3)
assert not f(4)
"""})
  with td:
   o=self.runr(r,["test_all.py"]);self.assertEqual(o["model_dependency_count"],0);self.assertEqual(o["external_capability_provider_count"],0);self.assertEqual(o["incremental_spend_usd"],0)
if __name__=="__main__":unittest.main(verbosity=2)
