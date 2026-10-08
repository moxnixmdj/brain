from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct


class R2VisualCodeDirectIntegrationV1Tests(unittest.TestCase):
    @patch.object(direct.visual_code_adequacy, "preflight")
    def test_visual_code_family_is_reachable_from_direct_preflight(self, preflight):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_VISUAL_CODE_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "image.qr.generate.qrencode",
            "policy_id": "BOUND_CAPABILITY_POLICY::qr::goal",
            "goal_sha256": "a" * 64,
            "format": "QR",
            "payload_sha256": "b" * 64,
            "output_path": "canonical/out.png",
        }
        out = direct.preflight({"task_id": "visual", "goal": "not another direct grammar"})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["route_id"], direct.VISUAL_CODE_ROUTE_ID)
        self.assertEqual(out["capability_id"], "image.qr.generate.qrencode")
        self.assertFalse(out["preflight_execution_authority"])

    @patch.object(direct.visual_code_adequacy, "run")
    @patch.object(direct.visual_code_adequacy, "preflight")
    def test_visual_code_verified_acceptance_becomes_direct_adequacy(
        self, preflight, run
    ):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_VISUAL_CODE_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "image.qr.generate.qrencode",
            "policy_id": "BOUND_CAPABILITY_POLICY::qr::goal",
            "goal_sha256": "a" * 64,
            "format": "QR",
            "payload_sha256": "b" * 64,
            "output_path": "canonical/out.png",
        }
        run.return_value = {
            "pass": True,
            "status": "PASS__TRANSACTIONAL_VISUAL_CODE_POLICY_ADEQUACY_VERIFIED",
            "capability_id": "image.qr.generate.qrencode",
            "policy_id": "BOUND_CAPABILITY_POLICY::qr::goal",
            "goal_sha256": "a" * 64,
            "accepted_raw_obligation_ids": ["RAWREQ:x"],
            "raw_acceptance_obligation_count": 1,
            "raw_result": {"pass": True},
            "authority_boundary": "bounded visual-code family",
        }
        out = direct.run({"task_id": "visual", "goal": "not another direct grammar"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["direct_adequacy_authority"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(
            out["selected_policy_id"],
            "BOUND_CAPABILITY_POLICY::qr::goal",
        )

    @patch.object(direct.visual_code_adequacy, "run")
    @patch.object(direct.visual_code_adequacy, "preflight")
    def test_visual_code_failure_never_falls_through(self, preflight, run):
        preflight.return_value = {
            "matched": True,
            "status": "DIRECT_VISUAL_CODE_ADEQUACY_ROUTE_MATCHED",
            "capability_id": "image.qr.generate.qrencode",
            "policy_id": "BOUND_CAPABILITY_POLICY::qr::goal",
            "goal_sha256": "a" * 64,
            "format": "QR",
            "payload_sha256": "b" * 64,
            "output_path": "canonical/out.png",
        }
        run.return_value = {
            "pass": False,
            "status": "OPEN__INDEPENDENT_VISUAL_CODE_ACCEPTANCE_DID_NOT_VERIFY",
            "transaction_rolled_back": True,
        }
        with patch.object(direct.typed_decision_adequacy, "run") as typed, \
             patch.object(direct.table_adequacy, "run") as table, \
             patch.object(direct.codec_adequacy, "run") as codec, \
             patch.object(direct.docx_adequacy, "run") as docx, \
             patch.object(direct.docx_json_adequacy, "run") as docx_json, \
             patch.object(direct.live_bound, "run_raw_goal") as legacy:
            out = direct.run({"task_id": "visual", "goal": "not another direct grammar"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        typed.assert_not_called()
        table.assert_not_called()
        codec.assert_not_called()
        docx.assert_not_called()
        docx_json.assert_not_called()
        legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
