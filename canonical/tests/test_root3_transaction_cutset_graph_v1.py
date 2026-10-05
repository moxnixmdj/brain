from __future__ import annotations
import unittest

from canonical.runtime.root3_transaction_cutset_graph_v1 import verify_graph


class TransactionCutsetGraphTests(unittest.TestCase):
    def test_baseline_graph_passes(self):
        out=verify_graph()
        self.assertEqual(out["status"],"PASS",out)
        self.assertTrue(out["sink_evidence"]["DURABLE_FILE_COMMIT"]["all_paths_dominated"])
        self.assertTrue(out["sink_evidence"]["PARENT_STATE_COMMIT"]["all_paths_dominated"])
        self.assertTrue(out["sink_evidence"]["USER_VISIBLE_LOAD_BEARING_OUTPUT"]["all_paths_dominated"])

    def test_direct_worker_to_durable_commit_bypass_fails_closed(self):
        out=verify_graph({
            ("UNTRUSTED_WORKER_BLACK_BOX","DURABLE_FILE_COMMIT"),
        })
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertTrue(
            any(
                x.get("sink")=="DURABLE_FILE_COMMIT"
                and x.get("reason")=="DOMINATOR_BYPASS"
                for x in out["failures"]
            ),
            out,
        )

    def test_worker_to_parent_state_bypass_fails_closed(self):
        out=verify_graph({
            ("UNTRUSTED_WORKER_BLACK_BOX","PARENT_STATE_COMMIT"),
        })
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertTrue(
            any(
                x.get("sink")=="PARENT_STATE_COMMIT"
                and x.get("reason")=="DOMINATOR_BYPASS"
                for x in out["failures"]
            ),
            out,
        )

    def test_result_to_user_output_bypass_fails_closed(self):
        out=verify_graph({
            ("RESULT_CAPTURE","USER_VISIBLE_LOAD_BEARING_OUTPUT"),
        })
        self.assertEqual(out["status"],"FAIL_CLOSED",out)


if __name__=="__main__":
    unittest.main(verbosity=2)
