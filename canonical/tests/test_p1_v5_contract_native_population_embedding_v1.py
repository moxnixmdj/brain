from __future__ import annotations

import unittest

from canonical.runtime import p1_v5_contract_native_population_embedding_v1 as emb


class P1V5ContractNativePopulationEmbeddingTests(unittest.TestCase):
    def test_live_frozen_population_is_a_v5_superset_candidate(self):
        out=emb.evaluate()
        self.assertEqual(
            out["status"],
            "PASS__FROZEN_CONTRACT_NATIVE_P1_POPULATION_EMBEDS_IN_V5__THREE_SUPERSET_RELATION_CANDIDATES",
            out,
        )
        self.assertTrue(out["population_superset_proven"])
        self.assertEqual(out["legacy_semantic_shape_count"],30)
        self.assertEqual(out["embedded_domain_shape_count"],180)
        self.assertEqual(out["canonical_domain_count"],6)
        self.assertEqual(len(out["surface_relations"]),3)
        self.assertEqual({r["relation"] for r in out["surface_relations"]},{"SUPERSET"})
        self.assertEqual(
            {r["direct_surface"] for r in out["surface_relations"]},
            set(emb.EXPECTED_SURFACES),
        )
        self.assertEqual(out["candidate_information_relation"],"CANDIDATE_HAS_STRICTLY_LESS_INFORMATION_PROVEN")
        self.assertEqual(out["removed_candidate_visible_field"],"repair_candidates")
        self.assertFalse(out["removed_field_load_bearing"])
        self.assertEqual(out["oracle_relation"],"CANDIDATE_STRONGER_PROVEN")
        self.assertEqual(out["failures"],[])

    def test_claim_ids_are_unique_and_bound_to_exact_three_surfaces(self):
        self.assertEqual(set(emb.CLAIM_IDS),set(emb.EXPECTED_SURFACES))
        self.assertEqual(len(set(emb.CLAIM_IDS.values())),3)

    def test_all_legacy_semantic_shapes_exist(self):
        reps=emb._find_shape_representatives()
        expected={(6+d,c) for d in range(1,6) for c in range(1,(6+d)-2)}
        self.assertEqual(set(reps),expected)
        self.assertEqual(len(expected),30)

    def test_embedding_removes_legacy_answer_bearing_repair_candidates(self):
        reps=emb._find_shape_representatives()
        case=next(iter(reps.values()))
        typed=emb.embed(case,"CODE")
        public=emb.v5_proof.public_task(typed)
        self.assertNotIn("repair_candidates",repr(public))
        self.assertNotIn("_oracle",public)
        self.assertNotIn("_intervention_model",public)

    def test_every_shape_preserves_cause_and_repair_under_all_domains(self):
        for legacy_case in emb._find_shape_representatives().values():
            for domain in emb.v5_proof.DOMAINS:
                typed=emb.embed(legacy_case,domain)
                out=emb.v5_candidate.solve(emb.v5_proof.public_task(typed))
                self.assertTrue(emb.v5_proof.score_case(typed,out)["pass"],(legacy_case["seed"],domain,out))
                bridged=emb._bridge_v5_to_legacy(out)
                self.assertTrue(emb.legacy.score_case(legacy_case,bridged)["pass"],(legacy_case["seed"],domain,bridged))

    def test_no_credit_or_replay(self):
        out=emb.evaluate()
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
