from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped


class ProfessionalQualityScopedEvidenceV1Tests(unittest.TestCase):
    def test_current_all_twelve_roots_have_bounded_scoped_capabilities_without_global_credit(self):
        out = scoped.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertIn(out["admitted_scope_count"], {16, 21}, out)
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

    def test_r6_scope_projects_bounded_semantic_and_execution_grounding_evidence(self):
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
            set(row["contributes_to_leaf_ids"]),
            {
                "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::SEMANTIC",
                "PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION",
            },
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



    def test_r10_decision_semantic_scope_is_bounded_and_nonpromotional(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "LOSSLESS_MINIMUM_INFORMATION_DECISION_SUFFICIENCY_SEMANTICS"
        )
        self.assertEqual(row["root_id"], "R10_ANALYSIS_DECISION")
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R10_ANALYSIS_DECISION::SEMANTIC"],
        )
        self.assertIn(
            "NO_EVIDENCE_IS_OMITTED_WITHOUT_A_FUTURE_OMISSION_CERTIFICATE",
            row["claim_scope"]["guarantees"],
        )
        self.assertIn(
            "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(row["global_root_credit"])

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



    def test_r11_firewall_semantic_scope_is_bounded_and_nonpromotional(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "CLEAN_EVALUATION_LANE_POST_IDENTITY_REVOCATION_SEMANTICS"
        )
        self.assertEqual(row["root_id"], "R11_ADAPTIVE_INTEGRITY_SECURITY")
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::SEMANTIC"],
        )
        self.assertIn(
            "UNKNOWN_CAPABILITY_DENIES_FAIL_CLOSED",
            row["claim_scope"]["guarantees"],
        )
        self.assertIn(
            "NO_GENERAL_PROMPT_INJECTION_CLOSURE",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(row["global_root_credit"])

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



    def test_r1_target_semantic_scope_is_bounded_and_nonpromotional(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "EXACT_PARAMETERIZED_PROFESSIONAL_ARTIFACT_TARGET_SEMANTICS"
        )
        self.assertEqual(row["root_id"], "R1_TARGET_SPECIFICATION")
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R1_TARGET_SPECIFICATION::SEMANTIC"],
        )
        self.assertIn(
            "NO_ARBITRARY_USER_PROMPT_SEMANTIC_COMPLETENESS",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "UNRESOLVED_RUNTIME_TASK_AMBIGUITY_REMAINS_OPEN",
            row["claim_scope"]["guarantees"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(row["global_root_credit"])

    def test_r1_scope_is_execution_only_and_preserves_semantic_truth_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R1_TARGET_SPECIFICATION"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "CONTENT_ADDRESSED_BEHAVIORAL_CONTRACT_STRUCTURAL_COMPLETENESS_GATE",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R1_TARGET_SPECIFICATION::EXECUTION"],
        )
        self.assertIn(
            "NO_OPAQUE_FIELD_OR_EXTENSION_SEMANTIC_INTERPRETATION",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "NO_NEGATIVE_POLICY_ABSENCE_OR_GLOBAL_MINIMALITY_WITHOUT_SEPARATE_COMPLETENESS_PROOF",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r1_stale_contract_schema_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r1 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R1_TARGET_SPECIFICATION"
        )
        r1["contract_schema"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R1_TARGET_SPECIFICATION"
        )
        self.assertIn("CONTRACT_SCHEMA_STALE", row["errors"])


    def test_r2_scope_is_execution_only_and_preserves_open_world_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R2_CANDIDATE_SEARCH"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "FINITE_SCOPE_COMPLETE_COMMON_POLICY_OR_MINIMUM_TRUTHFUL_DISCRIMINATOR_SEARCH",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R2_CANDIDATE_SEARCH::EXECUTION"],
        )
        self.assertIn(
            "NO_GLOBAL_CANDIDATE_SEARCH_COMPLETENESS",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "NO_ESCAPE_PROGRESS_TOTALITY",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r2_stale_minimax_dependency_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r2 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R2_CANDIDATE_SEARCH"
        )
        r2["minimax_runtime"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R2_CANDIDATE_SEARCH"
        )
        self.assertIn("MINIMAX_RUNTIME_STALE", row["errors"])


    def test_r9_scope_is_execution_only_and_preserves_deployment_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R9_TEMPORAL_DEPLOYMENT"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "FROZEN_POPULATION_CONSERVATIVE_CENSORING_AND_EARLY_FAILURE_ACCOUNTING",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R9_TEMPORAL_DEPLOYMENT::EXECUTION"],
        )
        self.assertIn(
            "NO_MULTIHORIZON_DEPLOYMENT_VALIDITY",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "NO_DISTRIBUTION_SHIFT_TRANSPORT_CLAIM",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])



    def test_r8_population_semantic_scope_is_bounded_and_nonpromotional(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["claim_kind"] == "FROZEN_512_CASE_DELEGATION_POPULATION_SEMANTICS"
        )
        self.assertEqual(row["root_id"], "R8_POPULATION_CONTEXT_OPERATOR")
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R8_POPULATION_CONTEXT_OPERATOR::SEMANTIC"],
        )
        self.assertIn(
            "POPULATION_SIZE_IS_EXACTLY_512",
            row["claim_scope"]["guarantees"],
        )
        self.assertIn(
            "NO_CONSTITUENCY_SUPPORT_CLAIM",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["global_leaf_credit"])
        self.assertFalse(row["global_root_credit"])

    def test_r8_scope_is_execution_only_and_preserves_population_limits(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R8_POPULATION_CONTEXT_OPERATOR"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "FROZEN_512_CASE_PRE_BEACON_DELEGATION_POPULATION_BINDING",
        )
        self.assertEqual(
            row["contributes_to_leaf_ids"],
            ["PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION"],
        )
        self.assertIn(
            "NO_CONSTITUENCY_SUPPORT_CLAIM",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "PREFLIGHT_ONLY__NO_POST_FREEZE_TERMINAL_RESULT",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r12_scope_projects_bounded_semantic_and_execution_meta_evidence(self):
        out = scoped.evaluate()
        row = next(
            x for x in out["admitted_scopes"]
            if x["root_id"] == "R12_META_COMPOSITION_CLOSURE"
        )
        self.assertEqual(
            row["claim_scope"]["kind"],
            "FAIL_CLOSED_ASSURANCE_GRAPH_META_COMPOSITION_AND_ORDER_INDEPENDENT_DEFEATER_ROUTING",
        )
        self.assertEqual(
            set(row["contributes_to_leaf_ids"]),
            {
                "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC",
                "PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION",
            },
        )
        self.assertIn(
            "NO_UNKNOWN_DEFEATER_COMPLETENESS",
            row["claim_scope"]["limitations"],
        )
        self.assertIn(
            "NO_DOMAIN_EXECUTION_CLOSURE",
            row["claim_scope"]["limitations"],
        )
        self.assertFalse(row["semantic_leaf_credit"])
        self.assertFalse(row["execution_leaf_credit"])

    def test_r8_stale_scope_governance_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r8 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R8_POPULATION_CONTEXT_OPERATOR"
        )
        r8["scope_governance"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R8_POPULATION_CONTEXT_OPERATOR"
        )
        self.assertIn("SCOPE_GOVERNANCE_STALE", row["errors"])

    def test_r12_stale_scope_governance_fails_closed(self):
        registry = json.loads(scoped.REGISTRY.read_text())
        r12 = next(
            x for x in registry["entries"]
            if x["root_id"] == "R12_META_COMPOSITION_CLOSURE"
        )
        r12["scope_governance"]["git_blob_sha"] = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "registry.json"
            p.write_text(json.dumps(registry, indent=2) + "\n")
            out = scoped.evaluate(registry_path=p)
        self.assertFalse(out["pass"], out)
        row = next(
            x for x in out["rejected_scopes"]
            if x["root_id"] == "R12_META_COMPOSITION_CLOSURE"
        )
        self.assertIn("SCOPE_GOVERNANCE_STALE", row["errors"])



if __name__ == "__main__":
    unittest.main()
