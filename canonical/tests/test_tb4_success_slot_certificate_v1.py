import unittest

from canonical.runtime.tb4_success_slot_certificate_v1 import (
    AGGREGATE_SCHEMA,
    CURRENT_REQUIRED_SUCCESSES,
    EXPECTED_PROTOCOL_RECEIPT_BLOB,
    EXPECTED_SCOPE_BLOB,
    EXPECTED_ZERO_SPEND_RECEIPT_BLOB,
    FROZEN_RELEASE_COMMIT,
    SCHEMA,
    aggregate_success_slots,
    certify_slot,
)

H64 = "a" * 64


def scope():
    return {
        "schema": "PROJECT_BRAIN_TB4_EXACT_66_TASK_TARGET_SCOPE_20261008_V1",
        "source": {"release_commit": FROZEN_RELEASE_COMMIT},
        "enumeration": {
            "tasks": [
                {"task": f"task-{i:02d}", "tree_sha": f"{i + 1:040x}"}
                for i in range(66)
            ]
        },
    }


def good(task_index=0, trial_index=1, reward=1, attempt=None):
    return {
        "schema": SCHEMA,
        "frozen_release_commit": FROZEN_RELEASE_COMMIT,
        "authority_bindings": {
            "scope_manifest_git_blob_sha": EXPECTED_SCOPE_BLOB,
            "protocol_receipt_git_blob_sha": EXPECTED_PROTOCOL_RECEIPT_BLOB,
            "zero_spend_receipt_git_blob_sha": EXPECTED_ZERO_SPEND_RECEIPT_BLOB,
        },
        "task": f"task-{task_index:02d}",
        "task_tree_sha": f"{task_index + 1:040x}",
        "trial_index": trial_index,
        "attempt_id": attempt or f"attempt-{task_index:02d}-{trial_index}",
        "actor_config_sha256": "a" * 64,
        "output_sha256": "b" * 64,
        "harbor_result_json_sha256": "c" * 64,
        "actor_output_frozen_before_verifier": True,
        "actor_write_closed_before_verifier": True,
        "hidden_verifier_exposed_to_actor": False,
        "same_task_replay_after_verifier": False,
        "official_frozen_task_bytes_used": True,
        "official_harbor_verifier_completed": True,
        "result_binding_complete": True,
        "declared_success_slot_count": 1,
        "verifier_reward": reward,
    }


class Tests(unittest.TestCase):
    def test_one_pass_is_exactly_one_slot(self):
        v = certify_slot(good(), scope_doc=scope())
        self.assertTrue(v.accepted)
        self.assertEqual(v.success_slot_delta, 1)
        self.assertFalse(v.owner_sandbox_identity_required)
        self.assertFalse(v.execution_authority)
        self.assertFalse(v.replay_authority)

    def test_one_result_cannot_claim_five_slots(self):
        x = good()
        x["declared_success_slot_count"] = 5
        v = certify_slot(x, scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.reason, "SUCCESS_SLOT_MULTIPLICITY_MUST_EQUAL_ONE")

    def test_zero_reward_is_not_a_success_slot(self):
        v = certify_slot(good(reward=0), scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.success_slot_delta, 0)

    def test_task_must_be_in_exact_frozen_scope(self):
        x = good()
        x["task"] = "not-in-scope"
        v = certify_slot(x, scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.reason, "TASK_OUTSIDE_FROZEN_66_SCOPE")

    def test_task_tree_must_match_exact_scope(self):
        x = good()
        x["task_tree_sha"] = "f" * 40
        v = certify_slot(x, scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.reason, "TASK_TREE_SHA_MISMATCH")

    def test_actor_verifier_leak_fails(self):
        x = good()
        x["hidden_verifier_exposed_to_actor"] = True
        v = certify_slot(x, scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.reason, "HIDDEN_VERIFIER_EXPOSURE_NOT_FALSE")

    def test_same_task_replay_after_verifier_fails(self):
        x = good()
        x["same_task_replay_after_verifier"] = True
        v = certify_slot(x, scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.reason, "SAME_TASK_REPLAY_NOT_FALSE")

    def test_duplicate_attempt_fails_aggregate(self):
        rows = [good(0, 1, attempt="same"), good(0, 2, attempt="same")]
        with self.assertRaisesRegex(Exception, "DUPLICATE_ATTEMPT_ID"):
            aggregate_success_slots(rows, scope_doc=scope())

    def test_duplicate_task_trial_slot_fails_aggregate(self):
        rows = [good(0, 1, attempt="a"), good(0, 1, attempt="b")]
        with self.assertRaisesRegex(Exception, "DUPLICATE_TASK_TRIAL_SLOT"):
            aggregate_success_slots(rows, scope_doc=scope())

    def test_219_distinct_successes_meet_current_target(self):
        rows = []
        for task_index in range(43):
            for trial_index in range(1, 6):
                rows.append(good(task_index, trial_index))
        for trial_index in range(1, 5):
            rows.append(good(43, trial_index))
        self.assertEqual(len(rows), 219)
        out = aggregate_success_slots(rows, scope_doc=scope())
        self.assertEqual(out["schema"], AGGREGATE_SCHEMA)
        self.assertEqual(out["certified_success_slots"], CURRENT_REQUIRED_SUCCESSES)
        self.assertTrue(out["threshold_met"])
        self.assertFalse(out["owner_sandbox_identity_required_as_separate_premise"])

    def test_218_distinct_successes_do_not_meet_target(self):
        rows = []
        for task_index in range(43):
            for trial_index in range(1, 6):
                rows.append(good(task_index, trial_index))
        for trial_index in range(1, 4):
            rows.append(good(43, trial_index))
        self.assertEqual(len(rows), 218)
        out = aggregate_success_slots(rows, scope_doc=scope())
        self.assertFalse(out["threshold_met"])
        self.assertEqual(out["remaining_success_slots"], 1)

    def test_wrong_authority_binding_fails(self):
        x = good()
        x["authority_bindings"]["protocol_receipt_git_blob_sha"] = "0" * 40
        v = certify_slot(x, scope_doc=scope())
        self.assertFalse(v.accepted)
        self.assertEqual(v.reason, "PROTOCOL_RECEIPT_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
