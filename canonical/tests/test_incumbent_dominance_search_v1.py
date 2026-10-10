import unittest
from canonical.runtime import incumbent_dominance_search_v1 as m


def c(cid, cap=5, gen=5, rel=5, lat=5, comp=5, mem=5, spend=0, contract="abc"):
    return dict(
        candidate_id=cid,
        semantic_contract_sha256=contract,
        independently_verified=True,
        capability=cap,
        generalization=gen,
        reliability=rel,
        latency=lat,
        compute=comp,
        memory=mem,
        incremental_spend_usd=spend,
    )


class TestIncumbentDominanceSearchV1(unittest.TestCase):
    def test_first_solution_never_implies_optimal(self):
        out = m.evaluate(incumbent=c("A"))
        self.assertEqual(out["status"], "OPEN__MATERIALLY_BETTER_CANDIDATE_NOT_EXCLUDED")
        self.assertFalse(out["search_may_stop"])
        self.assertTrue(out["family_coverage_challenge_required"])

    def test_known_dominator_replaces_incumbent(self):
        out = m.evaluate(incumbent=c("A"), candidates=[c("B", cap=6)])
        self.assertEqual(out["status"], "REPLACE_INCUMBENT_AND_REPEAT")
        self.assertEqual(out["next_incumbent_candidate_id"], "B")
        self.assertTrue(out["must_repeat_search_after_replacement"])

    def test_tradeoff_not_miscalled_dominance(self):
        out = m.evaluate(incumbent=c("A"), candidates=[c("B", cap=6, lat=9)])
        self.assertEqual(out["status"], "OPEN__MATERIALLY_BETTER_CANDIDATE_NOT_EXCLUDED")

    def test_different_contract_not_dominator(self):
        out = m.evaluate(incumbent=c("A"), candidates=[c("B", cap=9, contract="other")])
        self.assertEqual(out["status"], "OPEN__MATERIALLY_BETTER_CANDIDATE_NOT_EXCLUDED")

    def test_complete_cover_and_eliminated_regions_proves_optimality(self):
        out = m.evaluate(
            incumbent=c("A"),
            candidate_regions=[
                {"region_id": "config", "status": "EXHAUSTED"},
                {"region_id": "algorithm", "status": "UPPER_BOUND_ELIMINATED", "independent_bound_proof": True},
            ],
            candidate_family_cover_complete=True,
            family_cover_independently_verified=True,
        )
        self.assertEqual(out["status"], "OPTIMALITY_PROVED__NO_BETTER_REGION_REMAINS")
        self.assertTrue(out["optimality_proved"])

    def test_incomplete_family_cover_blocks_optimality(self):
        out = m.evaluate(incumbent=c("A"), candidate_regions=[{"region_id": "known", "status": "EXHAUSTED"}])
        self.assertFalse(out["optimality_proved"])
        self.assertTrue(out["family_coverage_challenge_required"])

    def test_open_region_blocks_optimality(self):
        out = m.evaluate(
            incumbent=c("A"),
            candidate_regions=[{"region_id": "unknown", "status": "OPEN"}],
            candidate_family_cover_complete=True,
            family_cover_independently_verified=True,
        )
        self.assertIn("unknown", out["unresolved_region_ids"])
        self.assertFalse(out["search_may_stop"])

    def test_sufficiency_can_stop_when_optimality_not_requested(self):
        out = m.evaluate(
            incumbent=c("A"),
            optimality_required=False,
            explicit_sufficiency_contract={"independently_verified": True, "incumbent_satisfies": True},
        )
        self.assertEqual(out["status"], "SUFFICIENT__OPTIMALITY_NOT_REQUIRED")
        self.assertTrue(out["search_may_stop"])
        self.assertFalse(out["optimality_proved"])

    def test_upper_bound_requires_proof(self):
        with self.assertRaises(m.SearchControlError):
            m.evaluate(
                incumbent=c("A"),
                candidate_regions=[{"region_id": "x", "status": "UPPER_BOUND_ELIMINATED"}],
            )

    def test_reported_dominator_requires_verification_loop(self):
        out = m.evaluate(
            incumbent=c("A"),
            candidate_regions=[{"region_id": "new-class", "status": "DOMINATOR_FOUND", "candidate_id": "Z"}],
        )
        self.assertEqual(out["status"], "DOMINATOR_REPORTED__VERIFY_AND_REPEAT")
        self.assertFalse(out["optimality_proved"])


if __name__ == "__main__":
    unittest.main()
