from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v14 as agent
from execution_guard.logical_attempt_identity_v1 import logical_attempt_id as logical_attempt_id_v1
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as logical_attempt_id_v2


SLOT = "terminal-bench-science/example::trial-0"
TASK = "sha256:" + "1" * 64
CLAIM = "sha256:" + "2" * 64


class HarborScienceAgentV14ClaimBoundIdentityTests(unittest.TestCase):
    def test_legacy_v1_identity_still_passes_without_claim_digest(self):
        expected = logical_attempt_id_v1(slot_id=SLOT, task_digest=TASK)
        with patch.dict(
            os.environ,
            {
                "BRAIN_SLOT_ID": SLOT,
                "BRAIN_TASK_DIGEST": TASK,
                "BRAIN_LOGICAL_ATTEMPT_ID": expected,
            },
            clear=True,
        ):
            self.assertEqual(agent.logical_attempt_id_for_goal("goal"), expected)

    def test_claim_bound_v2_identity_passes_when_digest_present(self):
        expected = logical_attempt_id_v2(
            slot_id=SLOT,
            task_digest=TASK,
            execution_claim_binding_digest=CLAIM,
        )
        with patch.dict(
            os.environ,
            {
                "BRAIN_SLOT_ID": SLOT,
                "BRAIN_TASK_DIGEST": TASK,
                "BRAIN_LOGICAL_ATTEMPT_ID": expected,
                "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST": CLAIM,
            },
            clear=True,
        ):
            self.assertEqual(agent.logical_attempt_id_for_goal("goal"), expected)

    def test_claim_bound_surface_rejects_legacy_v1_identity(self):
        legacy = logical_attempt_id_v1(slot_id=SLOT, task_digest=TASK)
        with patch.dict(
            os.environ,
            {
                "BRAIN_SLOT_ID": SLOT,
                "BRAIN_TASK_DIGEST": TASK,
                "BRAIN_LOGICAL_ATTEMPT_ID": legacy,
                "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST": CLAIM,
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH"
            ):
                agent.logical_attempt_id_for_goal("goal")

    def test_missing_carried_identity_fails_closed(self):
        with patch.dict(
            os.environ,
            {
                "BRAIN_SLOT_ID": SLOT,
                "BRAIN_TASK_DIGEST": TASK,
                "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST": CLAIM,
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "BRAIN_LOGICAL_ATTEMPT_ID_REQUIRED"
            ):
                agent.logical_attempt_id_for_goal("goal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
