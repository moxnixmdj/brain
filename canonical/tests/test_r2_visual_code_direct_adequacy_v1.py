from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_visual_code_direct_adequacy_v1 as visual


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical/astra_runtime/tmp"
QR = TMP / "R2_VISUAL_CODE_QR.png"
BAR = TMP / "R2_VISUAL_CODE_CODE128.png"

QR_GOAL = (
    'Generate a QR code image encoding exactly "PROJECT BRAIN 42" and save it to '
    "canonical/astra_runtime/tmp/R2_VISUAL_CODE_QR.png."
)
BAR_GOAL = (
    'Generate a Code 128 barcode image encoding exactly "PROJECT BRAIN 42" and save it to '
    "canonical/astra_runtime/tmp/R2_VISUAL_CODE_CODE128.png."
)


class R2VisualCodeDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        for p in (QR, BAR):
            if p.exists():
                p.unlink()

    def tearDown(self):
        for p in (QR, BAR):
            if p.exists():
                p.unlink()

    def test_real_registry_preflight_selects_qr_verified_producer(self):
        out = visual.preflight({"task_id": "qr", "goal": QR_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_VISUAL_CODE_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["format"], "QR")
        self.assertEqual(out["capability_id"], "image.qr.generate.qrencode")
        self.assertEqual(out["verifier_capability_id"], "image.code.decode.zbarimg")
        self.assertFalse(out["preflight_execution_authority"])
        self.assertTrue(set(out["producer_packages"]).isdisjoint(out["verifier_packages"]))

    def test_real_registry_preflight_selects_code128_verified_producer(self):
        out = visual.preflight({"task_id": "code128", "goal": BAR_GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["format"], "CODE128")
        self.assertEqual(out["capability_id"], "auto.apt.zint")
        self.assertEqual(out["verifier_capability_id"], "image.code.decode.zbarimg")
        self.assertTrue(set(out["producer_packages"]).isdisjoint(out["verifier_packages"]))

    def test_extra_instruction_is_outside_exact_family(self):
        out = visual.preflight({
            "task_id": "extra",
            "goal": QR_GOAL + " Then upload it somewhere.",
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    def test_unquoted_payload_is_outside_exact_family(self):
        out = visual.preflight({
            "task_id": "unquoted",
            "goal": (
                "Generate a QR code image encoding exactly PROJECT BRAIN 42 and save it to "
                "canonical/astra_runtime/tmp/R2_VISUAL_CODE_QR.png."
            ),
        })
        self.assertFalse(out["matched"])

    @patch.object(visual.live_bound, "run_raw_goal")
    def test_exact_independent_decode_commits_and_proves_adequacy(self, execute):
        pf = visual.preflight({"task_id": "qr-pass", "goal": QR_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            QR.write_bytes(b"\x89PNG\r\n\x1a\nproducer")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = visual.run(
            {"task_id": "qr-pass", "goal": QR_GOAL},
            verifier_provider=lambda p: {
                "verified": True,
                "producer_independent": True,
                "supplier_packages_disjoint": True,
                "decoded_payload": p["payload"],
            },
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(
            len(out["accepted_raw_obligation_ids"]),
            out["raw_acceptance_obligation_count"],
        )

    @patch.object(visual.live_bound, "run_raw_goal")
    def test_wrong_decoded_payload_rolls_back_new_artifact(self, execute):
        pf = visual.preflight({"task_id": "qr-mismatch", "goal": QR_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            QR.write_bytes(b"\x89PNG\r\n\x1a\nbad")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = visual.run(
            {"task_id": "qr-mismatch", "goal": QR_GOAL},
            verifier_provider=lambda p: {
                "verified": True,
                "producer_independent": True,
                "supplier_packages_disjoint": True,
                "decoded_payload": "WRONG",
            },
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(QR.exists())

    @patch.object(visual.live_bound, "run_raw_goal")
    def test_failed_decode_restores_preexisting_artifact(self, execute):
        old = b"old-visual-code"
        QR.write_bytes(old)
        pf = visual.preflight({"task_id": "qr-restore", "goal": QR_GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(request):
            QR.write_bytes(b"\x89PNG\r\n\x1a\nreplacement")
            return {
                "pass": True,
                "compiled_capability_id": pf["capability_id"],
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = visual.run(
            {"task_id": "qr-restore", "goal": QR_GOAL},
            verifier_provider=lambda p: {
                "verified": False,
                "producer_independent": True,
                "supplier_packages_disjoint": True,
                "decoded_payload": "",
            },
        )
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(QR.read_bytes(), old)


if __name__ == "__main__":
    unittest.main(verbosity=2)
