from copy import deepcopy
from pathlib import Path
import json, unittest

from canonical.runtime import professional_r12_semantic_stable_c1_v1 as c1

ROOT = Path(__file__).resolve().parents[2]


def current_inputs():
    r12 = c1._current_r12_claim(ROOT)
    payload = json.loads((ROOT / c1.INPUT_PATH).read_text(encoding="utf-8"))
    assert r12 is not None
    return r12, payload


class StableC1Tests(unittest.TestCase):
    def test_current_stable_claim_c1_passes_scope_only(self):
        out = c1.verify(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["claim_id"], c1.CURRENT_CLAIM_ID)
        self.assertTrue(out["c1_assumption_guarantee_composition_proved"])
        self.assertFalse(out["c8_nonvacuity_proved"])
        self.assertFalse(out["stronger_material_defeater_totality_proved"])
        self.assertFalse(out["semantic_property_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_old_claim_substitution_fails(self):
        r12, payload = current_inputs()
        r12 = deepcopy(r12)
        r12["frozen_claim"]["claim_id"] = c1.OLD_CLAIM_ID
        out = c1.evaluate(r12_claim=r12, composition_payload=payload, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "R12_STABLE_CLAIM_ID_DRIFT")

    def test_missing_root_binding_fails(self):
        r12, payload = current_inputs()
        payload = deepcopy(payload)
        payload["root_subject_bindings"] = payload["root_subject_bindings"][:-1]
        out = c1.evaluate(r12_claim=r12, composition_payload=payload, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SAME_SUBJECT_COMPOSITION_GATE_REJECTED")

    def test_duplicate_root_binding_fails(self):
        r12, payload = current_inputs()
        payload = deepcopy(payload)
        payload["root_subject_bindings"][-1] = deepcopy(payload["root_subject_bindings"][0])
        out = c1.evaluate(r12_claim=r12, composition_payload=payload, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SAME_SUBJECT_COMPOSITION_GATE_REJECTED")

    def test_subject_drift_fails_before_gate(self):
        r12, payload = current_inputs()
        payload = deepcopy(payload)
        payload["subject_sha256"] = "0" * 64
        out = c1.evaluate(r12_claim=r12, composition_payload=payload, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "COMPOSITION_SUBJECT_DRIFT")

    def test_mission_binding_drift_fails(self):
        r12, payload = current_inputs()
        r12 = deepcopy(r12)
        r12["frozen_claim"]["mission_blob_sha"] = "0" * 40
        out = c1.evaluate(r12_claim=r12, composition_payload=payload, repo_root=ROOT)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "R12_MISSION_BINDING_DRIFT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
