from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from execution_guard.logical_attempt_identity_v1 import logical_attempt_id as logical_attempt_id_v1
from canonical.runtime.logical_attempt_identity_v2 import logical_attempt_id as logical_attempt_id_v2
from canonical.runtime import harbor_science_agent_v13 as agent


SLOT="terminal-bench-science/test-slot::trial-0"
DIGEST="sha256:" + "1"*64
CLAIM="sha256:" + "2"*64
GOAL="test goal"


class TestHarborScienceAgentV13LogicalAttemptIdentity(unittest.TestCase):
    def _env(self, *, carried: str, claim: str | None = None):
        env={
            "BRAIN_SLOT_ID":SLOT,
            "BRAIN_TASK_DIGEST":DIGEST,
            "BRAIN_LOGICAL_ATTEMPT_ID":carried,
        }
        if claim is not None:
            env["BRAIN_EXECUTION_CLAIM_BINDING_DIGEST"]=claim
        return patch.dict(os.environ,env,clear=True)

    def test_legacy_v1_identity_remains_valid_without_claim_digest(self):
        carried=logical_attempt_id_v1(slot_id=SLOT,task_digest=DIGEST)
        with self._env(carried=carried):
            self.assertEqual(agent.logical_attempt_id_for_goal(GOAL),carried)

    def test_claim_bound_v2_identity_is_required_when_claim_digest_present(self):
        carried=logical_attempt_id_v2(
            slot_id=SLOT,
            task_digest=DIGEST,
            execution_claim_binding_digest=CLAIM,
        )
        with self._env(carried=carried,claim=CLAIM):
            self.assertEqual(agent.logical_attempt_id_for_goal(GOAL),carried)

    def test_legacy_v1_identity_is_rejected_when_claim_digest_present(self):
        carried=logical_attempt_id_v1(slot_id=SLOT,task_digest=DIGEST)
        with self._env(carried=carried,claim=CLAIM):
            with self.assertRaisesRegex(RuntimeError,"V2_CLAIM_BOUND"):
                agent.logical_attempt_id_for_goal(GOAL)

    def test_wrong_v2_identity_is_rejected(self):
        wrong_claim="sha256:" + "3"*64
        carried=logical_attempt_id_v2(
            slot_id=SLOT,
            task_digest=DIGEST,
            execution_claim_binding_digest=wrong_claim,
        )
        with self._env(carried=carried,claim=CLAIM):
            with self.assertRaisesRegex(RuntimeError,"V2_CLAIM_BOUND"):
                agent.logical_attempt_id_for_goal(GOAL)


if __name__=="__main__":
    unittest.main(verbosity=2)
