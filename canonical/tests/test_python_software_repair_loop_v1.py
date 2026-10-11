import importlib.util, pathlib, tempfile, textwrap, unittest

SPEC=importlib.util.spec_from_file_location(
    "repair","canonical/runtime/bound_capabilities/python_software_repair_loop_v1.py"
)
repair=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(repair)

class T(unittest.TestCase):
    def fixture(self, files):
        td=tempfile.TemporaryDirectory(); root=pathlib.Path(td.name)
        for path,content in files.items():
            p=root/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(content))
        return td,root

    def run_loop(self,root,tests,**extra):
        args={"test_paths":tests,"output_path":"result.json","max_edits":6,"max_candidates":300,"timeout_s":4}
        args.update(extra)
        return repair.run(args,root)

    def test_two_edits_same_file(self):
        source="def a():\n    return False\n\ndef b(x):\n    return x < 3\n"
        td,r=self.fixture({
            "m.py":source,
            "test_a.py":"""import unittest
from m import a
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(a())
if __name__=='__main__': unittest.main()
""",
            "test_b.py":"""import unittest
from m import b
class X(unittest.TestCase):
 def test_b(self): self.assertTrue(b(3)); self.assertFalse(b(4))
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            out=self.run_loop(r,["test_a.py","test_b.py"])
            self.assertTrue(out["pass"]); self.assertEqual(out["edits_applied"],2)
            self.assertEqual(len(out["patches"]),1); self.assertTrue(out["source_restored"])
            self.assertEqual((r/"m.py").read_text(),source)

    def test_multi_file_multi_edit(self):
        a="def a():\n    return False\n"; b="def b():\n    return 4\n"
        td,r=self.fixture({
            "a.py":a,"b.py":b,
            "test_a.py":"""import unittest
from a import a
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(a())
if __name__=='__main__': unittest.main()
""",
            "test_b.py":"""import unittest
from b import b
class X(unittest.TestCase):
 def test_b(self): self.assertEqual(b(),7)
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            out=self.run_loop(r,["test_a.py","test_b.py"])
            self.assertTrue(out["pass"]); self.assertEqual(out["edits_applied"],2)
            self.assertEqual({p["source_path"] for p in out["patches"]},{"a.py","b.py"})
            self.assertEqual((r/"a.py").read_text(),a); self.assertEqual((r/"b.py").read_text(),b)

    def test_no_solution_fails_closed_and_restores(self):
        source="def f(x):\n    return x\n"
        td,r=self.fixture({
            "m.py":source,
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(2),99)
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            out=self.run_loop(r,["test_m.py"],max_candidates=20)
            self.assertFalse(out["pass"]); self.assertTrue(out["source_restored"])
            self.assertEqual(out["patches"],[]); self.assertEqual((r/"m.py").read_text(),source)

    def test_baseline_pass_rejected(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),1)
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            with self.assertRaisesRegex(repair.RepairLoopError,"BASELINE_ALREADY_PASSES"):
                self.run_loop(r,["test_m.py"])

    def test_edit_bound_fails_closed(self):
        source="def a():\n    return False\n\ndef b():\n    return False\n"
        td,r=self.fixture({
            "m.py":source,
            "test_a.py":"""import unittest
from m import a
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(a())
if __name__=='__main__': unittest.main()
""",
            "test_b.py":"""import unittest
from m import b
class X(unittest.TestCase):
 def test_b(self): self.assertTrue(b())
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            out=self.run_loop(r,["test_a.py","test_b.py"],max_edits=1)
            self.assertFalse(out["pass"]); self.assertTrue(out["source_restored"])
            self.assertEqual((r/"m.py").read_text(),source)

    def test_explicit_path_escape_rejected(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return False\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            with self.assertRaisesRegex(repair.RepairLoopError,"PATH_INVALID"):
                self.run_loop(r,["test_m.py"],source_paths=["../outside.py"])

    def test_deterministic_replay(self):
        source="def a():\n    return False\n\ndef b():\n    return 4\n"
        files={
            "m.py":source,
            "test_a.py":"""import unittest
from m import a
class X(unittest.TestCase):
 def test_a(self): self.assertTrue(a())
if __name__=='__main__': unittest.main()
""",
            "test_b.py":"""import unittest
from m import b
class X(unittest.TestCase):
 def test_b(self): self.assertEqual(b(),7)
if __name__=='__main__': unittest.main()
""",
        }
        td,r=self.fixture(files)
        with td:
            x=self.run_loop(r,["test_a.py","test_b.py"]); y=self.run_loop(r,["test_a.py","test_b.py"])
            self.assertEqual(x["repair_history"],y["repair_history"])
            self.assertEqual(x["patches"],y["patches"])

    def test_zero_model_and_zero_spend(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return False\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertTrue(f())
if __name__=='__main__': unittest.main()
""",
        })
        with td:
            out=self.run_loop(r,["test_m.py"])
            self.assertTrue(out["pass"]); self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_capability_provider_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
