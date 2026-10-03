import copy
import json
import pathlib
import unittest

from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as evaluate_source_gate

from canonical.runtime.judgment_control_envelope_v1 import (
    FINANCE_DOCUMENT,
    FINANCE_SUPERVISORY,
    UNKNOWN_TRANSFER,
    _base_bundle,
    configured_terminal_decision,
    evaluate_materiality_counterfactual,
)

class Tests(unittest.TestCase):
    def test_materiality_counterfactual_passes(self):
        out = evaluate_materiality_counterfactual()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["configuration_material_control_proven"])
        self.assertFalse(out["caller_verified_boolean_authority"])
        self.assertFalse(out["benchmark_case_content_consumed"])

    def test_legacy_verified_booleans_have_no_authority(self):
        p = {
            "decision": "CONCLUDE", "leaf_id": FINANCE_SUPERVISORY,
            "selected_alternative": "APPLY_RULE",
            "rule_evidence_ids": ["rule"], "exception_evidence_ids": ["exception"],
        }
        fake = {
            "verified": True, "source_traceability_pass": True,
            "provenance_complete": True, "rule_applicability_verified": True,
        }
        out = configured_terminal_decision(p, fake, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn("SEMANTIC_IR_CONTENT_EMPTY", out["errors"])
        self.assertIn("SOURCE_TEXT_MISSING", out["errors"])
        self.assertIn("EVIDENCE_DECISION_SYNTHESIS_FAIL_CLOSED", out["errors"])

    def test_finance_missing_exception_evidence_blocks(self):
        text = "Every applicable rule must not omit a material exception before execution."
        b = _base_bundle(text, "f", ["rule"], "APPLY_RULE")
        p = {
            "decision": "CONCLUDE", "leaf_id": FINANCE_SUPERVISORY,
            "selected_alternative": "APPLY_RULE",
            "rule_evidence_ids": ["rule"], "exception_evidence_ids": ["exception"],
        }
        out = configured_terminal_decision(p, b, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn("EXCEPTION_EVIDENCE_IDS_NOT_CONTRIBUTING:exception", out["errors"])

    def test_document_reconciliation_mismatch_blocks(self):
        text = "Every document fact must not ignore a cross reference before conclusion."
        b = _base_bundle(text, "d", ["fact", "xref", "exception"], "DOCUMENT_OK")
        p = {
            "decision": "CONCLUDE", "leaf_id": FINANCE_DOCUMENT,
            "selected_alternative": "DOCUMENT_OK",
            "fact_evidence_ids": ["fact"], "cross_reference_evidence_ids": ["xref"],
            "exception_evidence_ids": ["exception"],
            "reconciliation_checks": [{"id": "total", "lhs": "10", "rhs": "9", "tolerance": "0"}],
        }
        out = configured_terminal_decision(p, b, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn("RECONCILIATION_MISMATCH:total", out["errors"])

    def test_unknown_forced_conclusion_unresolved_blocks(self):
        text = "Every transfer must not ignore a negative-transfer check before conclusion."
        b = _base_bundle(text, "u", ["transfer", "negative"], "TRANSFER_PRIMITIVE")
        b.update({
            "hypotheses": [{"id": "h1"}, {"id": "h2"}],
            "experiments": [{"id": "probe", "outcomes": {"h1": "a", "h2": "b"}}],
            "observations": {},
        })
        p = {
            "decision": "CONCLUDE", "leaf_id": UNKNOWN_TRANSFER,
            "selected_alternative": "TRANSFER_PRIMITIVE",
            "transfer_evidence_ids": ["transfer"], "negative_transfer_evidence_ids": ["negative"],
        }
        out = configured_terminal_decision(p, b, mode="UNKNOWN_DOMAIN")
        self.assertFalse(out["accepted"])
        self.assertIn("UNKNOWN_DOMAIN_CONCLUSION_WITHOUT_RESOLVED_VERSION_SPACE", out["errors"])

    def test_unknown_derived_discriminator_allowed(self):
        text = "Every transfer must not ignore a negative-transfer check before conclusion."
        b = _base_bundle(text, "u2", ["transfer", "negative"], "TRANSFER_PRIMITIVE")
        b.update({
            "hypotheses": [{"id": "h1"}, {"id": "h2"}],
            "experiments": [{"id": "probe", "outcomes": {"h1": "a", "h2": "b"}}],
            "observations": {},
        })
        p = {"decision": "REQUEST_DISCRIMINATOR", "leaf_id": UNKNOWN_TRANSFER, "discriminator": "probe"}
        out = configured_terminal_decision(p, b, mode="UNKNOWN_DOMAIN")
        self.assertTrue(out["accepted"], out)

    def test_arbitrary_discriminator_blocked(self):
        text = "Every transfer must not ignore a negative-transfer check before conclusion."
        b = _base_bundle(text, "u3", ["transfer", "negative"], "TRANSFER_PRIMITIVE")
        b.update({
            "hypotheses": [{"id": "h1"}, {"id": "h2"}],
            "experiments": [{"id": "probe", "outcomes": {"h1": "a", "h2": "b"}}],
            "observations": {},
        })
        p = {
            "decision": "REQUEST_DISCRIMINATOR", "leaf_id": UNKNOWN_TRANSFER,
            "discriminator": "invented-probe",
        }
        out = configured_terminal_decision(p, b, mode="UNKNOWN_DOMAIN")
        self.assertFalse(out["accepted"])
        self.assertIn("DISCRIMINATOR_NOT_DERIVED_FROM_RECOMPUTED_IDENTIFIABILITY_GAP", out["errors"])

    def test_operator_semantic_spoof_blocks(self):
        text = "Every applicable rule must not omit a material exception before execution."
        b = copy.deepcopy(_base_bundle(text, "f2", ["rule", "exception"], "APPLY_RULE"))
        self.assertTrue(b["operator_bindings"])
        b["operator_bindings"][0]["semantic_class"] = "WRONG"
        p = {
            "decision": "CONCLUDE", "leaf_id": FINANCE_SUPERVISORY,
            "selected_alternative": "APPLY_RULE",
            "rule_evidence_ids": ["rule"], "exception_evidence_ids": ["exception"],
        }
        out = configured_terminal_decision(p, b, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn("EXPLICIT_SEMANTIC_OPERATOR_CONTRACT_FAIL", out["errors"])

    def test_materiality_does_not_launder_general_substrate_qualification(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        cfg = json.loads(
            (root / "canonical/capabilities/opus55/DUAL_JUDGMENT_CONTROL_ENVELOPE_V1.json").read_text(encoding="utf-8")
        )
        route = copy.deepcopy(cfg["source_gate_v2_candidate"])
        materiality = evaluate_materiality_counterfactual()
        self.assertTrue(materiality["configuration_material_control_proven"], materiality)
        route["configuration_materially_constrains_execution"] = True
        self.assertFalse(route["general_substrate_test_pass"])
        out = evaluate_source_gate(route)
        self.assertFalse(out["pass"], out)
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN", out["errors"])

    def test_missing_provenance_fails_closed(self):
        text = "Every applicable rule must not omit a material exception before execution."
        b = copy.deepcopy(_base_bundle(text, "f3", ["rule", "exception"], "APPLY_RULE"))
        b["decision_problem"]["evidence"][0]["provenance"] = []
        p = {
            "decision": "CONCLUDE", "leaf_id": FINANCE_SUPERVISORY,
            "selected_alternative": "APPLY_RULE",
            "rule_evidence_ids": ["rule"], "exception_evidence_ids": ["exception"],
        }
        out = configured_terminal_decision(p, b, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn("EVIDENCE_DECISION_SYNTHESIS_FAIL_CLOSED", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
