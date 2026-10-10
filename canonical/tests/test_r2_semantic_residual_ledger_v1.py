from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime import capability_first_scheduler_v1 as scheduler
from canonical.runtime import r2_semantic_residual_ledger_v1 as ledger


ROOT = Path(__file__).resolve().parents[2]


def _authority(boundary: str) -> dict:
    return {
        "schema": "PROJECT_BRAIN_CURRENT_R2_DECISION_INTELLIGENCE_POINTER_V1",
        "status": "ACTIVE_CURRENT_R2_AUTHORITY__GENERAL_MECHANISM_CLOSED",
        "general_mechanism_missing": False,
        "current_cell_classifications": {
            "FINANCE_SEMANTIC_ADEQUACY_TAIL": {
                "state": "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
                "remaining_boundary": boundary,
                "wake_on": ["NEW_AUTHENTIC_POLICY_CHANGING_SOURCE_OR_CONTEXT_FACT"],
                "required_action": "ACQUIRE_ONLY_MINIMUM_POLICY_CHANGING_EVIDENCE",
            }
        },
    }


def _work(work_id: str, cause_id: str, **overrides) -> dict:
    row = {
        "work_id": work_id,
        "work_type": "CAPABILITY_BUILD",
        "expected_capability_gain_lcb": 10,
        "expected_efficiency_gain_lcb": 10,
        "expected_reliability_gain_lcb": 10,
        "reuse_breadth_lcb": 10,
        "generalization_lcb": 10,
        "success_probability_lcb": "1",
        "wall_clock_cost_ub": 1,
        "compute_cost_ub": 1,
        "memory_cost_ub": 1,
        "complexity_cost_ub": 1,
        "shared_residual_cause_ids": [cause_id],
    }
    row.update(overrides)
    return row


class R2SharedCauseResidualLedgerV1Tests(unittest.TestCase):
    def test_synthetic_residuals_group_into_shared_causes(self):
        out = ledger.build_ledger(
            _authority(
                "FINANCE_COREFERENCE_CASES_WITH_MISSING_TERMINAL_SIGNATURES"
                "__NONEXPLICIT_SEMANTIC_RELATIONS_WITHOUT_VERIFIER_BACKED_DOMAIN_MAPPING"
                "__CROSS_DOCUMENT_CASES_WITH_REQUIRED_EFFECT_FIELD_REMAINING_AT_SEMANTIC_TOP"
            )
        )
        self.assertTrue(out["classification_complete"], out)
        self.assertEqual(len(out["clauses"]), 3)
        parents = {row["cause_id"]: row for row in out["shared_causes"]}
        self.assertEqual(
            parents["SEMANTIC_SCOPE_AUTHORITY"]["fanout_clause_count"],
            2,
        )
        self.assertEqual(
            parents["DOCUMENT_EFFECT_AUTHORITY"]["fanout_clause_count"],
            1,
        )
        self.assertEqual(
            out["highest_fanout_shared_cause"],
            "SEMANTIC_SCOPE_AUTHORITY",
        )
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["credit_delta"], 0)

    def test_unclassified_clause_is_visible_and_fanout_index_fails_closed(self):
        out = ledger.build_ledger(_authority("TOTALLY_NEW_RESIDUAL_KIND"))
        self.assertFalse(out["classification_complete"])
        self.assertEqual(out["unclassified_clauses"], ["TOTALLY_NEW_RESIDUAL_KIND"])
        with self.assertRaises(ledger.R2SemanticResidualLedgerError):
            ledger.cause_fanout_index(out)

    def test_live_current_authority_is_fully_classified(self):
        out = ledger.load_current_ledger()
        self.assertTrue(out["general_mechanism_closed"])
        self.assertTrue(out["classification_complete"], out["unclassified_clauses"])
        cause_ids = {row["cause_id"] for row in out["fine_causes"]}
        for expected in (
            "MENTION_UNIVERSE_COMPLETENESS",
            "TERMINAL_SIGNATURE_COVERAGE",
            "WORD_SENSE_BINDING",
            "SCOPED_DOMAIN_MAPPING_AUTHORITY",
            "SEMANTIC_RELATION_PROOF",
            "OPEN_WORLD_ONTOLOGY_AUTHORITY",
            "CROSS_DOCUMENT_EFFECT_PROOF",
            "EXTERNAL_FACT_AUTHENTICATION",
            "CROSS_FILING_SEMANTIC_STABILITY",
            "IDENTITY_DISCRIMINATION",
        ):
            self.assertIn(expected, cause_ids)
        self.assertEqual(
            out["highest_fanout_shared_cause"],
            "SEMANTIC_SCOPE_AUTHORITY",
        )
        self.assertGreater(out["highest_fanout_clause_count"], 1)

    def test_scheduler_prefers_higher_fanout_only_after_primary_score_ties(self):
        live = ledger.load_current_ledger()
        shared = sorted(
            live["shared_causes"],
            key=lambda row: (row["fanout_clause_count"], row["cause_id"]),
        )
        low = shared[0]
        high = shared[-1]
        self.assertGreater(
            high["fanout_clause_count"],
            low["fanout_clause_count"],
        )
        out = scheduler.rank_work(
            [
                _work("LOW_FANOUT", low["cause_id"]),
                _work("HIGH_FANOUT", high["cause_id"]),
            ],
            checkpoint_open_obligation_count=0,
        )
        self.assertEqual(out["ranked"][0]["work_id"], "HIGH_FANOUT")
        self.assertEqual(
            out["ranked"][0]["priority_score"],
            out["ranked"][1]["priority_score"],
        )
        self.assertGreater(
            int(out["ranked"][0]["shared_residual_fanout_score"]),
            int(out["ranked"][1]["shared_residual_fanout_score"]),
        )

    def test_stronger_capability_score_still_beats_higher_residual_fanout(self):
        live = ledger.load_current_ledger()
        shared = sorted(
            live["shared_causes"],
            key=lambda row: (row["fanout_clause_count"], row["cause_id"]),
        )
        low = shared[0]["cause_id"]
        high = shared[-1]["cause_id"]
        stronger = _work(
            "STRONGER_CAPABILITY",
            low,
            expected_capability_gain_lcb=100,
            expected_efficiency_gain_lcb=100,
            expected_reliability_gain_lcb=100,
        )
        weaker = _work("HIGHER_FANOUT", high)
        out = scheduler.rank_work(
            [weaker, stronger],
            checkpoint_open_obligation_count=0,
        )
        self.assertEqual(out["ranked"][0]["work_id"], "STRONGER_CAPABILITY")

    def test_open_world_residual_does_not_wake_from_fanout_alone(self):
        high = ledger.load_current_ledger()["highest_fanout_shared_cause"]
        row = _work(
            "GLOBAL_OPEN_WORLD_HUNT",
            high,
            frontier_class=scheduler.OPEN_WORLD_EVIDENCE_FRONTIER,
        )
        out = scheduler.rank_work([row], checkpoint_open_obligation_count=0)
        ranked = out["ranked"][0]
        self.assertEqual(
            ranked["eligibility"],
            "DEMOTED_OPEN_WORLD_EVIDENCE_FRONTIER_WITHOUT_CURRENT_CAPABILITY_DEFECT",
        )
        self.assertEqual(ranked["priority_score"], "0")
        self.assertEqual(ranked["shared_residual_fanout_score"], "0")

    def test_unknown_residual_cause_fails_closed(self):
        with self.assertRaisesRegex(
            scheduler.CapabilityFirstSchedulerError,
            "UNKNOWN_SHARED_RESIDUAL_CAUSE",
        ):
            scheduler.rank_work(
                [_work("STALE", "CAUSE_THAT_DOES_NOT_EXIST")],
                checkpoint_open_obligation_count=0,
            )

    def test_governance_pointer_binds_live_derived_ledger(self):
        pointer = json.loads(
            (
                ROOT
                / "canonical/governance/CURRENT_R2_SHARED_CAUSE_RESIDUAL_LEDGER.json"
            ).read_text()
        )
        activation = json.loads(
            (
                ROOT
                / "canonical/governance/R2_SHARED_CAUSE_RESIDUAL_LEDGER_ACTIVATION_20261010_V1.json"
            ).read_text()
        )
        self.assertEqual(
            pointer["runtime"],
            "canonical/runtime/r2_semantic_residual_ledger_v1.py",
        )
        self.assertEqual(
            pointer["source_authority"],
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        )
        self.assertEqual(
            activation["scheduler_binding"]["rule"],
            "PRIMARY_CAPABILITY_RESOURCE_SCORE_FIRST__SHARED_CAUSE_FANOUT_SECONDARY_TIE_BREAK__OPUS_CHECKPOINT_AUDIT_TERTIARY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
