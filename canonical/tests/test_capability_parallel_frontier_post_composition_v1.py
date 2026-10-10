import unittest
from copy import deepcopy

from canonical.runtime import capability_parallel_frontier_post_composition_v1 as p
from canonical.runtime import capability_parallel_frontier_v2 as core


class Tests(unittest.TestCase):
    def current_frontier(self):
        return core.load_current_frontier()

    def professional_row(self, frontier):
        return p._professional_row(frontier)

    def test_current(self):
        frontier = self.current_frontier()
        row = self.professional_row(frontier)
        out = p.plan_current_post_composition_frontier()
        self.assertEqual(out["parallel_full_execution_work_ids"], [])
        self.assertIn(
            row["work_id"],
            out["parallel_read_only_evidence_work_ids"],
        )
        self.assertEqual(
            out["professional_phase_identity"],
            "SOURCE_BOUND_PROPERTY_TRUTH_FRONTIER",
        )
        self.assertFalse(out["execution_authority"])

    def test_requires_current_property_truth_count(self):
        frontier = deepcopy(self.current_frontier())
        row = self.professional_row(frontier)
        row["read_only_evidence"]["property_truth_closed_count"] += 1
        with self.assertRaisesRegex(
            p.PostCompositionFrontierError,
            "PROFESSIONAL_PROPERTY_TRUTH_COUNT_STALE",
        ):
            p._assert_post_composition(frontier)

    def test_requires_current_professional_source_binding(self):
        frontier = deepcopy(self.current_frontier())
        row = self.professional_row(frontier)
        row["read_only_evidence"]["source_git_blob_sha"] = "0" * 40
        with self.assertRaisesRegex(
            p.PostCompositionFrontierError,
            "PROFESSIONAL_CANDIDATE_SOURCE_STALE",
        ):
            p._assert_post_composition(frontier)

    def test_requires_read_only_professional_lane(self):
        frontier = deepcopy(self.current_frontier())
        row = self.professional_row(frontier)
        row["evidence_acquisition_mode"] = "FULL_EXECUTION"
        with self.assertRaisesRegex(
            p.PostCompositionFrontierError,
            "PROFESSIONAL_POST_COMPOSITION_NOT_READ_ONLY",
        ):
            p._assert_post_composition(frontier)

    def test_professional_phase_identity_is_not_work_id_hardcoded(self):
        frontier = deepcopy(self.current_frontier())
        row = self.professional_row(frontier)
        row["work_id"] = "PROFESSIONAL_QUALITY_V7_FUTURE_PHASE"
        p._assert_post_composition(frontier)

    def test_requires_single_professional_lane(self):
        frontier = deepcopy(self.current_frontier())
        frontier["candidates"] = [
            row
            for row in frontier["candidates"]
            if not (
                row.get("source") == p.PROFESSIONAL_SOURCE_REL
                and p.PROFESSIONAL_MUTATION_KEY
                in (row.get("mutation_keys") or [])
            )
        ]
        with self.assertRaisesRegex(
            p.PostCompositionFrontierError,
            "POST_COMPOSITION_PROFESSIONAL_CANDIDATE_CARDINALITY",
        ):
            p._assert_post_composition(frontier)


if __name__ == "__main__":
    unittest.main()
