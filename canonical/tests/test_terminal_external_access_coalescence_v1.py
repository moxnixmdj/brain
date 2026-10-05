from __future__ import annotations
import copy, json, pathlib, unittest
from canonical.runtime.terminal_external_access_coalescence_v1 import compile_cut, AccessCutError

ROOT=pathlib.Path(__file__).resolve().parents[2]
DOC=json.loads((ROOT/"canonical/governance/EXTERNAL_RESULT_ACCESS_COALESCENCE_20261005_V1.json").read_text())

class ExternalAccessCoalescenceTests(unittest.TestCase):
    def test_current_cut_is_exact_and_selects_buildkite(self):
        out=compile_cut(DOC)
        self.assertEqual(out["target_count"],11)
        self.assertEqual(out["lane_count"],6)
        self.assertEqual(out["actionable_lane_count"],2)
        self.assertEqual(out["waiting_lane_count"],4)
        self.assertEqual(out["selected_next_lane"],"L1_BUILDKITE_TB4_CHARTOGRAPHY")
        self.assertEqual(set(out["selected_targets"]),{"CODING_TB4_GE_66_4","CHARTOGRAPHY_TOOLS_GE_89"})

    def test_missing_target_fails_closed(self):
        x=copy.deepcopy(DOC); x["lanes"][0]["targets"].pop()
        with self.assertRaisesRegex(AccessCutError,"TARGET_COVERAGE_DRIFT"):
            compile_cut(x)

    def test_duplicate_target_fails_closed(self):
        x=copy.deepcopy(DOC); x["lanes"][1]["targets"].append("CODING_TB4_GE_66_4")
        with self.assertRaisesRegex(AccessCutError,"TARGET_DUPLICATED_ACROSS_LANES"):
            compile_cut(x)

    def test_wait_lane_must_forbid_duplicate_outreach(self):
        x=copy.deepcopy(DOC); x["lanes"][2]["duplicate_outreach_forbidden"]=False
        with self.assertRaisesRegex(AccessCutError,"WAIT_LANE_MUST_FORBID_DUPLICATE_OUTREACH"):
            compile_cut(x)

    def test_off_frontier_target_fails_closed(self):
        x=copy.deepcopy(DOC); x["lanes"][5]["targets"].append("H100_FULL_FROZEN_BRAIN_CAPABILITY_ENVELOPE")
        with self.assertRaisesRegex(AccessCutError,"TARGET_COVERAGE_DRIFT"):
            compile_cut(x)

if __name__=="__main__":
    unittest.main(verbosity=2)
