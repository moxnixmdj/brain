import importlib.util, pathlib, tempfile, textwrap, unittest

SPEC=importlib.util.spec_from_file_location("acc","canonical/runtime/bound_capabilities/software_task_acceptance_compiler_v1.py")
acc=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(acc)

class T(unittest.TestCase):
    def fixture(self,test):
        td=tempfile.TemporaryDirectory(); r=pathlib.Path(td.name)
        (r/"test_app.py").write_text(textwrap.dedent(test))
        return td,r

    def run_compiler(self,r,task,**extra):
        a={"task_text":task,"test_paths":["test_app.py"],"output_path":"result.json"}
        a.update(extra)
        return acc.run(a,r)

    def test_unittest_numeric_complete(self):
        td,r=self.fixture("""import unittest
from app import f
class X(unittest.TestCase):
 def test_f(self): self.assertEqual(f(),7)
""")
        with td:
            out=self.run_compiler(r,"f must return 7.")
            self.assertTrue(out["complete"])
            self.assertEqual(out["bound_obligation_count"],1)

    def test_compound_split_complete(self):
        td,r=self.fixture("""import unittest
from app import f,g
class X(unittest.TestCase):
 def test_f(self): self.assertEqual(f(),7)
 def test_g(self): self.assertEqual(g(),'good')
""")
        with td:
            out=self.run_compiler(r,"f must return 7 and g must return 'good'.")
            self.assertTrue(out["complete"])
            self.assertEqual(out["obligation_count"],2)

    def test_extra_semantics_fail_closed(self):
        td,r=self.fixture("""import unittest
from app import f
class X(unittest.TestCase):
 def test_f(self): self.assertEqual(f(),7)
""")
        with td:
            out=self.run_compiler(r,"f must return 7 without changing api.")
            self.assertFalse(out["complete"])
            self.assertEqual(out["obligations"][0]["status"],"PARTIAL_TEST_MATCH_WITH_UNBOUND_SEMANTICS")
            self.assertIn("api",out["obligations"][0]["residual_tokens"])

    def test_pytest_style_true(self):
        td,r=self.fixture("""from app import ready
def test_ready():
 assert ready()
""")
        with td:
            out=self.run_compiler(r,"ready must return true.")
            self.assertTrue(out["complete"])

    def test_ambiguous_duplicate_evidence_rejected(self):
        td,r=self.fixture("""import unittest
from app import f
class X(unittest.TestCase):
 def test_a(self): self.assertEqual(f(),7)
 def test_b(self): self.assertEqual(f(),7)
""")
        with td:
            out=self.run_compiler(r,"f must return 7.")
            self.assertFalse(out["complete"])
            self.assertEqual(out["obligations"][0]["status"],"AMBIGUOUS_TEST_EVIDENCE")

    def test_empty_task_rejected(self):
        td,r=self.fixture("""def test_x(): assert True
""")
        with td:
            with self.assertRaisesRegex(acc.AcceptanceCompilerError,"TASK_TEXT_REQUIRED"):
                self.run_compiler(r,"")

    def test_path_escape_rejected(self):
        td,r=self.fixture("""def test_x(): assert True
""")
        with td:
            with self.assertRaisesRegex(acc.AcceptanceCompilerError,"PATH_INVALID"):
                self.run_compiler(r,"x must return true.",test_paths=["../test_x.py"])

    def test_zero_model_zero_spend_and_unbound_preserved(self):
        td,r=self.fixture("""import unittest
from app import f
class X(unittest.TestCase):
 def test_f(self): self.assertEqual(f(),7)
""")
        with td:
            out=self.run_compiler(r,"f must return 7. Preserve backward compatibility.")
            self.assertFalse(out["complete"])
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_capability_provider_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)
            self.assertEqual(out["obligations"][1]["status"],"UNBOUND_SEMANTIC_REQUIREMENT")

if __name__=="__main__": unittest.main(verbosity=2)
