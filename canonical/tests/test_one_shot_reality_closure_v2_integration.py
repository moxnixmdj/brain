from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import one_shot_reality_closure_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


class RealityClosureV2IntegrationTests(unittest.TestCase):
    def test_empty_r3_state_does_not_hide_current_r2_internal_gap(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            state_path = Path(td) / "state.json"
            state = learning._empty_state()
            learning._write_state(state, state_path)

            out = v2.run(
                repo_root=ROOT,
                state_path=state_path,
                max_repair_rounds=1,
            )

            self.assertFalse(out["pass"], out)
            self.assertEqual(
                out["status"],
                "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT_PROVIDER_REQUIRED",
            )
            self.assertEqual(
                out["gap_contract"]["gap_class"],
                "PENDING_ACQUISITION_OR_EXPERIMENT",
            )
            self.assertEqual(
                out["transcript"][0]["closure_status"],
                "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            )
            basis = out["gap_contract"]["basis"]
            self.assertEqual(basis["constructive_internal_blockers"], [])
            self.assertEqual(basis["r2_acquisition_request_count"], 1)
            self.assertEqual(
                basis["evidence_blockers"],
                ["R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL"],
            )
            request = basis["r2_acquisition_requests"][0]
            self.assertEqual(request["cell_id"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")
            self.assertFalse(request["full_benchmark_default"])
            self.assertTrue(
                request["broad_acquisition_forbidden_without_minimality_proof"]
            )
            self.assertEqual(
                out["gap_contract"]["constructive_capability_contract_count"],
                0,
            )
            self.assertFalse(out["terminal_authority"])


    def _solved_closure(self, initial="i1", final="f1"):
        return {
            "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
            "status": "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
            "pass": True,
            "fixed_point": True,
            "closure_class": "NO_CURRENT_INTERNAL_IMPROVEMENT_WORK_REMAINS",
            "initial_frontier_digest": initial,
            "final_frontier_digest": final,
            "final_state_sha256": "a" * 64,
            "irreducible_external_information_proved": False,
            "residual": {
                "class": "NONE",
                "internal_blockers": [],
                "evidence_blockers": [],
                "irreducible_external_information_proved": False,
            },
        }

    def test_infrastructure_repair_is_recorded_and_resolved_in_r3_ledger(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            state_path = Path(td) / "state.json"
            learning._write_state(learning._empty_state(), state_path)
            repair_requests = []

            def repair(request):
                repair_requests.append(request)
                return {
                    "pass": True,
                    "infrastructure_repaired": True,
                    "verification_authority_mutated": False,
                    "receipt_sha256": "7" * 64,
                    "reuse_first_attempted": False,
                }

            with patch.object(
                v2.v1,
                "run",
                side_effect=[
                    RuntimeError("runner unavailable"),
                    self._solved_closure(),
                ],
            ):
                out = v2.run(
                    repo_root=ROOT,
                    state_path=state_path,
                    infrastructure_repair_provider=repair,
                    max_repair_rounds=2,
                )

            state = learning.load_state(state_path)

        self.assertTrue(out["pass"], out)
        self.assertEqual(len(repair_requests), 1)
        request = repair_requests[0]
        self.assertFalse(request["reuse_first_required"])
        self.assertTrue(request["learning_failure_fingerprint"])
        self.assertTrue(request["learning_retry_capsule_sha256"])

        failures = list(state["failures"].values())
        self.assertEqual(len(failures), 1)
        receipts = failures[0]["repair_receipts"]
        self.assertEqual(len(receipts), 1)
        self.assertTrue(next(iter(receipts.values()))["original_replay_pass"])

        repair_work = [
            row for row in state["improvement_queue"].values()
            if row["kind"] == "REPAIR_FAILURE_CLASS"
        ]
        self.assertEqual(len(repair_work), 1)
        self.assertEqual(repair_work[0]["status"], "RESOLVED")
        self.assertIn(
            "INFRASTRUCTURE_REPAIR_REPLAY_VERIFIED__R3_REPAIR_LEDGER_RESOLVED",
            [row.get("status") for row in out["transcript"]],
        )

    def test_repeated_infrastructure_failure_forces_reuse_first(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            state_path = Path(td) / "state.json"
            learning._write_state(learning._empty_state(), state_path)
            requests = []

            def repair(request):
                requests.append(request)
                prior = request["prior_verified_repair_receipts"]
                reused = sorted(prior)[0] if prior else None
                return {
                    "pass": True,
                    "infrastructure_repaired": True,
                    "verification_authority_mutated": False,
                    "receipt_sha256": ("8" if not prior else "9") * 64,
                    "reuse_first_attempted": bool(prior),
                    "reused_repair_receipt_sha256": reused,
                }

            for suffix in ("a", "b"):
                with patch.object(
                    v2.v1,
                    "run",
                    side_effect=[
                        RuntimeError("runner unavailable"),
                        self._solved_closure(
                            initial="i-" + suffix,
                            final="f-" + suffix,
                        ),
                    ],
                ):
                    out = v2.run(
                        repo_root=ROOT,
                        state_path=state_path,
                        infrastructure_repair_provider=repair,
                        max_repair_rounds=2,
                    )
                self.assertTrue(out["pass"], out)

            state = learning.load_state(state_path)

        self.assertEqual(len(requests), 2)
        self.assertFalse(requests[0]["reuse_first_required"])
        self.assertTrue(requests[1]["reuse_first_required"])
        self.assertTrue(requests[1]["prior_verified_repair_receipts"])

        repair_work = [
            row for row in state["improvement_queue"].values()
            if row["kind"] == "REPAIR_FAILURE_CLASS"
        ]
        self.assertEqual(len(repair_work), 1)
        self.assertGreaterEqual(repair_work[0]["reopen_count"], 1)
        self.assertEqual(repair_work[0]["status"], "RESOLVED")



if __name__ == "__main__":
    unittest.main(verbosity=2)
