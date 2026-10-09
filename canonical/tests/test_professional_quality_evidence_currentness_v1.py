from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_evidence_currentness_v1 as gate

ROOT=Path(__file__).resolve().parents[2]

class ProfessionalQualityEvidenceCurrentnessV1Tests(unittest.TestCase):
    def test_current_repo_exposes_only_three_stale_mutable_entries(self):
        out=gate.evaluate(ROOT)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__STALE_MUTABLE_EVIDENCE_REBIND_REQUIRED")
        self.assertEqual(out["evidence_entry_count"],24)
        self.assertEqual(out["fresh_count"],21)
        self.assertEqual(out["stale_rebind_count"],3)
        self.assertEqual(out["broken_binding_count"],0)
        stale={(r["root_id"],r["path"]) for r in out["rows"] if r["state"]=="STALE_REBIND_REQUIRED"}
        self.assertEqual(stale,{
            ("R6_EVIDENCE_GROUNDING_DEPENDENCE","canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"),
            ("R10_ANALYSIS_DECISION","canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"),
            ("R12_META_COMPOSITION_CLOSURE","canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"),
        })
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_mutable_pointer_mismatch_is_open_not_broken(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"v":2}\n')
            matrix={
                "roots":[{
                    "id":"R",
                    "evidence":[{
                        "path":"canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json",
                        "git_blob_sha":"0"*40,
                        "supports":"X",
                    }],
                }],
            }
            mp=root/gate.DEFAULT_MATRIX
            mp.parent.mkdir(parents=True,exist_ok=True)
            mp.write_text(json.dumps(matrix))
            out=gate.evaluate(root)
            self.assertEqual(out["status"],"OPEN__STALE_MUTABLE_EVIDENCE_REBIND_REQUIRED")
            self.assertEqual(out["stale_rebind_count"],1)
            self.assertEqual(out["broken_binding_count"],0)

    def test_immutable_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/verification/x.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"v":2}\n')
            matrix={
                "roots":[{
                    "id":"R",
                    "evidence":[{
                        "path":"canonical/verification/x.json",
                        "git_blob_sha":"0"*40,
                        "supports":"X",
                    }],
                }],
            }
            mp=root/gate.DEFAULT_MATRIX
            mp.parent.mkdir(parents=True,exist_ok=True)
            mp.write_text(json.dumps(matrix))
            out=gate.evaluate(root)
            self.assertEqual(out["status"],"FAIL_CLOSED__BROKEN_EVIDENCE_BINDING")
            self.assertEqual(out["broken_binding_count"],1)

if __name__=="__main__":
    unittest.main()
