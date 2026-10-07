import unittest

from canonical.runtime.terminal_autopilot_v1 import plan


OPEN = [
    "CODING_TB4_GE_66_4",
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_CURSORBENCH_GE_57_8",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT",
    "AUTOMATIONBENCH_GE_40",
    "HLE_TOOLS_GE_67_7",
    "TB_SCIENCE_GE_58_7",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "FINANCE_AGENT_V2_GE_58_59",
    "MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER",
]


def manifest():
    return {
        "terminal": False,
        "zero_incremental_spend_hard_stop": True,
        "max_concurrency": 16,
        "obligations": [{"id": x, "status": "OPEN"} for x in OPEN],
        "blockers": [{
            "id": "TB_SCIENCE_CARRIER_CLOSURE",
            "status": "OPEN",
            "unlocks": ["TB_SCIENCE_GE_58_7"],
            "repair_action": "BUILD_VERIFY_TB_SCIENCE_TRANSITIVE_CARRIER_CLOSURE",
        }],
        "routes": [{
            "id": "SCOPE_COMPLETE_UNIVERSAL_COVER",
            "status": "OPEN",
            "can_discharge": OPEN,
        }],
        "active_jobs": [],
    }


class TerminalAutopilotTests(unittest.TestCase):
    def test_fans_out_all_runnable_work_and_repairs_blocker(self):
        out = plan(manifest())
        self.assertTrue(out["pass"], out)
        kinds = [x["kind"] for x in out["dispatch"]]
        self.assertIn("REPAIR", kinds)
        self.assertIn("ROUTE_RACE", kinds)
        direct_targets = {x["obligation_ids"][0] for x in out["dispatch"] if x["kind"] == "EVIDENCE"}
        self.assertNotIn("TB_SCIENCE_GE_58_7", direct_targets)
        self.assertEqual(len(direct_targets), 12)
        self.assertEqual(len(out["dispatch"]), 14)

    def test_blocker_closure_unlocks_tb_science_without_human_replan(self):
        m = manifest()
        m["blockers"][0]["status"] = "CLOSED"
        out = plan(m)
        direct_targets = {x["obligation_ids"][0] for x in out["dispatch"] if x["kind"] == "EVIDENCE"}
        self.assertIn("TB_SCIENCE_GE_58_7", direct_targets)
        self.assertEqual(len(direct_targets), 13)

    def test_result_flows_to_verify_then_promote(self):
        m = manifest()
        m["obligations"][0]["status"] = "RESULT_PRESENT"
        out = plan(m)
        self.assertEqual(out["verify"][0]["obligation_ids"], [OPEN[0]])
        m["obligations"][0]["status"] = "VERIFIED"
        out = plan(m)
        self.assertEqual(out["promote"][0]["obligation_ids"], [OPEN[0]])

    def test_terminal_true_cancels_active_jobs(self):
        m = manifest()
        m["terminal"] = True
        m["active_jobs"] = [{"id": "job1", "lease_key": "x", "obligation_ids": [OPEN[0]]}]
        out = plan(m)
        self.assertEqual(out["dispatch"], [])
        self.assertEqual(out["cancel"], ["job1"])


if __name__ == "__main__":
    unittest.main()
