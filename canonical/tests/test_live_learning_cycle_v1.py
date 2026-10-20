"""The learning cycle's plumbing, without depending on any bound tool.

The point of this suite is the handoff, not the answers: the cycle must carry a
durable store forward across runs, must refuse a store the store's own loader
rejects instead of dying on it, and must drain the improvement queue with the
Brain-owned independent verifier rather than its own opinion.  All three run
with zero goals, so nothing here needs jq, pandoc, sqlite3 or tesseract.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning  # noqa: E402
from execution_guard import live_learning_cycle_v1 as cycle  # noqa: E402


class LiveLearningCyclePlumbing(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.state_path = Path(learning.DEFAULT_STATE_PATH)
        self._state_existed = self.state_path.exists()
        self._state_backup = None
        if self._state_existed:
            self._state_backup = self.tmp / "prior_state.json"
            shutil.copyfile(self.state_path, self._state_backup)

    def tearDown(self) -> None:
        if self._state_existed and self._state_backup is not None:
            shutil.copyfile(self._state_backup, self.state_path)
        elif not self._state_existed:
            self.state_path.unlink(missing_ok=True)
        self._tmp.cleanup()

    def _run(self, name: str = "run", **kwargs) -> dict:
        out = self.tmp / name
        out.mkdir(parents=True, exist_ok=True)
        receipt = cycle.run(
            out=out,
            state_in=kwargs.pop("state_in", None),
            goal_count=kwargs.pop("goal_count", 0),
            max_rounds=kwargs.pop("max_rounds", 1),
            max_actions=kwargs.pop("max_actions", 1),
            seed=kwargs.pop("seed", None),
            observe=kwargs.pop("observe", False),
        )
        self.assertEqual(kwargs, {}, "unexpected leftover kwargs")
        return receipt

    def test_zero_goal_cycle_reaches_a_fixed_point_and_carries_the_store(self):
        learning._write_state(learning._empty_state(), self.state_path)
        r = self._run()
        self.assertEqual(r["schema"], cycle.SCHEMA)
        self.assertEqual(r["goals_generated"], 0)
        self.assertEqual(r["attempts"], [])
        self.assertIs(r["promotion_before"]["pass"], True, r["promotion_before"])
        self.assertTrue(r["promotion_before"]["fixed_point"], r["promotion_before"])
        self.assertIn("experience_v1.json", r["carried"])
        self.assertIn(cycle.STATE_NAME, r["carried"])
        self.assertEqual(r["authority"], "NONE")
        self.assertEqual(r["terminal_credit_delta"], 0)

    def test_store_survives_a_handoff(self):
        learning._write_state(learning._empty_state(), self.state_path)
        first = self._run("first")
        carried_dir = self.tmp / "first"
        self.assertTrue((carried_dir / cycle.STATE_NAME).is_file())
        self.state_path.unlink(missing_ok=True)

        second = self._run("second", state_in=carried_dir)
        self.assertIs(second["state_restore"]["restored"], True, second["state_restore"])
        self.assertEqual(
            second["state_restore"]["sha256"], first["carried"][cycle.STATE_NAME]
        )

    def test_a_store_the_loader_rejects_is_quarantined_not_trusted(self):
        bad = self.tmp / "state_in"
        bad.mkdir()
        (bad / cycle.STATE_NAME).write_text("{\"schema\": \"NOT_THE_STORE\"}", encoding="utf-8")
        self.state_path.unlink(missing_ok=True)

        r = self._run(state_in=bad)
        self.assertIs(r["state_restore"]["restored"], False, r["state_restore"])
        self.assertEqual(
            r["state_restore"]["reason"], "STATE_ARTIFACT_REJECTED_BY_STORE_LOADER"
        )
        self.assertFalse(self.state_path.exists(), "a rejected store must not be installed")
        quarantine = Path(r["state_restore"]["quarantined_as"])
        self.assertTrue(quarantine.is_file())
        # the cycle still completed instead of crashing
        self.assertEqual(r["promotion_before"]["status"], "VERIFIED_R3_FIXED_POINT_REACHED")

    def test_receipt_writes_both_artifacts(self):
        learning._write_state(learning._empty_state(), self.state_path)
        out = self.tmp / "receipt_out"
        self.assertEqual(cycle.main(["--out", str(out), "--goals", "0", "--no-observe"]), 0)
        self.assertTrue((out / "LIVE_LEARNING_CYCLE_RECEIPT.json").is_file())
        summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn("live learning cycle", summary)


if __name__ == "__main__":
    unittest.main()
