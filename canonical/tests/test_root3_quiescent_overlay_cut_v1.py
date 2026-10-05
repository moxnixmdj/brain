from __future__ import annotations

import unittest

from canonical.runtime.root3_quiescent_overlay_cut_v1 import verify


class QuiescentOverlayCutTests(unittest.TestCase):
    def test_baseline_passes_with_one_semantic_channel(self):
        out = verify()
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["semantic_worker_channel_count"], 1)
        self.assertEqual(
            out["semantic_worker_channels"],
            ["PRIVATE_OVERLAY_SNAPSHOT"],
        )
        self.assertEqual(out["live_worker_broker_fd"], "ABSENT_BY_DESIGN")

    def test_live_worker_result_channel_fails_closed(self):
        out = verify({
            ("UNTRUSTED_RUNTIME_BLACK_BOX", "RESULT_CHANNEL"),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(any(
            row.get("reason") == "LIVE_OR_DIRECT_WORKER_CHANNEL_ADDED"
            for row in out["failures"]
        ))

    def test_direct_worker_durable_artifact_bypass_fails_closed(self):
        out = verify({
            ("UNTRUSTED_RUNTIME_BLACK_BOX", "DURABLE_DECLARED_ARTIFACT"),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_result_to_user_output_bypass_fails_closed(self):
        out = verify({
            ("TYPED_JOURNAL_CLASSIFIER", "USER_VISIBLE_LOAD_BEARING_OUTPUT"),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(any(
            row.get("sink") == "USER_VISIBLE_LOAD_BEARING_OUTPUT"
            and row.get("reason") == "DOMINATOR_BYPASS"
            for row in out["failures"]
        ))

    def test_live_information_service_response_fails_closed(self):
        out = verify({
            ("TRUSTED_INFORMATION_SERVICE", "UNTRUSTED_RUNTIME_BLACK_BOX"),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(any(
            row.get("reason") == "LIVE_INFORMATION_RESPONSE_BYPASS"
            for row in out["failures"]
        ))

    def test_information_admission_bypass_fails_closed(self):
        out = verify({
            ("INFORMATION_REQUEST_ENTRY", "TRUSTED_INFORMATION_SERVICE"),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertTrue(any(
            row.get("sink") == "TRUSTED_INFORMATION_SERVICE"
            and row.get("reason") == "DOMINATOR_BYPASS"
            for row in out["failures"]
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
