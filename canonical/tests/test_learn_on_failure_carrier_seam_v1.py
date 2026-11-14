"""The carrier refusal must not sever the read-only learn-on-failure seam.

Measured on the live tree before this repair: `solve()` returned
`FAIL__RAW_GOAL_COMPILATION_GAP` with `executed: False`, while
`solve_or_learn()` returned the generic admitted-confinement status with
`side_effects_may_exist: True` and no ignorance-ledger/JIT record.  The
effectful documentation fallback was refused, but that refusal also swallowed
the only precise learning signal the controller had.

These tests pin the narrow repair:

* an unexecuted learnable compile gap keeps its precise status, records the gap,
  and may read external knowledge;
* the carrier decision is preserved under `carrier_gate`, not deleted;
* naming a program is still not permission to run it, even `--help`;
* prior execution or uncertain effects still keep the carrier answer;
* disabling gap recording or JIT network access disables exactly this read-only
  learning surface, not the safety refusal.

Producer-run regression tests.  Authority NONE.  No capability credit.
"""
from __future__ import annotations

import os
import pathlib
import tempfile
import unittest
from unittest import mock

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import ignorance_ledger_v1 as ledger
from canonical.runtime import jit_knowledge_v1 as jit
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime.memory_policy_v1 import READ_ONLY, memory_policy_scope
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

GAP = "FAIL__RAW_GOAL_COMPILATION_GAP"
GAP_CLASS = "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP"


class LearnOnFailureCarrierSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-carrier-seam-")
        self.root = pathlib.Path(self.tmp.name)
        self.ledger_path = self.root / "ignorance.json"
        self._old_ledger = ledger.DEFAULT_STATE
        ledger.DEFAULT_STATE = str(self.ledger_path)
        self.front = {
            "pass": False,
            "status": GAP,
            "failure_class": GAP_CLASS,
            "executed": False,
        }
        self.knowledge = {
            "status": jit.PASS,
            "pass": True,
            "complete": True,
            "document_count": 2,
            "documents": [
                {"id": "example-audio-tool", "title": "Audio transcription tool"},
                {"id": "example-docs", "title": "Documentation"},
            ],
            "sources_answered": ["pypi", "github"],
            "kinds_answered": ["package_registry", "code_host"],
            "min_kinds_required": 2,
            "authority": "EXTERNAL_PUBLIC_EVIDENCE_FETCHED",
        }

    def tearDown(self) -> None:
        ledger.DEFAULT_STATE = self._old_ledger
        self.tmp.cleanup()

    def _solve(self, goal: str = "transcribe the audio in this recording to text", **kwargs):
        with mock.patch.object(controller, "recall_and_execute_workflow", return_value=None), \
             mock.patch.object(door, "solve", return_value=dict(self.front)), \
             mock.patch.object(jit, "resolve", return_value=dict(self.knowledge)) as resolve, \
             mock.patch.object(VerifiedSkillStore, "count", return_value=0), \
             mock.patch.object(cenv, "perform", return_value={"pass": False}) as perform:
            result = controller.solve_or_learn(
                {"task_id": "seam", "goal": goal},
                allow_tier1_composition=False,
                **kwargs,
            )
        return result, resolve, perform

    def test_unexecuted_compile_gap_keeps_reason_and_reaches_ledger_and_knowledge(self) -> None:
        result, resolve, perform = self._solve()
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], GAP)
        self.assertEqual(result["failure_class"], GAP_CLASS)
        self.assertFalse(result["executed"])
        self.assertFalse(result["side_effects_may_exist"])
        self.assertEqual(result["carrier_gate"]["status"], boundary.STATUS)
        self.assertTrue(result["refusal_precedes_the_carrier_gate"])
        self.assertFalse(result["documentation_fallback_executed"])
        learned = result["learning"]
        self.assertTrue(learned["gap_recorded"])
        self.assertTrue(learned["gap_id"])
        self.assertIn("transcribe the audio in this recording to text", learned["what_to_learn_next"])
        self.assertTrue(learned["knowledge"]["complete"])
        self.assertGreaterEqual(len(learned["knowledge"]["kinds_answered"]), 2)
        self.assertFalse(learned["attempted"])
        resolve.assert_called()
        perform.assert_not_called()
        rows = ledger.rank(limit=5)
        self.assertTrue(any(row["what"] == "transcribe the audio in this recording to text" for row in rows))

    def test_named_program_is_not_run_even_for_help(self) -> None:
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        marker = self.root / "ran"
        exe = bin_dir / "fixture-audio-command"
        exe.write_text("#!/bin/sh\nprintf ran > '" + str(marker) + "'\n", encoding="utf-8")
        exe.chmod(0o700)
        with mock.patch.dict(os.environ, {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")}):
            result, _, perform = self._solve(goal="use fixture-audio-command to transcribe the audio in this recording to text")
        self.assertFalse(marker.exists(), "named executable ran without admitted confinement")
        perform.assert_not_called()
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], GAP)
        learned = result["learning"]
        self.assertEqual(learned["executable"], "fixture-audio-command")
        self.assertEqual(learned["executable_status"], boundary.STATUS)
        self.assertFalse(learned["attempted"])

    def test_prior_effects_are_not_erased_by_the_learning_seam(self) -> None:
        self.front.update(executed=True, side_effects_may_exist=True)
        result, resolve, perform = self._solve()
        self.assertFalse(result["pass"])
        self.assertTrue(result["executed"])
        self.assertTrue(result["side_effects_may_exist"])
        self.assertNotIn("refusal_precedes_the_carrier_gate", result)
        self.assertNotIn("learning", result)
        resolve.assert_not_called()
        perform.assert_not_called()

    def test_disabling_gap_recording_keeps_the_carrier_refusal(self) -> None:
        result, resolve, _ = self._solve(record_open_gap=False, allow_jit_network=False)
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], boundary.STATUS)
        self.assertFalse(result["learning"]["gap_recorded"])
        resolve.assert_not_called()
        self.assertFalse(self.ledger_path.exists())

    def test_disabling_jit_network_still_records_the_gap_without_external_knowledge(self) -> None:
        result, resolve, _ = self._solve(allow_jit_network=False)
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], GAP)
        self.assertTrue(result["learning"]["gap_recorded"])
        self.assertNotIn("knowledge", result["learning"])
        resolve.assert_not_called()

    def test_read_only_memory_does_not_claim_a_persisted_gap_or_credit_jit_sources(self) -> None:
        with memory_policy_scope(READ_ONLY):
            result, resolve, _ = self._solve()
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], boundary.STATUS)
        self.assertFalse(result["learning"]["gap_recorded"])
        self.assertNotIn("gap_id", result["learning"])
        self.assertNotIn("knowledge", result["learning"])
        self.assertFalse(self.ledger_path.exists())
        resolve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
