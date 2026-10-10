from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped
from canonical.runtime import professional_quality_leaf_coverage_projection_v2 as cover
from canonical.runtime import professional_quality_same_subject_composition_gate_v1 as same

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
SUBJECT = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_DECLARED_SYSTEM_SUBJECT_20261010_V2.json"
WORKLIST = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V2.json"


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class ProfessionalQualityFullBoundedSemanticFrontierV1Tests(unittest.TestCase):
    def test_current_pointer_matches_live_scoped_and_leaf_projection(self):
        cur = json.loads(CURRENT.read_text(encoding="utf-8"))
        s = scoped.evaluate()
        p = cover.project()
        self.assertTrue(s["pass"], s)
        self.assertTrue(p["pass"], p)
        self.assertEqual(s["admitted_scope_count"], 21)
        self.assertEqual(p["partial_coverage_leaf_count"], 24)
        self.assertEqual(p["semantic_partial_coverage_leaf_count"], 12)
        self.assertEqual(p["execution_partial_coverage_leaf_count"], 12)
        self.assertEqual(p["no_scoped_evidence_leaf_count"], 0)
        self.assertEqual(p["verified_global_leaf_count"], 0)
        self.assertFalse(p["global_leaf_closure"])
        self.assertEqual(cur["scoped_evidence"]["admitted_scope_count"], 21)
        self.assertEqual(cur["leaf_coverage_projection"]["partial_coverage_leaf_count"], 24)
        self.assertEqual(cur["leaf_coverage_projection"]["no_scoped_evidence_leaf_count"], 0)
        self.assertFalse(cur["live_default"])
        self.assertFalse(cur["quality_authority"])

    def test_declared_subject_v2_is_content_current_and_hash_correct(self):
        doc = json.loads(SUBJECT.read_text(encoding="utf-8"))
        for row in doc["system_material"]["components"]:
            p = ROOT / row["path"]
            self.assertTrue(p.is_file(), row)
            self.assertEqual(_blob(p), row["git_blob_sha"], row)
        canonical = json.dumps(
            doc["system_material"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        self.assertEqual(
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            doc["subject_sha256"],
        )
        self.assertEqual(doc["evidence_state"]["admitted_scoped_capability_count"], 21)
        self.assertEqual(doc["evidence_state"]["no_scoped_evidence_leaf_count"], 0)

    def test_worklist_has_all_twelve_roots_with_bounded_semantic_and_execution_support(self):
        work = json.loads(WORKLIST.read_text(encoding="utf-8"))
        self.assertEqual(work["root_binding_count"], 12)
        self.assertEqual(work["verified_root_subject_binding_count"], 0)
        self.assertEqual(len(work["roots"]), 12)
        for row in work["roots"]:
            self.assertTrue(row["semantic_scoped_support"], row["root_id"])
            self.assertTrue(row["execution_scoped_support"], row["root_id"])
            self.assertGreaterEqual(len(row["current_scoped_support"]), 1)
            self.assertFalse(row["new_primitive_required"])

    def test_same_subject_gate_consumes_live_multiscope_registry_without_granting_credit(self):
        out = same.evaluate({"root_subject_bindings": []})
        self.assertEqual(out["status"], "OPEN__SAME_SUBJECT_BINDINGS_REQUIRED", out)
        self.assertEqual(out["scoped_root_count"], 12)
        self.assertEqual(out["admitted_scope_count"], 21)
        self.assertFalse(out["composition_admissible"])
        self.assertFalse(out["professional_quality_closed"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
