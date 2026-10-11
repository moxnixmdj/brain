from __future__ import annotations

import unittest

from canonical.runtime.benchmark_capability_dominance_scheduler_v2 import plan


def frontier(state="RUNNABLE"):
    return {
        "benchmark_rows": [
            {
                "id": "BENCH_A",
                "scheduler_state": state,
                "capability_projection": {
                    "relation": "SCHEDULING_HEURISTIC_ONLY",
                    "families": ["F1", "F2"],
                },
            }
        ]
    }


def candidate(cid, edges=None, **kw):
    out = {
        "id": cid,
        "type": "CAPABILITY",
        "external_runtime_cognition": 0,
        "incremental_spend_usd": 0,
        "waits_for_external_event": False,
        "proved_live_defect": True,
        "verified_counterexample": False,
        "authorized_discriminating_experiment": False,
        "reusable_family_count": 0,
        "projected_benchmark_row_count": 0,
        "wall_clock_rank": 10,
        "new_reality_units": 0,
        "clean_case_spend": 0,
        "evidence_cost": 0.0,
        "proposition_edges": edges or [],
    }
    out.update(kw)
    return out


def edge(pid, ptype="CAPABILITY_RELATION", relation="CONSERVATIVE_DOMINANCE", **kw):
    out = {
        "proposition_id": pid,
        "proposition_type": ptype,
        "relation": relation,
        "entailment_proved": True,
        "scope_bound": True,
        "evidence_ref": "canonical/evidence.json",
    }
    out.update(kw)
    return out


class BenchmarkCapabilityDominanceSchedulerV2Tests(unittest.TestCase):
    def test_proved_closure_beats_large_heuristic_projection(self):
        a = candidate(
            "HEURISTIC_BIG",
            reusable_family_count=99,
            projected_benchmark_row_count=99,
        )
        b = candidate("PROVED", [edge("P1")], wall_clock_rank=100)
        out = plan(frontier(), [a, b], required_propositions=["P1"])
        self.assertEqual(out["selected"]["id"], "PROVED")
        self.assertEqual(out["selection_mode"], "EXACT_MINIMUM_PROOF_COVER")

    def test_exact_statistic_rejects_capability_relation(self):
        bad = candidate(
            "BAD",
            [
                edge(
                    "B1",
                    ptype="EXACT_BENCHMARK_STATISTIC",
                    relation="CONSERVATIVE_DOMINANCE",
                )
            ],
        )
        out = plan(frontier(), [bad], required_propositions=["B1"])
        self.assertIsNone(out["selected"])
        self.assertIn(
            "EXACT_STATISTIC_RELATION_INVALID:B1",
            out["admitted"][0]["proposition_edge_errors"],
        )

    def test_exact_statistic_bridge_requires_frozen_scorer(self):
        bad = candidate(
            "BAD",
            [
                edge(
                    "B1",
                    ptype="EXACT_BENCHMARK_STATISTIC",
                    relation="EXACT_STATISTIC_BRIDGE",
                    frozen_scorer_state_bound=False,
                )
            ],
        )
        out = plan(frontier(), [bad], required_propositions=["B1"])
        self.assertIsNone(out["selected"])
        self.assertIn(
            "EXACT_STATISTIC_SCORER_UNBOUND:B1",
            out["admitted"][0]["proposition_edge_errors"],
        )

    def test_minimum_cover_prefers_one_multi_proposition_route(self):
        both = candidate("BOTH", [edge("P1"), edge("P2")], wall_clock_rank=50)
        p1 = candidate("P1_ONLY", [edge("P1")], wall_clock_rank=1)
        p2 = candidate("P2_ONLY", [edge("P2")], wall_clock_rank=1)
        out = plan(frontier(), [p1, p2, both], required_propositions=["P1", "P2"])
        self.assertEqual(out["proof_cover"]["selected_route_ids"], ["BOTH"])
        self.assertEqual(out["selected"]["id"], "BOTH")

    def test_incomplete_cover_selects_max_verified_marginal_closure(self):
        two = candidate("TWO", [edge("P1"), edge("P2")], wall_clock_rank=50)
        one = candidate("ONE", [edge("P1")], wall_clock_rank=1)
        out = plan(
            frontier(),
            [one, two],
            required_propositions=["P1", "P2", "P3"],
        )
        self.assertEqual(out["proof_cover"]["status"], "INCOMPLETE_COVER")
        self.assertEqual(out["selection_mode"], "MAX_VERIFIED_MARGINAL_CLOSURE")
        self.assertEqual(out["selected"]["id"], "TWO")

    def test_ownership_edge_requires_brain_owned_configuration(self):
        bad = candidate(
            "BAD",
            [
                edge(
                    "O1",
                    ptype="OWNERSHIP_PREDICATE",
                    relation="BRAIN_OWNERSHIP_CERTIFICATE",
                )
            ],
            brain_owned_operative_configuration=False,
        )
        out = plan(frontier(), [bad], required_propositions=["O1"])
        self.assertIsNone(out["selected"])
        self.assertIn(
            "OWNERSHIP_CONFIGURATION_UNBOUND:O1",
            out["admitted"][0]["proposition_edge_errors"],
        )

    def test_wake_gated_benchmark_specific_candidate_stays_rejected(self):
        bench = {
            "id": "BENCH",
            "type": "BENCHMARK_SPECIFIC",
            "benchmark_row_id": "BENCH_A",
            "external_runtime_cognition": 0,
            "incremental_spend_usd": 0,
            "waits_for_external_event": False,
            "new_policy_changing_evidence": True,
            "proposition_edges": [edge("P1")],
        }
        out = plan(frontier("WAKE_GATED"), [bench], required_propositions=["P1"])
        self.assertIsNone(out["selected"])
        self.assertEqual(out["rejected"][0]["reason"], "BENCHMARK_ROW_NOT_RUNNABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
