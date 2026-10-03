from __future__ import annotations
import copy
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def live_docs():
    return [
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"),
        load("canonical/verification/CURRENT_27_ZERO_REALITY_FRONTIER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/governance/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_V1.json"),
        load("canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
        load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
    ]

class AdaptiveTerminalClosureControllerV2Tests(unittest.TestCase):
    def m(self):
        return importlib.import_module("canonical.runtime.adaptive_terminal_closure_controller_v2")

    def test_live_world_is_exact_post_dual_refinement(self):
        out=self.m().evaluate_repository(ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["live_world"]["unresolved_predicates"],27)
        self.assertEqual(out["live_world"]["nondominated_certificates"],14)
        self.assertEqual(out["live_world"]["verified_zero_reality_requirements"],17)
        self.assertEqual(out["live_world"]["zero_reality_covered_predicates"],25)
        self.assertEqual(out["live_world"]["direct_reality_blocked_predicates"],[
            "FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
        ])
        self.assertEqual(out["live_world"]["matched_primitive_child_facts"],16)
        self.assertEqual(out["action_refinement"]["direct_nonmatched_work_units"],15)
        self.assertEqual(out["action_refinement"]["primitive_acceptance_work_units"],31)
        self.assertEqual(len(out["first_resource_priority_work_unit_ids"]),16)

    def test_matched_parent_requirements_are_replaced_by_16_children(self):
        out=self.m().evaluate_repository(ROOT)
        ids={x["work_unit_id"] for x in out["acceptance_work_units"]}
        self.assertNotIn("MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",ids)
        self.assertNotIn("MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",ids)
        matched=[x for x in out["acceptance_work_units"] if x["lane"]=="MATCHED_TARGET_PROOF"]
        self.assertEqual(len(matched),16)
        self.assertTrue(all(len(x["target_predicates"])==1 for x in matched))
        self.assertTrue(all(x["first_resource_priority"] is True for x in matched))

    def test_tool_discovery_requires_v4_over_v3_v2(self):
        out=self.m().evaluate_repository(ROOT)
        rows=[x for x in out["acceptance_work_units"]
              if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in x["target_predicates"]]
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertTrue(row["mandatory_tool_discovery_v4_gate"])
        self.assertEqual(
            row["source_hints"][0],
            "MANDATORY_TOOL_DISCOVERY_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE_RETRIEVAL_GATE",
        )
        self.assertIn("DIVERSITY_PRESERVING_FEDERATION_WITH_ROUTER_RECEIPTS",row["source_hints"])

    def test_v10_or_v3_only_scheduling_fails_closed(self):
        docs=copy.deepcopy(live_docs())
        docs[-1]["status"]="ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V10_CURRENT"
        docs[-1]["mandatory_tool_discovery_retrieval"]["authority"]="V3_OVER_VERIFIED_V2_BASE"
        out=self.m().evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("SCHEDULING_AUTHORITY_NOT_CURRENT_V12_INDEPENDENT_PASS",out["errors"])
        self.assertIn("TOOL_DISCOVERY_NOT_V4_OVER_V3_V2",out["errors"])

    def test_two_direct_reality_predicates_are_not_zero_reality_work_units(self):
        out=self.m().evaluate_repository(ROOT)
        zero_targets={p for row in out["acceptance_work_units"] for p in row["target_predicates"]}
        self.assertNotIn("FINANCE_UNCOVERED_SCOPE_AUDIT",zero_targets)
        self.assertNotIn("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",zero_targets)
        self.assertTrue(all(x["globally_authorized"] is False for x in out["direct_reality_blocked_work_units"]))

    def test_accepted_unowned_families_reconcile_in_parallel(self):
        out=self.m().evaluate_repository(ROOT)
        self.assertEqual(
            {x["family"] for x in out["ownership_reconciliation_work_units"]},
            {"SUBAGENT_DELEGATION_AND_COORDINATION","SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"},
        )

    def test_probability_history_is_scheduling_only(self):
        m=self.m()
        base=m.evaluate_repository(ROOT)
        uid=base["acceptance_work_units"][0]["work_unit_id"]
        out=m.evaluate(*live_docs(),attempt_history={
            uid:{"verified_successes":3,"verified_failures":1,"total_wall_seconds":40}
        })
        row=next(x for x in out["acceptance_work_units"] if x["work_unit_id"]==uid)
        p=row["empirical_posterior"]
        self.assertEqual((p["alpha"],p["beta"]),(4,2))
        self.assertAlmostEqual(p["posterior_mean_verified_discharge_probability"],4/6)
        self.assertEqual(p["mean_wall_seconds"],10.0)
        self.assertTrue(p["promotion_use_forbidden"])
        self.assertFalse(out["promotion_authority"])

    def test_unknown_probability_is_never_invented(self):
        out=self.m().evaluate_repository(ROOT)
        self.assertEqual(out["probability_policy"]["empirically_scored_work_unit_count"],0)
        self.assertFalse(out["probability_policy"]["unknown_success_probability_may_be_invented"])
        self.assertTrue(all(x["empirical_posterior"] is None for x in out["acceptance_work_units"]))

    def test_early_fresh_reality_permission_fails_closed(self):
        docs=copy.deepcopy(live_docs())
        docs[-1]["fresh_reality_authority"]=True
        out=self.m().evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("SCHEDULING_AUTHORITY_FRESH_REALITY_LEAK",out["errors"])

    def test_controller_never_grants_credit_or_authority(self):
        out=self.m().evaluate_repository(ROOT)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        for k in ("acceptance_credit_delta","capability_credit_delta","family_credit_delta",
                  "ownership_credit_delta","incremental_spend_usd","new_reality_units_consumed"):
            self.assertEqual(out[k],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
