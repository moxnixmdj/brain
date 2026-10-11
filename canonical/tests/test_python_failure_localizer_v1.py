import pathlib, tempfile, textwrap, unittest
from canonical.runtime.bound_capabilities import python_failure_localizer_v1 as loc

class T(unittest.TestCase):
    def fixture(self, files):
        td=tempfile.TemporaryDirectory(); root=pathlib.Path(td.name)
        for name,content in files.items():
            p=root/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(textwrap.dedent(content),encoding="utf-8")
        return td,root

    def test_traceback_localizes_source_symbol(self):
        td,r=self.fixture({
            "m.py":"""def f(x):
    return 10 // x
""",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): f(0)
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=loc.localize({"test_paths":["test_m.py"],"timeout_s":4},r)
            self.assertEqual(out["status"],"PASS__OBSERVABLE_FAILURE_CANDIDATES_LOCALIZED")
            first=out["candidates"][0]
            self.assertEqual(first["source_path"],"m.py")
            self.assertEqual(first["symbol"]["name"],"f")
            self.assertEqual(first["evidence_kind"],"TRACEBACK_FRAME")
            self.assertFalse(first["causal_supported"])

    def test_assertion_failure_uses_import_fallback(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),2)
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=loc.localize({"test_paths":["test_m.py"]},r)
            self.assertEqual(out["candidates"][0]["source_path"],"m.py")
            self.assertEqual(out["candidates"][0]["evidence_kind"],"FAILING_TEST_LOCAL_IMPORT")

    def test_passing_suite_yields_no_failures(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),1)
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=loc.localize({"test_paths":["test_m.py"]},r)
            self.assertEqual(out["status"],"NO_FAILURES_OBSERVED")
            self.assertEqual(out["failure_count"],0)
            self.assertEqual(out["candidate_count"],0)

    def test_test_frame_is_not_candidate(self):
        td,r=self.fixture({
            "test_m.py":"""import unittest
class X(unittest.TestCase):
 def test_v(self): raise RuntimeError('x')
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=loc.localize({"test_paths":["test_m.py"]},r)
            self.assertEqual(out["status"],"OPEN__FAILURE_OBSERVED_NO_REPOSITORY_LOCAL_CANDIDATE")
            self.assertEqual(out["candidate_count"],0)

    def test_explicit_path_escape_rejected(self):
        td,r=self.fixture({"test_m.py":"raise RuntimeError('x')\n"})
        with td:
            with self.assertRaisesRegex(loc.FailureLocalizationError,"PATH_INVALID"):
                loc.localize({"test_paths":["../x.py"]},r)

    def test_deterministic(self):
        td,r=self.fixture({
            "m.py":"""def f(x):
    return 1 // x
""",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): f(0)
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            a=loc.localize({"test_paths":["test_m.py"]},r)
            b=loc.localize({"test_paths":["test_m.py"]},r)
            self.assertEqual(a["candidates"],b["candidates"])
            self.assertEqual(a["failures"],b["failures"])

    def test_zero_model_provider_spend(self):
        td,r=self.fixture({
            "m.py":"def f():\n    return 1\n",
            "test_m.py":"""import unittest
from m import f
class X(unittest.TestCase):
 def test_v(self): self.assertEqual(f(),2)
if __name__=='__main__': unittest.main()
"""
        })
        with td:
            out=loc.localize({"test_paths":["test_m.py"]},r)
            self.assertEqual(out["model_dependency_count"],0)
            self.assertEqual(out["external_capability_provider_count"],0)
            self.assertEqual(out["incremental_spend_usd"],0)

if __name__=="__main__": unittest.main(verbosity=2)
