from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import professional_quality_remaining_execution_batch_v1 as batch


class ProfessionalQualityRemainingExecutionBatchV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = batch.ROOT
        cls.docs = {}
        for key in (
            "manifest",
            "catalog",
            "graph",
            "scope_batch_verify",
            "binder_verify",
            "currentgen_verify",
            "order_verify",
            "defeater80_verify",
            "r5_verify",
            "r8_verify",
            "r9_verify",
            "r11_contamination_verify",
        ):
            rel, _ = batch.PINS[key]
            cls.docs[key] = batch._load(root / rel)
        cls.runtime_results = batch.run_root_runtime_checks()
        cls.full = batch.verify()

    def _evaluate(self, *, manifest=None, catalog=None, graph=None, runtime_results=None):
        d = self.docs
        return batch.evaluate_documents(
            manifest if manifest is not None else d["manifest"],
            catalog if catalog is not None else d["catalog"],
            graph if graph is not None else d["graph"],
            d["scope_batch_verify"],
            d["binder_verify"],
            d["currentgen_verify"],
            d["order_verify"],
            d["defeater80_verify"],
            d["r5_verify"],
            d["r8_verify"],
            d["r9_verify"],
            d["r11_contamination_verify"],
            runtime_results=(
                runtime_results
                if runtime_results is not None
                else self.runtime_results
            ),
            recompute_scope=False,
        )

    def test_exact_current_batch_closes_four_execution_leaves_only(self):
        out = self.full
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["closed_execution_leaf_count"], 4)
        self.assertEqual(
            set(out["closed_execution_leaf_ids"]),
            {
                "PQ::R5_EVALUATOR_REFERENCE::EXECUTION",
                "PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION",
                "PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION",
                "PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION",
            },
        )
        self.assertFalse(out["semantic_leaf_closed"])
        self.assertFalse(out["root_closed"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_real_root_specific_runtime_challenges_pass(self):
        for root_id, result in self.runtime_results.items():
            self.assertTrue(result["pass"], (root_id, result))
        self.assertEqual(
            self.runtime_results["R8_POPULATION_CONTEXT_OPERATOR"]["executed_count"],
            512,
        )
        self.assertEqual(
            self.runtime_results["R11_ADAPTIVE_INTEGRITY_SECURITY"][
                "contamination_admissible_witness_count"
            ],
            9,
        )

    def test_manifest_acceptance_drift_fails_closed(self):
        manifest = deepcopy(self.docs["manifest"])
        for row in manifest["roots"]:
            if row["root_id"] == "R5_EVALUATOR_REFERENCE":
                row["execution_leaf"]["acceptance"] = "WEAKER_ACCEPTANCE"
                break
        out = self._evaluate(manifest=manifest)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "EXECUTION_ACCEPTANCE_DRIFT:R5_EVALUATOR_REFERENCE",
        )

    def test_missing_canonical_defeater_fails_closed(self):
        catalog = deepcopy(self.docs["catalog"])
        catalog["challenges"] = [
            row
            for row in catalog["challenges"]
            if row.get("id") != "C17_REFERENCE_STANDARD_ERROR"
        ]
        out = self._evaluate(catalog=catalog)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CANONICAL_DEFEATER_SET_DRIFT:R5_EVALUATOR_REFERENCE",
        )

    def test_failed_root_runtime_evidence_fails_closed(self):
        runtime_results = deepcopy(self.runtime_results)
        runtime_results["R9_TEMPORAL_DEPLOYMENT"]["pass"] = False
        out = self._evaluate(runtime_results=runtime_results)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "ROOT_RUNTIME_CHALLENGE_FAILED:R9_TEMPORAL_DEPLOYMENT",
        )

    def test_missing_assurance_graph_defeater_node_fails_closed(self):
        graph = deepcopy(self.docs["graph"])
        graph["nodes"] = [
            row
            for row in graph["nodes"]
            if row.get("id") != "C53_PROMPT_INJECTION_JUDGE_CONTROL"
        ]
        out = self._evaluate(graph=graph)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CANONICAL_ROOT_DEFEATER_CHALLENGE_FAILED:R11_ADAPTIVE_INTEGRITY_SECURITY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
