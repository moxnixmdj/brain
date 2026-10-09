from __future__ import annotations

import unittest

from canonical.runtime import assurance_closure_compiler_v1 as uvck
from canonical.runtime import semantic_root_uvck_adapter_v1 as a


def support_all():
    return {
        root: {
            "status": "SUPPORTED",
            "authoritative": True,
            "certificate_id": "cert:" + root,
        }
        for root in a.SEMANTIC_ROOTS
    }


class SemanticRootUvckAdapterV1Tests(unittest.TestCase):
    def test_exact_semantic_root_set(self):
        self.assertEqual(
            a.SEMANTIC_ROOTS,
            (
                "SR1_REALITY_CONTAINMENT",
                "SR2_MISSION_SOUNDNESS",
                "SR3_TERMINAL_CLOSURE",
                "SR4_ASSURANCE_AUTHORITY",
            ),
        )

    def test_supported_roots_close_uvck_proof_but_adapter_grants_no_terminal_authority(self):
        out = a.evaluate(support_all())
        self.assertTrue(out["closure_gates"]["proof_closure"], out)
        self.assertEqual(out["status"], "OPEN__EXECUTION_CLOSURE_REQUIRED")
        self.assertFalse(out["semantic_terminal_authority"])
        self.assertEqual(out["semantic_terminal_credit_delta"], 0)

    def test_open_sr3_is_existing_residual_not_new_primitive(self):
        s = support_all()
        s["SR3_TERMINAL_CLOSURE"] = {"status": "OPEN"}
        out = a.evaluate(s)
        self.assertEqual(out["status"], "OPEN__ASSURANCE_RESIDUAL")
        self.assertFalse(out["new_primitive_required"])
        novelty = a.classify_novelty(out)
        self.assertEqual(
            novelty["classification"],
            "EXISTING_SEMANTIC_ROOT_OR_SR4_ASSURANCE_RESIDUAL",
        )
        self.assertFalse(novelty["new_semantic_root_required"])

    def test_uvck_new_primitive_does_not_mean_new_semantic_root(self):
        graph = {
            "schema": uvck.GRAPH_SCHEMA,
            "root_ids": ["root"],
            "nodes": [
                {
                    "id": "root",
                    "type": "CLAIM",
                    "status": "SUPPORTED",
                    "depends_on": ["x"],
                    "defeated_by": [],
                },
                {"id": "x", "type": "UNSUPPORTED_NEW_KIND", "status": "OPEN"},
            ],
            "execution_closure_proved": False,
            "adversarial_closure_proved": False,
        }
        out = uvck.evaluate(graph)
        self.assertTrue(out["new_primitive_required"], out)
        novelty = a.classify_novelty(out)
        self.assertEqual(
            novelty["classification"],
            "UVCK_REPRESENTATION_EXTENSION_REQUIRED",
        )
        self.assertFalse(novelty["new_semantic_root_required"])

    def test_only_semantic_countermodel_requests_root_theorem_review(self):
        novelty = a.classify_novelty({}, semantic_countermodel=True)
        self.assertEqual(
            novelty["classification"],
            "SEMANTIC_ROOT_THEOREM_REVIEW_REQUIRED",
        )
        self.assertTrue(novelty["new_semantic_root_required"])

    def test_proof_search_failure_is_capability_gap(self):
        novelty = a.classify_novelty({}, proof_search_failure_only=True)
        self.assertEqual(
            novelty["classification"],
            "CAPABILITY_CLOSURE_PROOF_ROUTE_GAP",
        )
        self.assertFalse(novelty["new_semantic_root_required"])

    def test_stale_root_reopens_without_new_architecture(self):
        s = support_all()
        s["SR4_ASSURANCE_AUTHORITY"] = {"status": "STALE"}
        out = a.evaluate(s)
        self.assertEqual(out["status"], "OPEN__ASSURANCE_RESIDUAL")
        self.assertIn("SR4_ASSURANCE_AUTHORITY", out["stale_ids"])
        self.assertFalse(out["new_primitive_required"])

    def test_material_cost_reduction_is_optimization_not_new_root(self):
        novelty = a.classify_novelty({}, material_proof_cost_reduction=True)
        self.assertEqual(
            novelty["classification"],
            "EXISTING_ROOT_OPTIMIZATION_CANDIDATE",
        )
        self.assertFalse(novelty["new_semantic_root_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
