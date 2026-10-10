from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

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
                "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT__CONCRETE_DECISION_BOUND_TARGET_REQUIRED",
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
            self.assertTrue(out["default_evidence_acquisition_provider_bound"])
            self.assertEqual(
                out["evidence_provider_result"]["status"],
                "OPEN__PENDING_ACQUISITION_OR_EXPERIMENT__CONCRETE_DECISION_BOUND_TARGET_REQUIRED",
            )
            self.assertFalse(
                out["evidence_provider_result"]["broad_acquisition_attempted"]
            )
            self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
