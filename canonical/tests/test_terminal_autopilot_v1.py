import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_autopilot_v1 import build_manifest_from_repo, plan


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
        "blockers": [],
        "routes": [{"id": "SCOPE_COMPLETE_UNIVERSAL_COVER", "status": "OPEN", "can_discharge": OPEN}],
        "active_jobs": [],
    }


class TerminalAutopilotTests(unittest.TestCase):
    def test_fans_out_all_direct_work_and_universal_race(self):
        out = plan(manifest())
        self.assertTrue(out["pass"], out)
        self.assertEqual(sum(x["kind"] == "EVIDENCE" for x in out["dispatch"]), 13)
        self.assertEqual(sum(x["kind"] == "ROUTE_RACE" for x in out["dispatch"]), 1)
        self.assertEqual(len(out["dispatch"]), 14)

    def test_active_target_is_not_dispatched_twice(self):
        m = manifest()
        m["obligations"][7]["status"] = "RUNNING"
        m["active_jobs"] = [{"id": "rank9", "lease_key": "existing-intent::rank9",
                             "obligation_ids": ["TB_SCIENCE_GE_58_7"]}]
        out = plan(m)
        direct = {x["obligation_ids"][0] for x in out["dispatch"] if x["kind"] == "EVIDENCE"}
        self.assertNotIn("TB_SCIENCE_GE_58_7", direct)
        self.assertEqual(len(direct), 12)

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

    def test_repo_mode_reads_quotient_and_existing_tb_intent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            q = root / "canonical/governance"
            a = root / "canonical/action_intents"
            q.mkdir(parents=True)
            a.mkdir(parents=True)
            (q / "FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json").write_text(
                json.dumps({"independent_open_obligations": OPEN}), encoding="utf-8")
            (a / "ACTION_INTENT_TB_SCIENCE_RANK9_ONE_SHOT_20261007_V1.json").write_text(
                json.dumps({"status": "READY_AFTER_TRANSITIVE_CARRIER_CLOSURE_AND_LIVE_EPOCH_BINDING"}),
                encoding="utf-8")
            built = build_manifest_from_repo(root)
            tb = [x for x in built["obligations"] if x["id"] == "TB_SCIENCE_GE_58_7"][0]
            self.assertEqual(tb["status"], "RUNNING")
            out = plan(built)
            direct = {x["obligation_ids"][0] for x in out["dispatch"] if x["kind"] == "EVIDENCE"}
            self.assertNotIn("TB_SCIENCE_GE_58_7", direct)
            routes = {
                x["route_id"]
                for x in out["dispatch"]
                if x["kind"] == "ROUTE_RACE"
            }
            self.assertIn("SCOPE_COMPLETE_UNIVERSAL_COVER", routes)
            self.assertIn("OBJECTIVE_ACCEPTANCE_COMMON_LAW", routes)
            self.assertIn("CODING_TRIAD_SCOPE_COMPLETE_COVER", routes)
            self.assertIn("FINANCE_MYSTERY_COMMON_POLICY_COVER", routes)
            self.assertIn("PROFESSIONAL_QUALITATIVE_ROBUST_DOMINANCE", routes)
            self.assertLessEqual(len(direct), 12)


    def test_repo_mode_blocks_stale_science_intent_after_authority_consumed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            q = root / "canonical/governance"
            a = root / "canonical/action_intents"
            q.mkdir(parents=True)
            a.mkdir(parents=True)
            (q / "FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json").write_text(
                json.dumps({"independent_open_obligations": OPEN}), encoding="utf-8")
            (q / "CURRENT_TERMINAL_AUTHORITY.json").write_text(json.dumps({
                "live_truth": {
                    "tb_science_rank9_authority_active": False,
                    "tb_science_rank9_execution_authority_consumed": True,
                    "tb_science_rank10_authority_active": False,
                    "tb_science_planner_grammar_repair_candidate_bound": True,
                    "tb_science_planner_grammar_repair_live_transport_verified": False,
                }
            }), encoding="utf-8")
            (a / "ACTION_INTENT_TB_SCIENCE_RANK9_ONE_SHOT_20261007_V1.json").write_text(
                json.dumps({"status": "READY_AFTER_TRANSITIVE_CARRIER_CLOSURE_AND_LIVE_EPOCH_BINDING"}),
                encoding="utf-8")
            built = build_manifest_from_repo(root)
            tb = [x for x in built["obligations"] if x["id"] == "TB_SCIENCE_GE_58_7"][0]
            self.assertEqual(tb["status"], "BLOCKED")
            self.assertEqual(len(built["active_jobs"]), 0)
            self.assertEqual(built["blockers"][0]["unlocks"], ["TB_SCIENCE_GE_58_7"])
            out = plan(built)
            direct = {
                x["obligation_ids"][0]
                for x in out["dispatch"]
                if x["kind"] == "EVIDENCE"
            }
            self.assertNotIn("TB_SCIENCE_GE_58_7", direct)
            repairs = [x for x in out["dispatch"] if x["kind"] == "REPAIR"]
            self.assertEqual(len(repairs), 1)
            self.assertEqual(
                repairs[0]["action_id"],
                "repair::TB_SCIENCE_PLANNER_TRANSPORT_PREFLIGHT",
            )
            routes = {
                x["route_id"]
                for x in out["dispatch"]
                if x["kind"] == "ROUTE_RACE"
            }
            self.assertIn("SCOPE_COMPLETE_UNIVERSAL_COVER", routes)

    def test_repo_mode_allows_science_intent_only_with_live_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            q = root / "canonical/governance"
            a = root / "canonical/action_intents"
            q.mkdir(parents=True)
            a.mkdir(parents=True)
            (q / "FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json").write_text(
                json.dumps({"independent_open_obligations": OPEN}), encoding="utf-8")
            (q / "CURRENT_TERMINAL_AUTHORITY.json").write_text(json.dumps({
                "live_truth": {
                    "tb_science_rank9_authority_active": False,
                    "tb_science_rank10_authority_active": True,
                }
            }), encoding="utf-8")
            (a / "ACTION_INTENT_TB_SCIENCE_RANK10_ONE_SHOT_20261007_V1.json").write_text(
                json.dumps({"status": "READY_AFTER_PREFLIGHT"}),
                encoding="utf-8")
            built = build_manifest_from_repo(root)
            tb = [x for x in built["obligations"] if x["id"] == "TB_SCIENCE_GE_58_7"][0]
            self.assertEqual(tb["status"], "RUNNING")
            self.assertEqual(len(built["blockers"]), 0)


    def test_repo_mode_installs_one_shot_attack_graph(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            q = root / "canonical/governance"
            q.mkdir(parents=True)
            (q / "FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json").write_text(
                json.dumps({"independent_open_obligations": OPEN}), encoding="utf-8")
            built = build_manifest_from_repo(root)
            self.assertTrue(built["one_shot_attack_graph"])
            by_id = {row["id"]: row for row in built["routes"]}
            self.assertEqual(len(by_id), 6)
            self.assertEqual(
                set(by_id["SCOPE_COMPLETE_UNIVERSAL_COVER"]["can_discharge"]),
                set(OPEN),
            )
            self.assertEqual(
                set(by_id["CODING_TRIAD_SCOPE_COMPLETE_COVER"]["can_discharge"]),
                {
                    "CODING_TB4_GE_66_4",
                    "CODING_FRONTIERCODE_GE_54_4",
                    "CODING_CURSORBENCH_GE_57_8",
                },
            )
            for route in by_id.values():
                self.assertFalse(route["promotion_authority"])
                self.assertFalse(route["terminal_credit"])
                self.assertTrue(set(route["can_discharge"]).issubset(set(OPEN)))


if __name__ == "__main__":
    unittest.main()
