from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v13 as agent
from execution_guard.logical_attempt_identity_v1 import logical_attempt_id as v1_id
from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as v2_id

SLOT = "terminal-bench-science/diag-chipseq::trial-0"
TASK = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
CLAIM = "sha256:4e9cae8c879a8122f11fe6ae7eea775fcc4fb0ae62b3a87e208a95d28ea4d05f"
EXPECTED_V2 = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"
OBSERVED_V1 = "def7e2921acf58d4ef03e3183512996c718a5a13069482cb825464c0c963a8b4"


def env(carried: str = EXPECTED_V2, claim: str = CLAIM) -> dict[str, str]:
    return {
        "BRAIN_SLOT_ID": SLOT,
        "BRAIN_TASK_DIGEST": TASK,
        "BRAIN_LOGICAL_ATTEMPT_ID": carried,
        "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST": claim,
    }


class AgentV13ClaimBoundIdentityTests(unittest.TestCase):
    def test_exact_rank19_v2_identity_passes(self):
        self.assertEqual(
            v2_id(
                slot_id=SLOT,
                task_digest=TASK,
                execution_claim_binding_digest=CLAIM,
            ),
            EXPECTED_V2,
        )
        with patch.dict(os.environ, env(), clear=True):
            self.assertEqual(
                agent.logical_attempt_id_for_goal("synthetic goal"),
                EXPECTED_V2,
            )

    def test_old_v1_identity_is_provably_different_and_rejected(self):
        self.assertEqual(v1_id(slot_id=SLOT, task_digest=TASK), OBSERVED_V1)
        self.assertNotEqual(OBSERVED_V1, EXPECTED_V2)
        with patch.dict(os.environ, env(carried=OBSERVED_V1), clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH"
            ):
                agent.logical_attempt_id_for_goal("synthetic goal")

    def test_missing_claim_binding_digest_fails_closed(self):
        bad = env()
        bad.pop("BRAIN_EXECUTION_CLAIM_BINDING_DIGEST")
        with patch.dict(os.environ, bad, clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "BRAIN_EXECUTION_CLAIM_BINDING_DIGEST_REQUIRED"
            ):
                agent.logical_attempt_id_for_goal("synthetic goal")

    def test_claim_digest_change_changes_identity_and_rejects_carried_id(self):
        other = "sha256:" + "0" * 64
        self.assertNotEqual(
            v2_id(
                slot_id=SLOT,
                task_digest=TASK,
                execution_claim_binding_digest=other,
            ),
            EXPECTED_V2,
        )
        with patch.dict(os.environ, env(claim=other), clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "BRAIN_LOGICAL_ATTEMPT_ID_MISMATCH"
            ):
                agent.logical_attempt_id_for_goal("synthetic goal")

    def test_goal_text_is_not_identity_material(self):
        with patch.dict(os.environ, env(), clear=True):
            one = agent.logical_attempt_id_for_goal("goal one")
            two = agent.logical_attempt_id_for_goal("different goal text")
        self.assertEqual(one, EXPECTED_V2)
        self.assertEqual(two, EXPECTED_V2)


class AgentV14SourceCompileTests(unittest.TestCase):
    def test_v14_and_v8_source_compile(self):
        for rel in (
            "canonical/runtime/harbor_science_agent_v14.py",
            "canonical/runtime/harbor_science_planner_v8.py",
        ):
            src = Path(rel).read_text(encoding="utf-8")
            compile(src, rel, "exec")


if __name__ == "__main__":
    unittest.main(verbosity=2)
