import unittest
from copy import deepcopy

from canonical.runtime import coverage_cc_r3_mission_scope_bridge_guard_v1 as guard


def live():
    return guard.validate()


class CC_R3MissionScopeBridgeGuardTests(unittest.TestCase):
    def test_current_state_passes_with_bridge_open_and_conjunct_open(self):
        out = live()
        self.assertTrue(out["pass"], out["errors"])
        self.assertFalse(out["mission_scope_bridge_proved"])
        self.assertEqual(out["cc_r3_real_mission_conjunct"], "OPEN__UNKNOWN")
        self.assertFalse(out["checkpoint_u_empty_real_mission_closure_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_recorded_countermodel_is_internally_consistent(self):
        status = guard._load_json(guard.STATUS_PATH)
        model = status["defect_record"]["countermodel"]
        guard._validate_countermodel(model)  # must not raise
        self.assertEqual(model["witness"], ["b"])

    def test_countermodel_tamper_witness_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        model = deepcopy(status["defect_record"]["countermodel"])
        model["witness"] = ["a"]
        with self.assertRaises(guard.CC_R3ScopeBridgeError):
            guard._validate_countermodel(model)

    def test_countermodel_u_not_empty_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        model = deepcopy(status["defect_record"]["countermodel"])
        model["checkpoint_scope"] = ["a", "b"]  # U_checkpoint no longer empty
        with self.assertRaises(guard.CC_R3ScopeBridgeError):
            guard._validate_countermodel(model)

    def test_checkpoint_u_empty_cannot_be_granted_real_mission_authority(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["cc_r3_real_mission_conjunct"]["closed_by_checkpoint_u_empty_alone"] = True
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertIn("CHECKPOINT_U_EMPTY_GRANTED_REAL_MISSION_CLOSURE_AUTHORITY", out["errors"])

    def test_real_mission_conjunct_cannot_close_without_bridge(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["cc_r3_real_mission_conjunct"]["status"] = "CLOSED"
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertIn("REAL_MISSION_CONJUNCT_NOT_OPEN", out["errors"])

    def test_live_abc_closed_without_bridge_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        authority = guard._load_json(guard.TERMINAL_AUTHORITY_PATH)
        tampered_authority = deepcopy(authority)
        tampered_authority["live_truth"]["complete_selected_context_ABC_closed"] = True
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=tampered_authority)
        self.assertFalse(out["pass"])
        self.assertIn("LIVE_ABC_CLOSED_WITHOUT_BRIDGE", out["errors"])

    def test_live_terminal_true_without_bridge_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        authority = guard._load_json(guard.TERMINAL_AUTHORITY_PATH)
        tampered_authority = deepcopy(authority)
        tampered_authority["live_truth"]["terminal"] = True
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=tampered_authority)
        self.assertFalse(out["pass"])
        self.assertIn("LIVE_TERMINAL_TRUE_WITHOUT_BRIDGE", out["errors"])

    def test_uncleared_cc_r3_claim_scope_fails_closed(self):
        # a checkpoint-scoped U-empty claim bound to the CC_R3 slot without a
        # declaration (and without a proved bridge) must be rejected
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["declared_non_real_mission_closure_claims"] = []
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertIn("CC_R3_CLAIM_SCOPE_NOT_CLEARED_FOR_REAL_MISSION_POSTURE", out["errors"])

    def test_declared_claim_with_real_mission_closure_claimed_true_is_not_cleared(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["declared_non_real_mission_closure_claims"][0]["real_mission_closure_claimed"] = True
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertIn("CC_R3_CLAIM_SCOPE_NOT_CLEARED_FOR_REAL_MISSION_POSTURE", out["errors"])

    def test_proved_bridge_requires_content_addressed_theorem_and_verification(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["mission_scope_bridge"] = {
            "proved": True,
            "form": "SCOPE_CONTAINMENT",
            "theorem_path": None,
            "theorem_git_blob_sha": None,
            "independent_verification_path": None,
            "independent_verification_git_blob_sha": None,
        }
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertTrue(any("BRIDGE_" in e for e in out["errors"]), out["errors"])

    def test_proved_bridge_with_stale_blob_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["mission_scope_bridge"] = {
            "proved": True,
            "form": "REAL_MISSION_U",
            "theorem_path": "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json",
            "theorem_git_blob_sha": "0" * 40,
            "independent_verification_path": "canonical/verification/R4_ACYCLIC_LIVE_BINDING_CURRENTNESS_20261010_V1.json",
            "independent_verification_git_blob_sha": "0" * 40,
        }
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertTrue(any("BRIDGE_BLOB_STALE" in e for e in out["errors"]), out["errors"])

    def test_registry_blob_drift_fails_closed(self):
        import json
        import tempfile
        from pathlib import Path
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["bindings"]["root_registry_git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "status.json"
            tmp.write_text(json.dumps(doc))
            original = guard.STATUS_PATH
            guard.STATUS_PATH = tmp
            try:
                out = guard.validate()
            finally:
                guard.STATUS_PATH = original
        self.assertFalse(out["pass"])
        self.assertIn("REGISTRY_BINDING_STALE", out["errors"])

    def test_nonzero_accounting_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["accounting"]["terminal_credit_delta"] = 1
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertIn("NONZERO_ACCOUNTING:terminal_credit_delta", out["errors"])

    def test_schema_drift_fails_closed(self):
        status = guard._load_json(guard.STATUS_PATH)
        doc = deepcopy(status)
        doc["schema"] = "OTHER_SCHEMA"
        out = guard.validate(doc, registry=guard._load_json(guard.REGISTRY_PATH),
                             terminal_authority=guard._load_json(guard.TERMINAL_AUTHORITY_PATH))
        self.assertFalse(out["pass"])
        self.assertIn("SCHEMA_DRIFT", out["errors"])


if __name__ == "__main__":
    unittest.main()
