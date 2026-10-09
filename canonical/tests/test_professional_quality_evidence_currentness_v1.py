from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_evidence_currentness_v1 as gate

class ProfessionalQualityEvidenceCurrentnessV1Tests(unittest.TestCase):
    def _matrix(self, root: Path, rel: str, expected: str):
        mp=root/gate.DEFAULT_MATRIX
        mp.parent.mkdir(parents=True,exist_ok=True)
        mp.write_text(json.dumps({"roots":[{"id":"R","evidence":[{"path":rel,"git_blob_sha":expected,"supports":"X"}]}]}))

    def test_exact_blob_is_fresh(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rel="canonical/verification/x.json"
            p=root/rel
            p.parent.mkdir(parents=True)
            p.write_text('{"v":1}\n')
            self._matrix(root,rel,gate.git_blob_sha(p))
            out=gate.evaluate(root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["status"],"PASS__ALL_EVIDENCE_REFERENCES_CURRENT")

    def test_mutable_mismatch_is_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rel=sorted(gate.MUTABLE_POINTER_PATHS)[0]
            p=root/rel
            p.parent.mkdir(parents=True)
            p.write_text('{"v":2}\n')
            self._matrix(root,rel,"0"*40)
            out=gate.evaluate(root)
            self.assertEqual(out["status"],"OPEN__STALE_MUTABLE_EVIDENCE_REBIND_REQUIRED")
            self.assertEqual(out["stale_rebind_count"],1)
            self.assertEqual(out["broken_binding_count"],0)

    def test_immutable_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rel="canonical/verification/x.json"
            p=root/rel
            p.parent.mkdir(parents=True)
            p.write_text('{"v":2}\n')
            self._matrix(root,rel,"0"*40)
            out=gate.evaluate(root)
            self.assertEqual(out["status"],"FAIL_CLOSED__BROKEN_EVIDENCE_BINDING")
            self.assertEqual(out["broken_binding_count"],1)

if __name__=="__main__":
    unittest.main()
