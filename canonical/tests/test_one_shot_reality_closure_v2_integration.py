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
                "OPEN__CAPABILITY_SYNTHESIS_PROVIDER_REQUIRED",
            )
            self.assertEqual(
                out["gap_contract"]["gap_class"],
                "CONSTRUCTIVE_CAPABILITY_GAP",
            )
            self.assertEqual(
                out["transcript"][0]["closure_status"],
                "OPEN__INTERNAL_UNSOLVED_R2_GAP_REMAINS",
            )
            internal = out["gap_contract"]["basis"]["internal_blockers"]
            self.assertTrue(
                any(
                    str(blocker).startswith("R2_CURRENT_INTERNAL_UNSOLVED:")
                    for blocker in internal
                ),
                out,
            )
            self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
