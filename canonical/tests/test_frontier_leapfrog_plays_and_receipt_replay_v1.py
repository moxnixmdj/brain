"""Verification tests for receipt input replay, declaration-floor projection,
unified `swe_kernel` organ routing, and Frontier Leapfrog Plays 1, 2, 3, and 6.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import (  # noqa: E402
    abstain_gated_skill_induction_v1 as play3,
    adversarial_mutation_admission_gate_v1 as play6,
    brain_unified_model_v1 as unified,
    capability_receipt_lane_v1 as lane,
    gradient_free_law_consolidation_v1 as play2,
    state_contract_world_model_v1 as play1,
    swe_kernel_organ_bridge_v1 as bridge,
)


class ReceiptReplayAndFloorTests(unittest.TestCase):
    def test_restore_snapshot_inputs_rehydrates_tmp_and_refuses_outside_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            payload = b'{"x": 42}\n'
            digest = hashlib.sha256(payload).hexdigest()
            store_dir = Path(scratch) / lane.INSTANCE_STORE
            store_dir.mkdir(parents=True, exist_ok=True)
            (store_dir / f"{digest}.bin").write_bytes(payload)

            tmp_rel = "canonical/astra_runtime/tmp/replay_case/in.json"
            ok = lane.restore_snapshot_inputs(
                scratch, {"input_path": tmp_rel}, {"input_path": digest}
            )
            self.assertTrue(ok)
            self.assertEqual((Path(scratch) / tmp_rel).read_bytes(), payload)

            # Attempting to materialize a missing file outside canonical/astra_runtime/tmp/ MUST fail closed!
            escaped = lane.restore_snapshot_inputs(
                scratch, {"input_path": "canonical/runtime/evil.py"}, {"input_path": digest}
            )
            self.assertFalse(escaped)
            self.assertFalse((Path(scratch) / "canonical/runtime/evil.py").exists())

    def test_verify_producer_receipts_replays_contract_args_and_input_digests(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / lane.BOUND).parent.mkdir(parents=True, exist_ok=True)
            (root / lane.BOUND).write_text('{"capabilities": {}}', encoding="utf-8")
            (root / lane.EXTENDED).write_text('{"capabilities": {}}', encoding="utf-8")

            in_rel = "canonical/astra_runtime/tmp/unit_case/data.txt"
            (root / in_rel).parent.mkdir(parents=True, exist_ok=True)
            (root / in_rel).write_text("alpha-beta\n", encoding="utf-8")

            mod_rel = "canonical/runtime/sample_contract.py"
            (root / mod_rel).write_text(
                "from pathlib import Path\n"
                "def run(args, root):\n"
                "    p = Path(root) / args['input_path']\n"
                "    text = p.read_text(encoding='utf-8').strip()\n"
                "    return {'status': 'OK', 'upper': text.upper(), 'k': int(args['k'])}\n",
                encoding="utf-8",
            )
            cid = "canonical.runtime.sample_contract.hidden.v1"
            rec = lane.execute_and_receipt(
                cid, mod_rel, "run", scratch, "producer-a", "contract",
                probe_args={"input_path": in_rel, "k": 7},
            )
            self.assertIsNotNone(rec)
            rpath = root / lane.receipt_path_for(cid)
            rpath.parent.mkdir(parents=True, exist_ok=True)
            rec["receipt_path"] = lane.receipt_path_for(cid)
            rpath.write_text(json.dumps(rec, indent=1, sort_keys=True), encoding="utf-8")

            # Wipe scratch tmp completely so replay MUST rehydrate from instances/*.bin!
            shutil.rmtree(root / "canonical/astra_runtime/tmp")
            ver = lane.verify_producer_receipts(scratch, "verifier-b", {})
            self.assertEqual(ver["reproduced"], 1)
            self.assertEqual(ver["mismatched"], 0)
            self.assertEqual(ver["capability_ids"], [cid])

    def test_cli_projection_entry_declares_expect_exit_zero(self) -> None:
        fake_cli_receipt = {
            "capability_id": "sample.cli.v1",
            "kind": "cli",
            "module_path": "canonical/tools/sample_cli.py",
            "module_sha256": "a" * 64,
            "entrypoint": "run",
            "invoked_args": {"argv": ["python3", "canonical/tools/sample_cli.py"]},
            "observed": {"returncode": 0},
            "receipt_path": "canonical/astra_runtime/evidence/CAPABILITY__sample.cli.v1__EXECUTION_RECEIPT.json",
            "independent_verifier": None,
        }
        proj = lane.projection_entry(fake_cli_receipt)
        self.assertEqual(proj["action_template"]["args"]["expect_exit"], 0)


class UnifiedOrgansAndLeapfrogPlaysTests(unittest.TestCase):
    def test_all_13_swe_kernel_organs_live_via_bridge_and_unified_model(self) -> None:
        probe = bridge.probe_all_organs(ROOT)
        self.assertEqual(probe["status"], "ALL_ORGANS_LIVE")
        self.assertEqual(probe["organs_total"], 13)
        self.assertEqual(probe["organs_live"], 13)

        model = unified.open_model()
        inventory = model.frontier_organs()
        self.assertEqual(inventory["swe_kernel_organs_count"], 13)
        self.assertEqual(inventory["leapfrog_plays_count"], 8)
        self.assertEqual(inventory["total_organs"], 21)

        ir_res = model.invoke_frontier_organ("guarded_meaning_ir", {})
        self.assertEqual(ir_res["status"], "OK")
        self.assertTrue(ir_res["egraph_rollback_clean"])

    def test_play_1_contract_world_model_catches_state_loss_and_prevents_loops(self) -> None:
        r1 = play1.run({}, ROOT)
        r2 = play1.run({}, ROOT)
        self.assertEqual(r1["trace_sha256"], r2["trace_sha256"])
        self.assertGreaterEqual(r1["delta_prediction_accuracy"], 0.60)
        self.assertEqual(r1["state_loss_events_caught"], 3)
        self.assertEqual(r1["unobservable_effects_refused"], 1)
        self.assertGreater(r1["action_loops_prevented"], 0)
        self.assertTrue(r1["workflow_completed"])
        self.assertFalse(r1["kill_criterion"]["kill_triggered"])

    def test_play_2_gradient_free_law_consolidation_compresses_and_reports_heldout_honestly(self) -> None:
        r = play2.run({}, ROOT)
        self.assertEqual(r["corpus_commits_total"], 45)
        self.assertLess(r["laws_after"], r["laws_before"])
        self.assertGreaterEqual(r["compression_ratio"], 0.50)
        self.assertGreater(r["clean_refutation_power_after"], r["clean_refutation_power_before"])
        self.assertEqual(r["false_refutations_after"], 0)
        # Held-out drop (1 -> 0 after pruning false-refuter) must be reported transparently, never hidden
        self.assertTrue(r["kill_criterion"]["kill_triggered"])

    def test_play_3_abstain_gated_skill_induction_beats_ungated_precision_and_transfers(self) -> None:
        r = play3.run({}, ROOT)
        self.assertEqual(r["episodes_total"], 40)
        self.assertEqual(r["test_probes_total"], 120)
        self.assertGreater(r["precision"], 0.50)
        self.assertGreater(r["precision"], r["ungated_baseline_precision"])
        self.assertGreater(r["cross_family_transfer_hits"], 0)
        self.assertGreaterEqual(r["unseen_negative_refusal_rate"], 0.90)
        self.assertFalse(r["kill_criterion"]["kill_triggered"])

    def test_play_6_mutation_gate_detects_corrupted_outputs_and_names_survivors(self) -> None:
        r = play6.run({}, ROOT)
        self.assertEqual(r["capabilities_tested"], 4)
        self.assertGreaterEqual(r["mutants_killed_by_receipt_oracle"], 3)
        self.assertIsInstance(r["surviving_mutants"], list)


if __name__ == "__main__":
    unittest.main()
