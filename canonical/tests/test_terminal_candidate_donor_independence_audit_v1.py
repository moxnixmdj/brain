from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import terminal_candidate_donor_independence_audit_v1 as audit


class TerminalCandidateDonorIndependenceAuditV1Tests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical/runtime").mkdir(parents=True)
        return td, root

    def _write(self, root: Path, name: str, source: str) -> None:
        (root / "canonical/runtime" / f"{name}.py").write_text(source, encoding="utf-8")

    def test_clean_repository_owned_closure_passes(self):
        td, root = self._root()
        try:
            self._write(root, "rootmod", "import json\n")
            with patch.object(audit, "ROOT_MODULES", ("rootmod",)):
                out = audit.evaluate(root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["undeclared_dependency_count"], 0)
            self.assertEqual(out["network_provider_dependencies"], [])
            self.assertEqual(out["target_capability_donor_runtime_dependencies"], [])
        finally:
            td.cleanup()

    def test_missing_local_root_module_fails_closed(self):
        td, root = self._root()
        try:
            with patch.object(audit, "ROOT_MODULES", ("missing_mod",)):
                out = audit.evaluate(root)
            self.assertFalse(out["pass"])
            self.assertTrue(any(x.startswith("LOCAL_MODULE_MISSING:") for x in out["errors"]))
        finally:
            td.cleanup()

    def test_forbidden_network_import_fails_closed(self):
        td, root = self._root()
        try:
            self._write(root, "rootmod", "import requests\n")
            with patch.object(audit, "ROOT_MODULES", ("rootmod",)):
                out = audit.evaluate(root)
            self.assertFalse(out["pass"])
            self.assertIn("requests", out["network_provider_dependencies"])
            self.assertTrue(any("FORBIDDEN_PROVIDER_OR_NETWORK_IMPORT" in x for x in out["errors"]))
        finally:
            td.cleanup()

    def test_forbidden_target_provider_import_fails_closed(self):
        td, root = self._root()
        try:
            self._write(root, "rootmod", "import openai\n")
            with patch.object(audit, "ROOT_MODULES", ("rootmod",)):
                out = audit.evaluate(root)
            self.assertFalse(out["pass"])
            self.assertIn("openai", out["target_capability_donor_runtime_dependencies"])
        finally:
            td.cleanup()

    def test_unclassified_external_import_fails_closed(self):
        td, root = self._root()
        try:
            self._write(root, "rootmod", "import totally_unknown_dependency\n")
            with patch.object(audit, "ROOT_MODULES", ("rootmod",)):
                out = audit.evaluate(root)
            self.assertFalse(out["pass"])
            self.assertTrue(any("UNCLASSIFIED_EXTERNAL_IMPORT" in x for x in out["errors"]))
        finally:
            td.cleanup()

    def test_unreviewed_dynamic_execution_fails_closed(self):
        td, root = self._root()
        try:
            self._write(root, "rootmod", "def f(src):\n    exec(src)\n")
            with patch.object(audit, "ROOT_MODULES", ("rootmod",)), patch.object(
                audit, "REVIEWED_DYNAMIC_BLOBS", {}
            ):
                out = audit.evaluate(root)
            self.assertFalse(out["pass"])
            self.assertTrue(any("UNREVIEWED_DYNAMIC_EXECUTION" in x for x in out["errors"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
