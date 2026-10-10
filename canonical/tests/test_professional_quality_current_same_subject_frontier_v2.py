from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_leaf_coverage_projection_v2 as cover
from canonical.runtime import professional_quality_same_subject_composition_gate_v1 as same

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
SUBJECT = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_DECLARED_SYSTEM_SUBJECT_20261010_V2.json"
WORKLIST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V2.json"

def blob(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

class ProfessionalQualityCurrentSameSubjectFrontierV2Tests(unittest.TestCase):
    def test_pointer_and_projection_agree_on_full_bounded_coverage(self):
        cur=json.loads(CURRENT.read_text())
        out=cover.project()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["admitted_scoped_capability_count"],21)
        self.assertEqual(out["partial_coverage_leaf_count"],24)
        self.assertEqual(out["no_scoped_evidence_leaf_count"],0)
        self.assertEqual(out["verified_global_leaf_count"],0)
        self.assertFalse(out["global_leaf_closure"])
        self.assertIn("TWENTY_ONE_SCOPED_CAPABILITIES_VERIFIED",cur["status"])
        self.assertIn("LEAF_FRONTIER_24_PARTIAL_0_NO_SCOPED_24_GLOBAL_OPEN",cur["status"])
        self.assertEqual(cur["same_subject_root_binding_frontier"]["verified_root_subject_binding_count"],0)
        self.assertFalse(cur["live_default"])
        self.assertFalse(cur["quality_authority"])

    def test_subject_v2_is_exactly_content_current(self):
        doc=json.loads(SUBJECT.read_text())
        for row in doc["system_material"]["components"]:
            p=ROOT/row["path"]
            self.assertTrue(p.is_file(),row)
            self.assertEqual(blob(p),row["git_blob_sha"],row)
        canon=json.dumps(doc["system_material"],sort_keys=True,separators=(",",":"),ensure_ascii=False)
        self.assertEqual(hashlib.sha256(canon.encode()).hexdigest(),doc["subject_sha256"])
        self.assertEqual(doc["subject_sha256"],"ebd841e7c471078a6ce7143ece3b9c072a9992532bfd6c2c3cb958f2406ed5f2")

    def test_worklist_has_semantic_and_execution_support_for_all_roots_but_no_transport_credit(self):
        work=json.loads(WORKLIST.read_text())
        self.assertEqual(work["root_binding_count"],12)
        self.assertEqual(work["verified_root_subject_binding_count"],0)
        self.assertEqual(len(work["roots"]),12)
        for row in work["roots"]:
            self.assertTrue(row["semantic_scoped_support"],row["root_id"])
            self.assertTrue(row["execution_scoped_support"],row["root_id"])
            self.assertGreaterEqual(len(row["current_scoped_support"]),1)
            self.assertFalse(row["new_primitive_required"])
            self.assertEqual(row["same_subject_binding_status"],"OPEN__NO_INDEPENDENT_ROOT_SUBJECT_BINDING_RECEIPT")

    def test_multiscope_gate_consumes_current_21_scope_graph_without_granting_composition(self):
        out=same.evaluate({"root_subject_bindings":[]})
        self.assertEqual(out["status"],"OPEN__SAME_SUBJECT_BINDINGS_REQUIRED",out)
        self.assertEqual(out["scoped_root_count"],12)
        self.assertEqual(out["admitted_scope_count"],21)
        self.assertFalse(out["composition_admissible"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
