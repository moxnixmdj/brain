from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import one_shot_reality_closure_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


class RealityClosureV2IntegrationTests(unittest.TestCase):
    def test_real_v1_cleanroom_empty_state_reaches_v2_fixed_point(self):
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

            self.assertTrue(out["pass"], out)
            self.assertTrue(out["fixed_point"], out)
            self.assertEqual(
                out["status"],
                "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
            )
            self.assertEqual(out["repair_rounds_executed"], 0)
            self.assertEqual(
                out["final_closure"]["status"],
                "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
            )
            self.assertEqual(out["transcript"][0]["gap_class"], "NONE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
