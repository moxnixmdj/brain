import importlib.util,pathlib,sys,tempfile,textwrap,unittest
P=pathlib.Path(__file__).resolve().parents[1]/"runtime/bound_capabilities/python_coupled_software_repair_loop_v1.py"
S=importlib.util.spec_from_file_location("coupled",P);m=importlib.util.module_from_spec(S);S.loader.exec_module(m)
class T(unittest.TestCase):
 def fixture(self,files):
  td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
  for n,b in files.items():
   p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(b))
  return td,r
 def invoke(self,r,**x):
  a={"source_root":".","test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"output_path":"result.json","timeout_s":5,"max_rounds":4,"max_files":6,"max_mutations_per_file":20,"max_pairs":500,"max_total_candidates":1200};a.update(x);return m.run(a,r)
 def test_atomic_pair_and_restore(self):
  td,r=self.fixture({"a.py":"def f(x):\n return x < 3\n","b.py":"def g():\n return False\n","z_distractor.py":"def junk(x):\n return x > 99\n","test_all.py":"""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_pair(self): self.assertEqual((f(3),g()),(True,True))
if __name__=="__main__":unittest.main()
"""})
  before={n:(r/n).read_bytes() for n in ("a.py","b.py","z_distractor.py")}
  with td:
   o=self.invoke(r);self.assertTrue(o["pass"],o);self.assertEqual(o["baseline_failure_score"],1);self.assertEqual(o["accepted_groups"][0]["kind"],"ATOMIC_CROSS_FILE_PAIR");self.assertEqual({x["source_path"] for x in o["patches"]},{"a.py","b.py"});self.assertEqual([x["failure_score"] for x in o["final_verification_replays"]],[0,0]);self.assertTrue(o["source_restored"])
   for n,b in before.items():self.assertEqual((r/n).read_bytes(),b)
 def test_localization_prefers_imported_called_symbols(self):
  td,r=self.fixture({"a.py":"def f(x):\n return x < 3\n","b.py":"def g():\n return False\n","z.py":"def f(x):\n return x < 100\ndef g():\n return False\n","test_all.py":"""import unittest
from a import f
from b import g
class X(unittest.TestCase):
 def test_pair(self): self.assertEqual((f(3),g()),(True,True))
if __name__=="__main__":unittest.main()
"""})
  with td:
   loc=self.invoke(r)["rounds"][0]["localized_files"];self.assertEqual([x["path"] for x in loc[:2]],["a.py","b.py"]);self.assertGreater(loc[1]["score"],next(x["score"] for x in loc if x["path"]=="z.py"))
 def test_single_and_no_solution(self):
  td,r=self.fixture({"m.py":"def f(x):\n return x < 3\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_a(self):self.assertTrue(f(3))
if __name__=="__main__":unittest.main()
"""})
  with td:self.assertEqual(self.invoke(r)["accepted_groups"][0]["kind"],"SINGLE")
  td,r=self.fixture({"m.py":"def f(x):\n return x\n","test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_a(self):self.assertEqual(f(2),999)
if __name__=="__main__":unittest.main()
"""})
  before=(r/"m.py").read_bytes()
  with td:
   o=self.invoke(r,max_mutations_per_file=5,max_pairs=10,max_total_candidates=20);self.assertFalse(o["pass"]);self.assertTrue(o["source_restored"]);self.assertEqual((r/"m.py").read_bytes(),before)
if __name__=="__main__":unittest.main(verbosity=2)
