from __future__ import annotations

import json
from hashlib import sha1
import unittest
from pathlib import Path

from canonical.runtime import capability_first_scheduler_v1 as s


ROOT = Path(__file__).resolve().parents[2]

def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def capability_row(work_id: str, **overrides):
    row = {
        "work_id": work_id,
        "work_type": "CAPABILITY_BUILD",
        "expected_capability_gain_lcb": 6,
        "expected_efficiency_gain_lcb": 5,
        "expected_reliability_gain_lcb": 4,
        "reuse_breadth_lcb": 8,
        "generalization_lcb": 7,
        "success_probability_lcb": "4/5",
        "wall_clock_cost_ub": 2,
        "compute_cost_ub": 2,
        "memory_cost_ub": 1,
        "complexity_cost_ub": 1,
    }
    row.update(overrides)
    return row


class CapabilityFirstSchedulerV1Tests(unittest.TestCase):
    def rank_general(self, rows):
        return s.rank_work(rows, checkpoint_open_obligation_count=0)

    def test_benchmark_bookkeeping_is_hard_demoted(self):
        out = self.rank_general([{
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
        }])
        row = out["ranked"][0]
        self.assertEqual(row["eligibility"], "DEMOTED_BENCHMARK_BOOKKEEPING")
        self.assertEqual(row["priority_score"], "0")
        self.assertEqual(row["checkpoint_audit_score"], "0")

    def test_capability_build_beats_checkpoint_certification(self):
        out = self.rank_general([
            capability_row("GENERALIZE_RELEVANCE_CEGAR"),
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

    def test_open_checkpoint_does_not_demote_generic_capability_work(self):
        out = s.rank_work(
            [
                capability_row(
                    "GENERAL_LIVE_BRAIN_IMPROVEMENT",
                    expected_capability_gain_lcb=20,
                    expected_efficiency_gain_lcb=20,
                    expected_reliability_gain_lcb=20,
                ),
                {
                    "work_id": "CHECKPOINT_ONLY",
                    "work_type": "BENCHMARK_INSTRUMENTATION",
                    "benchmark_role": "MILESTONE_CERTIFICATION",
                    "scheduling_lane": "LOAD_BEARING_PRIMARY",
                    "open_obligation_ids": ["OPEN_A"],
                    "expected_obligation_discharge_lcb": 10,
                    "expected_obligation_unlock_lcb": 0,
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
                },
            ],
            checkpoint_open_obligation_count=13,
        )
        self.assertEqual(out["ranked"][0]["work_id"], "GENERAL_LIVE_BRAIN_IMPROVEMENT")
        self.assertEqual(out["ranked"][0]["eligibility"], "ELIGIBLE")
        self.assertFalse(out["load_bearing_primary_gate_active"])
        self.assertTrue(out["checkpoint_audit_active"])

    def test_checkpoint_audit_score_only_breaks_capability_ties(self):
        common = capability_row("placeholder")
        a = dict(common, work_id="GENERAL_A")
        b = dict(
            common,
            work_id="CHECKPOINT_B",
            scheduling_lane="LOAD_BEARING_PRIMARY",
            open_obligation_ids=["OPEN_A"],
            expected_obligation_discharge_lcb=1,
            expected_obligation_unlock_lcb=0,
        )
        out = s.rank_work([a, b], checkpoint_open_obligation_count=13)
        self.assertEqual(out["ranked"][0]["work_id"], "CHECKPOINT_B")
        self.assertEqual(out["ranked"][0]["priority_score"], out["ranked"][1]["priority_score"])
        self.assertNotEqual(out["ranked"][0]["checkpoint_audit_score"], "0")
        self.assertEqual(out["ranked"][1]["checkpoint_audit_score"], "0")

    def test_low_capability_checkpoint_work_cannot_beat_stronger_capability_work(self):
        strong = capability_row(
            "STRONG_GENERAL",
            expected_capability_gain_lcb=100,
            expected_efficiency_gain_lcb=100,
            expected_reliability_gain_lcb=100,
        )
        checkpoint = capability_row(
            "WEAK_CHECKPOINT",
            expected_capability_gain_lcb=1,
            expected_efficiency_gain_lcb=0,
            expected_reliability_gain_lcb=0,
            scheduling_lane="LOAD_BEARING_PRIMARY",
            open_obligation_ids=["OPEN_A"],
            expected_obligation_discharge_lcb=1000,
            expected_obligation_unlock_lcb=1000,
            wall_clock_cost_ub=1,
        )
        out = s.rank_work([checkpoint, strong], checkpoint_open_obligation_count=13)
        self.assertEqual(out["ranked"][0]["work_id"], "STRONG_GENERAL")

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
        out = self.rank_general([
            dict(common, work_id="HEAVY", wall_clock_cost_ub=8, compute_cost_ub=8, memory_cost_ub=8, complexity_cost_ub=8),
            dict(common, work_id="LEAN", wall_clock_cost_ub=2, compute_cost_ub=2, memory_cost_ub=2, complexity_cost_ub=2),
        ])
        self.assertEqual(out["ranked"][0]["work_id"], "LEAN")

    def test_allowed_benchmark_roles_remain_instrumentation_eligible(self):
        for role in (
            "CAPABILITY_DEFECT_LOCALIZATION",
            "NEW_CAPABILITY_VALIDATION",
            "CAPABILITY_CLAIM_FALSIFICATION",
            "MILESTONE_CERTIFICATION",
        ):
            with self.subTest(role=role):
                row = self.rank_general([{
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

    def test_live_entrypoint_uses_checkpoint_as_audit_not_gate(self):
        out = s.rank_live_work([capability_row("LIVE_GENERAL_CAPABILITY")])
        self.assertGreater(out["checkpoint_open_obligation_count"], 0)
        self.assertFalse(out["load_bearing_primary_gate_active"])
        self.assertTrue(out["checkpoint_audit_active"])
        self.assertEqual(out["ranked"][0]["eligibility"], "ELIGIBLE")
        self.assertEqual(out["ranked"][0]["work_id"], "LIVE_GENERAL_CAPABILITY")

    def test_unbound_open_world_frontier_is_demoted_even_with_large_claimed_gain(self):
        frontier = capability_row(
            "GLOBAL_FINANCE_SEMANTIC_COMPLETION",
            frontier_class=s.OPEN_WORLD_EVIDENCE_FRONTIER,
            expected_capability_gain_lcb=1000000,
            expected_efficiency_gain_lcb=1000000,
            expected_reliability_gain_lcb=1000000,
            reuse_breadth_lcb=1000000,
            generalization_lcb=1000000,
            success_probability_lcb="1",
            wall_clock_cost_ub=1,
            compute_cost_ub=1,
            memory_cost_ub=1,
            complexity_cost_ub=1,
        )
        useful = capability_row("CONCRETE_GENERAL_CAPABILITY")
        out = self.rank_general([frontier, useful])
        self.assertEqual(out["ranked"][0]["work_id"], "CONCRETE_GENERAL_CAPABILITY")
        self.assertEqual(
            out["ranked"][1]["eligibility"],
            "DEMOTED_OPEN_WORLD_EVIDENCE_FRONTIER_WITHOUT_CURRENT_CAPABILITY_DEFECT",
        )
        self.assertEqual(out["ranked"][1]["priority_score"], "0")

    def test_open_world_frontier_wakes_on_task_local_counterexample(self):
        row = capability_row(
            "FINANCE_SEMANTIC_COUNTEREXAMPLE_REPAIR",
            frontier_class=s.OPEN_WORLD_EVIDENCE_FRONTIER,
            task_local_counterexample_ids=["task-case-1"],
        )
        out = self.rank_general([row])
        self.assertEqual(out["ranked"][0]["eligibility"], "ELIGIBLE")
        self.assertEqual(
            out["ranked"][0]["task_local_counterexample_ids"],
            ["task-case-1"],
        )
        self.assertNotEqual(out["ranked"][0]["priority_score"], "0")

    def test_open_world_frontier_wakes_on_verified_capability_defect(self):
        row = capability_row(
            "GENERAL_SEMANTIC_DEFECT_REPAIR",
            frontier_class=s.OPEN_WORLD_EVIDENCE_FRONTIER,
            verified_capability_defect_ids=["verified-defect-1"],
        )
        out = self.rank_general([row])
        self.assertEqual(out["ranked"][0]["eligibility"], "ELIGIBLE")
        self.assertEqual(
            out["ranked"][0]["verified_capability_defect_ids"],
            ["verified-defect-1"],
        )

    def test_r2_mechanism_policy_binds_mutable_current_r2_by_path_and_rechecks_invariants(self):
        pointer = json.loads(
            (ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json").read_text()
        )
        policy_rel = pointer["r2_mechanism_policy"]["path"]
        self.assertEqual(
            policy_rel,
            "canonical/governance/R2_MECHANISM_CLOSURE_OPEN_WORLD_FRONTIER_POLICY_20261010_V4.json",
        )
        policy = json.loads((ROOT / policy_rel).read_text())

        current = policy["sources"]["current_r2"]
        self.assertEqual(
            current["path"],
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        )
        self.assertEqual(
            current["binding"],
            "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__LIVE_INVARIANTS_RECHECKED",
        )
        self.assertFalse(current["activation_observed_blob_is_load_bearing"])
        self.assertNotIn("git_blob_sha", current)

        drifted = []
        for source_id, row in policy["sources"].items():
            source = ROOT / row["path"]
            self.assertTrue(source.is_file(), row["path"])
            if source_id == "current_r2":
                continue
            actual = _git_blob_sha(source)
            if actual != row["git_blob_sha"]:
                drifted.append(
                    {
                        "path": row["path"],
                        "policy_git_blob_sha": row["git_blob_sha"],
                        "current_git_blob_sha": actual,
                    }
                )
        self.assertEqual(
            pointer["scalar_fallback_state"],
            "BLOCKED_R2_POLICY_SOURCE_LOCK_DRIFT__PRIMARY_V17_ACTIVE",
        )
        self.assertEqual(
            pointer["r2_mechanism_policy"]["currentness_state"],
            "FAIL_CLOSED_IMMUTABLE_SOURCE_DRIFT",
        )
        self.assertEqual(
            sorted(drifted, key=lambda row: row["path"]),
            sorted(
                pointer["r2_mechanism_policy"]["drifted_sources"],
                key=lambda row: row["path"],
            ),
        )

        r2 = json.loads(
            (ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json").read_text()
        )
        required = policy["required_current_r2_invariants"]
        self.assertIn(required["status_contains"], r2["status"])
        self.assertEqual(
            r2["general_mechanism_missing"],
            required["general_mechanism_missing"],
        )
        self.assertEqual(
            r2["scheduler_result"]["primary_cell"],
            required["primary_internal_cell"],
        )
        finance = r2["current_cell_classifications"][required["primary_internal_cell"]]
        self.assertEqual(
            finance["state"],
            required["primary_internal_cell_state"],
        )
        self.assertEqual(
            r2["scheduler_result"][
                "primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"
            ],
            required["primary_internal_unsolved_count"],
        )
        self.assertEqual(
            finance["information_theoretic_externality_proved"],
            required["information_theoretic_externality_proved"],
        )
        self.assertEqual(
            r2["global_open_world_closure_claimed"],
            required["global_open_world_closure_claimed"],
        )
        self.assertEqual(
            policy["classification"]["finance_global_residual"],
            "OPEN_WORLD_EVIDENCE_FRONTIER__WAKE_GATED__NOT_GLOBAL_MECHANISM_FAILURE_BY_EXISTENCE_ALONE",
        )

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
        self.assertEqual([x["capability_id"] for x in out["frontier"]], ["a", "b"])

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

    def test_v7_scalar_contract_preserved_v9_history_and_v17_is_current_primary(self):
        v7 = json.loads(
            (
                ROOT
                / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V7.json"
            ).read_text()
        )
        v9 = json.loads(
            (
                ROOT
                / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V9.json"
            ).read_text()
        )
        v17 = json.loads(
            (
                ROOT
                / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261011_V17.json"
            ).read_text()
        )
        pointer = json.loads(
            (ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json").read_text()
        )
        mission = json.loads(
            (ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text()
        )
        self.assertEqual(
            v7["status"],
            "ACTIVE_PRIMARY_CAPABILITY_FIRST_DEVELOPMENT_SCHEDULER__REUSE_FIRST_ENFORCED__LIVE_SCORE_PROVENANCE_GATE_ADDED__BASE_C6826060__ZERO_CREDIT",
        )
        self.assertFalse(v7["primary_work_rule"]["checkpoint_obligations_are_primary_gate"])
        self.assertFalse(
            v7["primary_work_rule"][
                "generic_reusable_capability_work_is_demoted_while_checkpoint_open"
            ]
        )
        self.assertEqual(
            v7["reuse_first_residual_admission"]["scheduler_runtime_enforcement"],
            "MECHANICALLY_IMPLEMENTED__CLAIMS_NEW_PRIMITIVE_TRUE_REQUIRES_ALL_SIX_PROOF_OBLIGATIONS__ELSE_DEMOTED_UNPROVED_NEW_PRIMITIVE_CLAIM",
        )
        self.assertEqual(
            pointer["authoritative_activation"],
            "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261011_V17.json",
        )
        self.assertEqual(
            mission["current_development_scheduler"]["activation"],
            "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261011_V17.json",
        )
        self.assertEqual(
            v17["decision_value_authority"]["rule"],
            "ROWS_WHOSE_CURRENT_MODE_IS_WAKE_GATED_EVENT_DRIVEN_OR_PARKED_MUST_NOT_CONSUME_SAME_INFORMATION_WORK__ONLY_CURRENT_NONWAKE_ROWS_ENTER_GAP_A_EVIDENCE_SCHEDULING",
        )
        self.assertEqual(
            v17["current_projection"]["gap_a_actionable_row_ids"],
            [],
        )
        self.assertEqual(
            pointer["scalar_fallback_runtime"],
            "canonical/runtime/capability_first_live_scheduler_v1.py",
        )
        self.assertEqual(
            v9["primary_parallel_frontier"]["primary_entrypoint"],
            "plan_current_parallel_frontier",
        )
        self.assertIn(
            "EXPLICIT_NEW_PRIMITIVE_CLAIMS_REQUIRE_REUSE_FIRST_EXHAUSTION_PROOF",
            mission["scheduler_precedence"],
        )


    def test_unproved_new_primitive_claim_is_demoted(self):
        row = capability_row(
            "UNPROVED_NEW_PRIMITIVE",
            claims_new_primitive=True,
        )
        out = self.rank_general([row])
        ranked = out["ranked"][0]
        self.assertEqual(
            ranked["eligibility"],
            "DEMOTED_UNPROVED_NEW_PRIMITIVE_CLAIM",
        )
        self.assertTrue(ranked["claims_new_primitive"])
        self.assertFalse(ranked["new_primitive_proof_complete"])
        self.assertEqual(ranked["priority_score"], "0")
        self.assertEqual(
            set(ranked["new_primitive_missing_requirements"]),
            {
                "EXACT_UNSATISFIED_PREDICATE",
                "EXISTING_MECHANISMS_SEARCHED",
                "WHY_EACH_EXISTING_MECHANISM_CANNOT_SOUNDLY_CLOSE_THE_PREDICATE",
                "INDEPENDENTLY_VERIFIED_MISSING_PRIMITIVE_OR_COUNTEREXAMPLE",
                "MINIMUM_NEW_PRIMITIVE_SCOPE",
                "FALSIFIER_AND_PROMOTION_CRITERIA",
            },
        )

    def test_complete_new_primitive_exhaustion_proof_is_eligible(self):
        row = capability_row(
            "PROVED_NEW_PRIMITIVE",
            claims_new_primitive=True,
            exact_unsatisfied_predicate="P",
            existing_mechanisms_searched=["A", "B"],
            existing_mechanism_unsoundness_reasons={
                "A": "counterexample-a",
                "B": "counterexample-b",
            },
            independently_verified_missing_primitive_or_counterexample="receipt-1",
            minimum_new_primitive_scope="P-only",
            falsifier_and_promotion_criteria="fresh replay plus independent verifier",
        )
        out = self.rank_general([row])
        ranked = out["ranked"][0]
        self.assertEqual(ranked["eligibility"], "ELIGIBLE")
        self.assertTrue(ranked["claims_new_primitive"])
        self.assertTrue(ranked["new_primitive_proof_complete"])
        self.assertEqual(ranked["new_primitive_missing_requirements"], [])
        self.assertNotEqual(ranked["priority_score"], "0")

    def test_partial_mechanism_exhaustion_does_not_admit_new_primitive(self):
        row = capability_row(
            "PARTIAL_NEW_PRIMITIVE",
            claims_new_primitive=True,
            exact_unsatisfied_predicate="P",
            existing_mechanisms_searched=["A", "B"],
            existing_mechanism_unsoundness_reasons={"A": "counterexample-a"},
            independently_verified_missing_primitive_or_counterexample="receipt-1",
            minimum_new_primitive_scope="P-only",
            falsifier_and_promotion_criteria="fresh replay",
        )
        out = self.rank_general([row])
        ranked = out["ranked"][0]
        self.assertEqual(
            ranked["eligibility"],
            "DEMOTED_UNPROVED_NEW_PRIMITIVE_CLAIM",
        )
        self.assertIn(
            "WHY_EACH_EXISTING_MECHANISM_CANNOT_SOUNDLY_CLOSE_THE_PREDICATE",
            ranked["new_primitive_missing_requirements"],
        )

    def test_ordinary_capability_build_remains_eligible_without_novelty_proof(self):
        row = capability_row("REUSE_OR_ADAPT_EXISTING")
        out = self.rank_general([row])
        ranked = out["ranked"][0]
        self.assertEqual(ranked["eligibility"], "ELIGIBLE")
        self.assertFalse(ranked["claims_new_primitive"])
        self.assertTrue(ranked["new_primitive_proof_complete"])
        self.assertEqual(ranked["new_primitive_missing_requirements"], [])

    def test_reuse_first_policy_remains_load_bearing_through_v9(self):
        pointer = json.loads(
            (ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json").read_text()
        )
        activation = json.loads(
            (
                ROOT
                / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V7.json"
            ).read_text()
        )
        reuse = pointer["reuse_first_policy"]
        self.assertEqual(
            reuse["path"],
            "canonical/governance/REUSE_FIRST_RESIDUAL_EXECUTION_POLICY_20261010_V1.json",
        )
        self.assertEqual(
            reuse["status"],
            "ACTIVE_LOAD_BEARING_MECHANICALLY_ENFORCED_THROUGH_CAPABILITY_FIRST_SCHEDULER_V9",
        )
        self.assertIn("MECHANICALLY_IMPLEMENTED", activation["reuse_first_residual_admission"]["scheduler_runtime_enforcement"])
        self.assertEqual(
            activation["primary_work_rule"][
                "new_primitive_claim_without_reuse_exhaustion_proof"
            ],
            "DEMOTED_UNPROVED_NEW_PRIMITIVE_CLAIM",
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
