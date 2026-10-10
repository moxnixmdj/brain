from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_scoped_evidence_v1 as scoped


class ProfessionalQualityScopedEvidenceV1Tests(unittest.TestCase):
    def test_current_r3_r4_r5_r6_r7_r10_and_r11_scopes_are_admitted_without_global_credit(self):
        out = scoped.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["admitted_scope_count"], 7, out)
        self.assertEqual(out["rejected_scope_count"], 0, out)
        self.assertFalse(out["global_leaf_closure"])
        self.assertFalse(out["global_root_closure"])
        self.assertFalse(out["domain_semantic_closure"])
        self.assertFalse(out["domain_execution_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_registry_cannot_claim_global_leaf_closure(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["global_leaf_closure"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "GLOBAL_LEAF_CLOSURE_FORBIDDEN",
            out["rejected_scopes"][0]["errors"],
            out,
        )

    def test_stale_source_receipt_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["source_receipt"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "SOURCE_RECEIPT_STALE",
            out["rejected_scopes"][0]["errors"],
            out,
        )

    def test_wrong_leaf_binding_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        registry["entries"][0]["contributes_to_leaf_ids"] = [
            "PQ::R1_TARGET_SPECIFICATION::SEMANTIC"
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        self.assertIn(
            "LEAF_BINDING_INVALID",
            out["rejected_scopes"][0]["errors"],
            out,
        )

    def test_r7_scope_preserves_exact_single_edit_claim_kind(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R7_CAUSAL_PRESCRIPTIVE"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE",
        )
        self.assertEqual(
            set(row["contributes_to_leaf_ids"]),
            {
                "PQ::R7_CAUSAL_PRESCRIPTIVE::SEMANTIC",
                "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
            },
        )
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(row["global_root_credit"])

    def test_r3_scope_is_execution_only_and_preserves_limitations(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R3_REALIZATION_OBSERVATION"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "BOUNDED_GENERATED_EXPLICIT_LOW_LEVEL_TEXT_EDIT_RENDER_PRESERVATION",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R3_REALIZATION_OBSERVATION::EXECUTION"],
        )
        self.assertIn(
            "NO_ARBITRARY_SEMANTIC_TARGET_SELECTION",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r6_scope_is_execution_only_and_preserves_grounding_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R6_EVIDENCE_GROUNDING_DEPENDENCE"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "CONTENT_ADDRESSED_SCOPE_MATCHED_LEAF_EVIDENCE_ADMISSION_WITH_STATUS_NONAUTHORITY",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION"],
        )
        self.assertIn(
            "NO_GENERAL_EVIDENCE_TRUTH_CLOSURE",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r6_registry_cannot_promote_global_or_execution_leaf_credit(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r6 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R6_EVIDENCE_GROUNDING_DEPENDENCE"
        )
        r6["global_root_closure"] = True
        r6["execution_leaf_credit"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R6_EVIDENCE_GROUNDING_DEPENDENCE"
        )
        self.assertIn("GLOBAL_ROOT_CLOSURE_FORBIDDEN", row["errors"])
        self.assertIn("EXECUTION_LEAF_CREDIT_FORBIDDEN", row["errors"])


    def test_r10_scope_is_execution_only_and_preserves_decision_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R10_ANALYSIS_DECISION"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "LOSSLESS_DECISION_SUFFICIENT_GAP_REPRESENTATION_AND_MINIMUM_POLICY_CHANGING_INFORMATION_ROUTING",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R10_ANALYSIS_DECISION::EXECUTION"],
        )
        self.assertIn(
            "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r10_registry_cannot_promote_global_or_execution_leaf_credit(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r10 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R10_ANALYSIS_DECISION"
        )
        r10["global_root_closure"] = True
        r10["execution_leaf_credit"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R10_ANALYSIS_DECISION"
        )
        self.assertIn("GLOBAL_ROOT_CLOSURE_FORBIDDEN", row["errors"])
        self.assertIn("EXECUTION_LEAF_CREDIT_FORBIDDEN", row["errors"])


    def test_r11_scope_is_execution_only_and_bounded_to_clean_lane_firewall(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R11_ADAPTIVE_INTEGRITY_SECURITY"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "CLEAN_EVALUATION_LANE_POST_IDENTITY_DISCOVERY_REVOCATION",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION"],
        )
        self.assertIn(
            "NO_GLOBAL_R11_LEAF_OR_ROOT_CLOSURE",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r11_registry_cannot_promote_global_or_execution_leaf_credit(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r11 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R11_ADAPTIVE_INTEGRITY_SECURITY"
        )
        r11["global_root_closure"] = True
        r11["execution_leaf_credit"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R11_ADAPTIVE_INTEGRITY_SECURITY"
        )
        self.assertIn("GLOBAL_ROOT_CLOSURE_FORBIDDEN", row["errors"])
        self.assertIn("EXECUTION_LEAF_CREDIT_FORBIDDEN", row["errors"])


    def test_r3_registry_cannot_promote_execution_leaf_credit(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r3 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R3_REALIZATION_OBSERVATION"
        )
        r3["execution_leaf_credit"] = True
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        r3_result = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R3_REALIZATION_OBSERVATION"
        )
        self.assertIn("EXECUTION_LEAF_CREDIT_FORBIDDEN", r3_result["errors"])

    def test_r4_scope_is_execution_only_and_preserves_measurement_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R4_MEASUREMENT_CONSTRUCT"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "CONTENT_ADDRESSED_TYPED_MECHANICAL_ARTIFACT_MEASUREMENT_AND_ACCEPTANCE",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION"],
        )
        self.assertIn(
            "NO_AUTOMATIC_RUBRIC_OR_CONSTRUCT_SEMANTIC_ALIGNMENT",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "NO_HOLISTIC_OR_VISUAL_QUALITY_MEASUREMENT",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r4_stale_underlying_measurement_runtime_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r4 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R4_MEASUREMENT_CONSTRUCT"
        )
        r4["measurement_runtime"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R4_MEASUREMENT_CONSTRUCT"
        )
        self.assertIn("MEASUREMENT_RUNTIME_STALE", row["errors"])


    def test_r5_scope_is_execution_only_and_preserves_evaluator_semantic_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R5_EVALUATOR_REFERENCE"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "CONDITIONAL_EVALUATOR_UNCERTAINTY_ROBUST_MARGIN_CERTIFICATE",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R5_EVALUATOR_REFERENCE::EXECUTION"],
        )
        self.assertIn(
            "NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_THE_DECOMPOSITION",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "NO_PUBLIC_RUBRIC_TO_OWNER_SEMANTIC_PROMOTION",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])



if __name__ == "__main__":
    unittest.main()
