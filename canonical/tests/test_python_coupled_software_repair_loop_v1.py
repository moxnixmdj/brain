import importlib.util,pathlib,sys,tempfile,textwrap,unittest
P=pathlib.Path(__file__).resolve().parents[1]/"runtime/bound_capabilities/python_coupled_software_repair_loop_v1.py"
S=importlib.util.spec_from_file_location("coupled",P);m=importlib.util.module_from_spec(S);S.loader.exec_module(m)

class CoupledRepairTests(unittest.TestCase):
    def fixture(self,files):
        td=tempfile.TemporaryDirectory();root=pathlib.Path(td.name)
        for name,body in files.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(body))
        return td,root

    def invoke(self,root,**extra):
        args={"source_root":".","test_paths":["test_all.py"],"test_argv":[sys.executable,"test_all.py"],"output_path":"result.json","timeout_s":5,"max_rounds":4,"max_files":6,"max_mutations_per_file":20,"max_pairs":500,"max_total_candidates":1200}
        args.update(extra);return m.run(args,root)

    def test_atomic_cross_file_pair_crosses_flat_plateau(self):
        td,r=self.fixture({
            "a.py":"def f(x):\n    return x < 3\n",
            "b.py":"def g():\n    return False\n",
            "z_distractor.py":"def junk0x):\n    return x > 99\n",
            "test_all.py":"""import unittest
from a import f
from b import g
class X(unittest.TestCase):
    def test_pair(self): self.assertEqual((f(3),g()),(True,True))
if __name__=="__main__":unittest.main()
"""})
        before={n:(r/n).read_bytes() for n in ("a.py","b.py","z_distractor.py")}
        with td:
            out=self.invoke(r)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["baseline_failure_score"],1)
            self.assertEqual(out["accepted_groups"][0]["kind"],"ATOMIC_CROSS_FILE_PAIR")
            self.assertEqual(out["accepted_groups"][0]["score_after"],0)
            self.assertEqual({x["source_path"] for x in out["patches"]},{"a.py","b.py"})
            self.assertEqual([x["failure_score"] for x in out["final_verification_replays"]],[0,0])
            self.assertTrue(out["source_restored"])
            for n,b in before.items():self.assertEqual((r/n).read_bytes(),b)

    def test_localization_ranks_imported_called_symbols_over_distractor(self):
        td,r=self.fixture({
            "a.py":"def f(x):\n    return x < 3\n",
            "b.py":"def g():\n    return False\n",
            "z.py":"def f(x):\n    return x < 100\ndef g():\n    return False\n",
            "test_all.py":"""import unittest
from a import f
from b import g
class X(unittest.TestCase):
    def test_pair(self): self.assertEqual((f(3),g()),(True,True))
if __name__=="__main__":unittest.main()
"""})
        with td:
            out=self.invoke(r);loc=out["rounds"][0]["localized_files"]
            self.assertEqual([x["path"] for x in loc[:2]],["a.py","b.py"])
            self.assertTrue(all("TEST_IMPORT" in x["reasons"] for x in loc[:2]))
            self.assertGreater(loc[1]["score"],next(x["score"] for x in loc if x["path"]=="z.py"))

    def test_single_strict_improvement_still_works(self):
        td,r=self.fixture({
            "m.py":"def f(x):\n    return x < 3\n",
            "test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
    def test_a(self):self.assertTrue(f(3))
if __name__=="__main__":unittest.main()
"""})
        with td:
            out=self.invoke(r);self.assertTrue(out["pass"],out);self.assertEqual(out["accepted_groups"][0]["kind"],"SINGLE")

    def test_no_solution_fails_closed_and_restores(self):
        td,r=self.fixture({
            "m.py":"def f(x):\n    return x\n",
            "test_all.py":"""import unittest
from m import f
class X(unittest.TestCase):
    def test_a(self):self.assertEqual(f(2),999)
if __name__=="__main__":unittest.main()
"""})
        before=(r/"m.py").read_bytes()
        with td:
            out=self.invoke(r,max_mutations_per_file=5,max_pairs=10,max_total_candidates=20)
            self.assertFalse(out["pass"]);self.assertTrue(out["source_restored"]);self.assertEqual((r/"m.py").read_bytes(),before)

if __name__=="__main__":unittest.main(verbosity=2)
