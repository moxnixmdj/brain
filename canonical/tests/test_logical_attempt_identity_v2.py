from __future__ import annotations

import unittest

from canonical.runtime.logical_attempt_identity_v2 import (
    LogicalAttemptIdentityError,
    logical_attempt_id,
    logical_attempt_identity,
)

SLOT = "terminal-bench-science/diag-chipseq::trial-0"
TASK = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
CLAIM = "sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
EXPECTED = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"


class LogicalAttemptIdentityV2Tests(unittest.TestCase):
    def test_exact_rank19_claim_bound_identity(self):
        self.assertEqual(
            logical_attempt_id(
                slot_id=SLOT,
                task_digest=TASK,
                execution_claim_binding_digest=CLAIM,
            ),
            EXPECTED,
        )

    def test_identity_object_binds_claim_digest(self):
        out = logical_attempt_identity(
            slot_id=SLOT,
            task_digest=TASK,
            execution_claim_binding_digest=CLAIM,
        )
        self.assertEqual(out["logical_attempt_id"], EXPECTED)
        self.assertEqual(out["execution_claim_binding_digest"], CLAIM)

    def test_claim_digest_change_changes_attempt(self):
        other = "sha256:" + "0" * 64
        self.assertNotEqual(
            logical_attempt_id(
                slot_id=SLOT,
                task_digest=TASK,
                execution_claim_binding_digest=other,
            ),
            EXPECTED,
        )

    def test_slot_change_changes_attempt(self):
        self.assertNotEqual(
            logical_attempt_id(
                slot_id=SLOT + "-other",
                task_digest=TASK,
                execution_claim_binding_digest=CLAIM,
            ),
            EXPECTED,
        )

    def test_task_change_changes_attempt(self):
        other = "sha256:" + "1" * 64
        self.assertNotEqual(
            logical_attempt_id(
                slot_id=SLOT,
                task_digest=other,
                execution_claim_binding_digest=CLAIM,
            ),
            EXPECTED,
        )

    def test_carrier_identity_is_not_an_input(self):
        # There is intentionally no carrier/run/branch argument.
        one = logical_attempt_id(
            slot_id=SLOT,
            task_digest=TASK,
            execution_claim_binding_digest=CLAIM,
        )
        two = logical_attempt_id(
            slot_id=SLOT,
            task_digest=TASK,
            execution_claim_binding_digest=CLAIM,
        )
        self.assertEqual(one, two)

    def test_invalid_claim_digest_fails_closed(self):
        with self.assertRaisesRegex(
            LogicalAttemptIdentityError,
            "EXECUTION_CLAIM_BINDING_DIGEST_INVALID",
        ):
            logical_attempt_id(
                slot_id=SLOT,
                task_digest=TASK,
                execution_claim_binding_digest="not-a-digest",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
