from __future__ import annotations
import unittest

from canonical.runtime.root3_three_channel_transaction_graph_v1 import verify


class ThreeChannelTransactionGraphTests(unittest.TestCase):
    def test_baseline_passes(self):
        out=verify()
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual(out["worker_external_channel_count"],3)
        self.assertEqual(out["general_worker_durable_filesystem_commit"],"ABSENT_BY_DESIGN")

    def test_direct_worker_artifact_bypass_fails(self):
        out=verify({("UNTRUSTED_RUNTIME_BLACK_BOX","DURABLE_DECLARED_ARTIFACT")})
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_information_service_bypass_fails(self):
        out=verify({
            ("EXTERNAL_INFORMATION_REQUEST_EXTRACTOR","TRUSTED_EXTERNAL_INFORMATION_SERVICE")
        })
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(
            x.get("sink")=="TRUSTED_EXTERNAL_INFORMATION_SERVICE"
            and x.get("reason")=="DOMINATOR_BYPASS"
            for x in out["failures"]
        ))

    def test_result_to_user_output_bypass_fails(self):
        out=verify({("RESULT_CHANNEL","USER_VISIBLE_LOAD_BEARING_OUTPUT")})
        self.assertEqual(out["status"],"FAIL_CLOSED")


if __name__=="__main__":
    unittest.main(verbosity=2)
