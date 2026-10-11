import pathlib, tempfile, textwrap, unittest
from canonical.runtime.bound_capabilities import python_coupled_patch_search_v1 as cps

class T(unittest.TestCase):
    def fixture(self, files):
        td=tempfile.TemporaryDirectory(); root=pathlib.Path(td.name)
        for name,content in files.items():
            p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(content),encoding="utf-8")
        return td,root

    def run_search(self,root,tests,**extra):
        args={
            "test_paths":tests,
            "output_path":"result.json",
            "max_depth":2,
            "beam_width":60,
            "max_states":800,
            "max_mutations_per_source":40,
            "timeout_s":4,
        }
        args.update(extra)
        return cps.run(args,root)

    def test_two_coupled_edits_same_file_one_witness(self):
        source="""def a():
    return False

def b():
    return False
"""
        td,r=self.fixture({
            "m.py":source,
            "test_m.py":"""import unittest
from m import a,b
class X(unittest.TestCase):
 def test_both(self):
  self.assertTrue(a())
  self.assertTrue(b())
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=self.run_search(r,["test_m.py"])
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["winning_depth"],2)
            self.assertEqual(len(out["repair_history"]),2)
            self.assertTrue(out["source_restored"])
            self.assertEqual((r/"m.py").read_text(),source)

    def test_coupled_edits_across_two_files(self):
        a="def a():\n    return False\n"; b="def b():\n    return False\n"
        td,r=self.fixture({
            "a.py":a,"b.py":b,
            "test_both.py":"""import unittest
from a import a
from b import b
class X(unittest.TestCase):
 def test_both(self):
  self.assertTrue(a())
  self.assertTrue(b())
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=self.run_search(r,["test_both.py"])
            self.assertTrue(out["pass"],out)
            self.assertEqual({p["source_path"] for p in out["patches"]},{"a.py","b.py"})
            self.assertEqual((r/"a.py").read_text(),a)
            self.assertEqual((r/"b.py").read_text(),b)

    def test_depth_one_cannot_solve_two_edit_witness(self):
        source="""def a():
    return False
def b():
    return False
"""
        td,r=self.fixture({
            "m.py":source,
            "test_m.py":"""import unittest
from m import a,b
class X(unittest.TestCase):
 def test_both(self): self.assertTrue(a()); self.assertTrue(b())
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=self.run_search(r,["test_m.py"],max_depth=1)
            self.assertFalse(out["pass"])
            self.assertTrue(out["source_restored"])
            self.assertEqual((r/"m.py").read_text(),source)

    def test_baseline_pass_rejected(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return True\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            with self.assertRaisesRegex(cps.CoupledPatchSearchError,"BASELINE_ALREADY_PASSES"):
                self.run_search(r,["test_m.py"])

    def test_no_solution_fails_closed_and_restores(self):
        source="def f(x):\n    return x\n"
        td,r=self.fixture({
            "m.py":source,
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(2),999)
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=self.run_search(r,["test_m.py"],max_depth=1,max_states=25,max_mutations_per_source=20)
            self.assertFalse(out["pass"])
            self.assertEqual(out["patches"],[])
            self.assertTrue(out["source_restored"])
            self.assertEqual((r/"m.py").read_text(),source)

    def test_explicit_path_escape_rejected(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return False\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            with self.assertRaisesRegex(cps.CoupledPatchSearchError,"PATH_INVALID"):
                self.run_search(r,["test_m.py"],source_paths=["../x.py"])

    def test_deterministic(self):
        source="""def a():
    return False
def b():
    return False
"""
        files={
            "m.py":source,
            "test_m.py":"""import unittest
from m import a,b
class X(unittest.TestCase):
 def test_both(self): self.assertTrue(a()); self.assertTrue(b())
if __name__=='__main__': unittest.main()
"""
        }
        td,r=self.fixture(files)
        with td:
            a=self.run_search(r,["test_m.py"]); b=self.run_search(r,["test_m.py"])
            self.assertEqual(a["repair_history"],b["repair_history"])
            self.assertEqual(a["patches"],b["patches"])

    def test_zero_model_provider_spend(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return False\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=self.run_search(r,["test_m.py"])
            self.assertTrue(out["pass"])
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_capability_provider_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
