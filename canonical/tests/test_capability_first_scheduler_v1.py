from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime import capability_first_scheduler_v1 as s


ROOT = Path(__file__).resolve().parents[2]


class CapabilityFirstSchedulerV1Tests(unittest.TestCase):
    def test_benchmark_bookkeeping_is_hard_demoted(self):
        out = s.rank_work([
            {
                "work_id": "GDPVAL_ELO_RECONSTRUCTION",
                "work_type": "BENCHMARK_INSTRUMENTATION",
                "benchmark_role": "BOOKKEEPING",
                "expected_capability_gain_lcb": 0,
                "expected_efficiency_gain_lcb": 0,
                "expected_reliability_gain_lcb": 0,
                "reuse_breadth_lcb": 1,
                "generalization_lcb": 1,
                "success_probability_lcb": "1",
                "wall_clock_cost_ub": 1,
                "compute_cost_ub": 1,
                "memory_cost_ub": 1,
                "complexity_cost_ub": 1,
            }
        ])
        self.assertEqual(out["ranked"][0]["eligibility"], "DEMOTED_BENCHMARK_BOOKKEEPING")
        self.assertEqual(out["ranked"][0]["priority_score"], "0")

    def test_capability_build_beats_benchmark_certification(self):
        out = s.rank_work([
            {
                "work_id": "GENERALIZE_RELEVANCE_CEGAR",
                "work_type": "CAPABILITY_BUILD",
                "expected_capability_gain_lcb": 9,
                "expected_efficiency_gain_lcb": 8,
                "expected_reliability_gain_lcb": 7,
                "reuse_breadth_lcb": 10,
                "generalization_lcb": 9,
                "success_probability_lcb": "9/10",
                "wall_clock_cost_ub": 2,
                "compute_cost_ub": 2,
                "memory_cost_ub": 1,
                "complexity_cost_ub": 2,
            },
            {
                "work_id": "OPUS_MILESTONE_CERTIFICATION",
                "work_type": "BENCHMARK_INSTRUMENTATION",
                "benchmark_role": "MILESTONE_CERTIFICATION",
                "expected_capability_gain_lcb": 0,
                "expected_efficiency_gain_lcb": 0,
                "expected_reliability_gain_lcb": 1,
                "reuse_breadth_lcb": 2,
                "generalization_lcb": 2,
                "success_probability_lcb": "1",
                "wall_clock_cost_ub": 1,
                "compute_cost_ub": 1,
                "memory_cost_ub": 1,
                "complexity_cost_ub": 1,
            },
        ])
        self.assertEqual(out["ranked"][0]["work_id"], "GENERALIZE_RELEVANCE_CEGAR")
        self.assertEqual(
            out["milestone"],
            "OPUS_5_5_FIRST_FRONTIER_CHECKPOINT__NOT_TERMINAL_OBJECTIVE",
        )
        self.assertEqual(
            out["mission_objective"],
            "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE",
        )

    def test_lower_resource_cost_wins_when_benefit_equal(self):
        common = {
            "work_type": "EFFICIENCY_IMPROVEMENT",
            "expected_capability_gain_lcb": 4,
            "expected_efficiency_gain_lcb": 6,
            "expected_reliability_gain_lcb": 2,
            "reuse_breadth_lcb": 8,
            "generalization_lcb": 8,
            "success_probability_lcb": "4/5",
        }
        out = s.rank_work([
            dict(common, work_id="HEAVY", wall_clock_cost_ub=8, compute_cost_ub=8, memory_cost_ub=8, complexity_cost_ub=8),
            dict(common, work_id="LEAN", wall_clock_cost_ub=2, compute_cost_ub=2, memory_cost_ub=2, complexity_cost_ub=2),
        ])
        self.assertEqual(out["ranked"][0]["work_id"], "LEAN")

    def test_benchmark_roles_that_reveal_capability_are_allowed(self):
        for role in (
            "CAPABILITY_DEFECT_LOCALIZATION",
            "NEW_CAPABILITY_VALIDATION",
            "CAPABILITY_CLAIM_FALSIFICATION",
            "MILESTONE_CERTIFICATION",
        ):
            with self.subTest(role=role):
                row = s.rank_work([{
                    "work_id": role,
                    "work_type": "BENCHMARK_INSTRUMENTATION",
                    "benchmark_role": role,
                    "expected_capability_gain_lcb": 0,
                    "expected_efficiency_gain_lcb": 0,
                    "expected_reliability_gain_lcb": 1,
                    "reuse_breadth_lcb": 1,
                    "generalization_lcb": 1,
                    "success_probability_lcb": "1",
                    "wall_clock_cost_ub": 1,
                    "compute_cost_ub": 1,
                    "memory_cost_ub": 1,
                    "complexity_cost_ub": 1,
                }])["ranked"][0]
                self.assertEqual(row["eligibility"], "ELIGIBLE")

    def test_verified_reusable_candidate_enters_pareto_frontier(self):
        incumbent = {
            "capability_id": "old",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 5,
            "generalization": 5,
            "reliability": 5,
            "latency": 5,
            "compute": 5,
            "memory": 5,
            "incremental_spend_usd": 0,
        }
        candidate = {
            "capability_id": "new",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 6,
            "generalization": 6,
            "reliability": 6,
            "latency": 4,
            "compute": 4,
            "memory": 4,
            "incremental_spend_usd": 0,
        }
        out = s.update_pareto_frontier([incumbent], candidate)
        self.assertTrue(out["admitted"])
        self.assertEqual([x["capability_id"] for x in out["frontier"]], ["new"])
        self.assertEqual(out["removed_dominated"], ["old"])
        self.assertEqual(out["retired_from_active_frontier"], ["old"])
        self.assertFalse(out["dominated_means_deleted"])
        self.assertFalse(out["physical_deletion_authority"])


    def test_dominated_candidate_is_preserved_not_deleted(self):
        incumbent = {
            "capability_id": "incumbent",
            "semantic_contract_sha256": "sha256:same",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 10,
            "generalization": 10,
            "reliability": 10,
            "latency": 1,
            "compute": 1,
            "memory": 1,
            "incremental_spend_usd": 0,
        }
        candidate = {
            "capability_id": "candidate",
            "semantic_contract_sha256": "sha256:same",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 5,
            "generalization": 5,
            "reliability": 5,
            "latency": 5,
            "compute": 5,
            "memory": 5,
            "incremental_spend_usd": 0,
        }
        out = s.update_pareto_frontier([incumbent], candidate)
        self.assertFalse(out["admitted"])
        self.assertTrue(out["preserve_candidate_evidence"])
        self.assertFalse(out["dominated_means_deleted"])
        self.assertFalse(out["physical_deletion_authority"])

    def test_different_semantic_contracts_do_not_dominate(self):
        incumbent = {
            "capability_id": "a",
            "semantic_contract_sha256": "sha256:a",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 10,
            "generalization": 10,
            "reliability": 10,
            "latency": 1,
            "compute": 1,
            "memory": 1,
            "incremental_spend_usd": 0,
        }
        candidate = {
            "capability_id": "b",
            "semantic_contract_sha256": "sha256:b",
            "reusable_capability": True,
            "independently_verified": True,
            "capability": 1,
            "generalization": 1,
            "reliability": 1,
            "latency": 100,
            "compute": 100,
            "memory": 100,
            "incremental_spend_usd": 0,
        }
        out = s.update_pareto_frontier([incumbent], candidate)
        self.assertTrue(out["admitted"])
        self.assertEqual(
            [x["capability_id"] for x in out["frontier"]],
            ["a", "b"],
        )

    def test_benchmark_result_cannot_be_promoted_as_capability(self):
        out = s.update_pareto_frontier([], {
            "capability_id": "benchmark-score",
            "reusable_capability": False,
            "independently_verified": True,
            "capability": 10,
            "generalization": 10,
            "reliability": 10,
            "latency": 1,
            "compute": 1,
            "memory": 1,
            "incremental_spend_usd": 0,
        })
        self.assertFalse(out["admitted"])
        self.assertEqual(out["reason"], "REUSABLE_CAPABILITY_REQUIRED")

    def test_capability_learning_loop_is_canonical(self):
        self.assertEqual(
            s.CAPABILITY_LEARNING_LOOP,
            (
                "SOLVE",
                "VERIFY",
                "EXTRACT_MECHANISM",
                "GENERALIZE",
                "COMPRESS",
                "PRESERVE_OPTIONS",
                "REUSE_CHEAPER",
            ),
        )

    def test_governance_activation_and_terminal_pointer_are_bound(self):
        activation = json.loads((ROOT / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261008_V1.json").read_text())
        pointer = json.loads((ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").read_text())
        self.assertEqual(activation["status"], "ACTIVE_PRIMARY_CAPABILITY_DEVELOPMENT_SCHEDULER")
        self.assertEqual(
            activation["terminal_milestone"],
            "OPUS_5_5_FIRST_FRONTIER_CHECKPOINT__NOT_TERMINAL_OBJECTIVE",
        )
        self.assertEqual(
            activation["terminal_objective"],
            "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE",
        )
        self.assertFalse(
            activation["r2_judgment_model_policy"]["external_closed_model_dependency"]
        )
        self.assertEqual(
            activation["option_preservation"]["invariant"],
            "OPTIMIZE_IMPLEMENTATIONS_NOT_POSSIBILITIES",
        )
        self.assertFalse(
            activation["option_preservation"]["physical_deletion_authority_from_scheduler"]
        )
        self.assertEqual(
            pointer["capability_first_scheduler_20261008_v1"]["status"],
            "ACTIVE_PRIMARY_CAPABILITY_DEVELOPMENT_SCHEDULER",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
