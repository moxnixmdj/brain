import tempfile
import unittest
from pathlib import Path

from canonical.runtime.transitive_runtime_dependency_closure_v1 import compute_closure


class DependencyClosureTests(unittest.TestCase):
    def test_transitive_canonical_imports_are_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical" / "runtime"
            p.mkdir(parents=True)
            (p / "agent.py").write_text("from canonical.runtime.helper import f\n", encoding="utf-8")
            (p / "helper.py").write_text("from canonical.runtime.req import g\n", encoding="utf-8")
            (p / "req.py").write_text("def g(): return 1\n", encoding="utf-8")
            out = compute_closure(root, ["canonical/runtime/agent.py"])
            self.assertTrue(out["pass"], out)
            self.assertEqual(
                {x["path"] for x in out["files"]},
                {"canonical/runtime/agent.py", "canonical/runtime/helper.py", "canonical/runtime/req.py"},
            )

    def test_missing_transitive_module_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical" / "runtime"
            p.mkdir(parents=True)
            (p / "agent.py").write_text(
                "from canonical.runtime.explicit_requirement_index_v2 import build_index\n",
                encoding="utf-8",
            )
            out = compute_closure(root, ["canonical/runtime/agent.py"])
            self.assertFalse(out["pass"])
            self.assertEqual(out["classification"], "TRANSITIVE_DEPENDENCY_MISSING")
            self.assertIn(
                "canonical.runtime.explicit_requirement_index_v2",
                out["unresolved_canonical_modules"],
            )


if __name__ == "__main__":
    unittest.main()
