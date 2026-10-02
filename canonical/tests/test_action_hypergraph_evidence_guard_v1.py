from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from canonical.runtime.action_hypergraph_evidence_guard_v1 import evaluate

class Tests(unittest.TestCase):
    def _fixture(self, satisfied=True, receipt_status="PASS"):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        p=root/"canonical/verification/x.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({"status":receipt_status}),encoding="utf-8")
        doc={"actions":[{"id":"A","preconditions":[{
            "id":"P","satisfied":satisfied,
            "derived_evidence":{"path":"canonical/verification/x.json","field":"status","equals":"PASS"}
        }]}]}
        return td,root,doc

    def test_exact_receipt_supports_true(self):
        td,root,doc=self._fixture(True,"PASS")
        try:
            out=evaluate(root,doc)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["checked"],1)
        finally: td.cleanup()

    def test_stale_false_fails(self):
        td,root,doc=self._fixture(False,"PASS")
        try:
            out=evaluate(root,doc)
            self.assertFalse(out["pass"])
            self.assertIn("STALE_DERIVED_PRECONDITION:A:P",out["errors"])
        finally: td.cleanup()

    def test_stale_true_fails_if_receipt_changes(self):
        td,root,doc=self._fixture(True,"OTHER")
        try:
            out=evaluate(root,doc)
            self.assertFalse(out["pass"])
            self.assertIn("STALE_DERIVED_PRECONDITION:A:P",out["errors"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main(verbosity=2)
