from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

WORKLIST = "canonical/governance/PROFESSIONAL_QUALITY_P1_V7_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V9.json"
PROF = "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
ASSURANCE = "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
MISSION = "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
RESIDUAL = "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def blob(rel):
    data = (ROOT / rel).read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class ProfessionalR3V7CurrentnessTests(unittest.TestCase):
    def test_worklist_is_three_of_twelve_and_r4_next(self):
        w = load(WORKLIST)
        self.assertEqual(w["verified_root_subject_binding_count"], 3)
        r3 = next(x for x in w["roots"] if x["root_id"] == "R3_REALIZATION_OBSERVATION")
        r4 = next(x for x in w["roots"] if x["root_id"] == "R4_MEASUREMENT_CONSTRUCT")
        self.assertTrue(r3["same_subject_binding_status"].startswith("PASS__"))
        self.assertEqual(r3["binding"]["git_blob_sha"], "dbf8665c70c2e9ca432ec03fb0bdf5f17d0adf00")
        self.assertEqual(r3["verification"]["git_blob_sha"], "c4bb2984875312800ea0bb975ce30193a4921d30")
        self.assertTrue(r4["same_subject_binding_status"].startswith("OPEN__"))
        self.assertFalse(w["composition_admissible"])

    def test_professional_pointer_matches_v9_and_preserves_nonclaims(self):
        p = load(PROF)
        f = p["same_subject_root_binding_frontier"]
        self.assertEqual(f["path"], WORKLIST)
        self.assertEqual(f["git_blob_sha"], blob(WORKLIST))
        self.assertEqual(f["verified_root_subject_binding_count"], 3)
        self.assertTrue(p["r3_root_subject_binding"]["root_subject_binding_authority"])
        self.assertFalse(p["r3_root_subject_binding"]["global_r3_root_closed"])
        self.assertFalse(p["quality_authority"])
        self.assertFalse(p["terminal_authority"])
        self.assertFalse(p["live_default"])

    def test_assurance_pointer_matches_current_professional_and_v9(self):
        a = load(ASSURANCE)
        f = a["professional_quality_same_subject_frontier"]
        self.assertEqual(f["current_professional_execution_path"], PROF)
        self.assertEqual(f["current_professional_execution_git_blob_sha"], blob(PROF))
        self.assertEqual(f["root_binding_worklist"]["path"], WORKLIST)
        self.assertEqual(f["root_binding_worklist"]["git_blob_sha"], blob(WORKLIST))
        self.assertEqual(f["root_binding_worklist"]["verified_root_subject_binding_count"], 3)
        self.assertIn("R3_REALIZATION_OBSERVATION", f["current_verified_root_bindings"])
        self.assertFalse(a["terminal_authority"])
        self.assertFalse(a["live_default"])

    def test_mission_projection_binds_current_professional_and_assurance_bytes(self):
        m = load(MISSION)
        self.assertEqual(m["current_professional_quality_execution"]["path"], PROF)
        self.assertEqual(m["current_professional_quality_execution"]["observed_git_blob_sha"], blob(PROF))
        self.assertEqual(m["current_assurance_closure_compiler"]["path"], ASSURANCE)
        self.assertEqual(m["current_assurance_closure_compiler"]["observed_git_blob_sha"], blob(ASSURANCE))
        self.assertEqual(
            m["professional_quality_currentness_reconciliation"]["r3_verification"]["git_blob_sha"],
            "c4bb2984875312800ea0bb975ce30193a4921d30",
        )

    def test_residual_classifier_points_to_r4_without_inflating_closure(self):
        r = load(RESIDUAL)
        row = next(x for x in r["classifications"] if x["residual_id"] == "PROFESSIONAL_QUALITY_BROAD_EXECUTION")
        self.assertEqual(row["current_binding_frontier"]["worklist_path"], WORKLIST)
        self.assertEqual(row["current_binding_frontier"]["worklist_git_blob_sha"], blob(WORKLIST))
        self.assertEqual(row["current_binding_frontier"]["verified_root_subject_binding_count"], 3)
        self.assertEqual(row["current_binding_frontier"]["next_root"], "R4_MEASUREMENT_CONSTRUCT")
        self.assertIn("0_OF_24_GLOBAL_LEAVES_CLOSED", row["current_truth"])
        self.assertEqual(r["accounting"]["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
