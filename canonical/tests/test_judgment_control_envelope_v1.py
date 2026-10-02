import unittest

from canonical.runtime.judgment_control_envelope_v1 import (
    configured_terminal_decision,
    evaluate_materiality_counterfactual,
)

def common():
    return {
        "brain_sources_bound": True,
        "source_traceability_pass": True,
        "provenance_complete": True,
        "requirement_coverage_pass": True,
        "counterexample_coverage_pass": True,
        "contradictions_exposed_or_resolved": True,
        "semantic_identifiability": "UNIQUE",
        "finite_identifiability": "NOT_APPLICABLE",
        "discriminator_authorized": False,
    }

class Tests(unittest.TestCase):
    def test_materiality_counterfactual_passes(self):
        out = evaluate_materiality_counterfactual()
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["configuration_material_control_proven"])
        self.assertFalse(out["benchmark_case_content_consumed"])
        self.assertFalse(out["hidden_oracle_case_content_consumed"])

    def test_finance_blocks_unverified_rule_or_exception(self):
        e = common()
        e.update({
            "rule_applicability_verified": False,
            "material_exceptions_complete": False,
            "exact_reconciliation_pass": True,
        })
        p = {"decision":"CONCLUDE","claim_ids":["c"],"source_refs":["s"]}
        out = configured_terminal_decision(p, e, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn(
            "REQUIRED_VERIFIED_PREDICATE_FALSE_OR_UNKNOWN:rule_applicability_verified",
            out["errors"],
        )

    def test_finance_accepts_only_complete_supported_conclusion(self):
        e = common()
        e.update({
            "rule_applicability_verified": True,
            "material_exceptions_complete": True,
            "exact_reconciliation_pass": True,
        })
        p = {"decision":"CONCLUDE","claim_ids":["c"],"source_refs":["s"]}
        self.assertTrue(configured_terminal_decision(p, e, mode="FINANCE")["accepted"])

    def test_unknown_blocks_forced_conclusion_under_ambiguity(self):
        e = common()
        e.update({
            "semantic_identifiability":"AMBIGUOUS",
            "finite_identifiability":"NONIDENTIFIABLE",
            "transfer_provenance_verified":True,
            "negative_transfer_checked":True,
        })
        p = {"decision":"CONCLUDE","claim_ids":["c"],"source_refs":["a","b"]}
        out = configured_terminal_decision(p, e, mode="UNKNOWN_DOMAIN")
        self.assertFalse(out["accepted"])
        self.assertIn(
            "FORCED_CONCLUSION_WITHOUT_UNIQUE_SEMANTIC_IDENTIFICATION",
            out["errors"],
        )
        self.assertIn(
            "UNKNOWN_DOMAIN_CONCLUSION_WITHOUT_RESOLVED_VERSION_SPACE",
            out["errors"],
        )

    def test_unknown_allows_authorized_discriminator_when_nonidentifiable(self):
        e = common()
        e.update({
            "semantic_identifiability":"AMBIGUOUS",
            "finite_identifiability":"NONIDENTIFIABLE",
            "discriminator_authorized":True,
        })
        p = {"decision":"REQUEST_DISCRIMINATOR","discriminator":"measure X"}
        out = configured_terminal_decision(p, e, mode="UNKNOWN_DOMAIN")
        self.assertTrue(out["accepted"], out)

    def test_unknown_allows_witnessed_abstention_when_nonidentifiable(self):
        e = common()
        e.update({
            "semantic_identifiability":"NONIDENTIFIABLE",
            "finite_identifiability":"NONIDENTIFIABLE",
        })
        p = {"decision":"ABSTAIN","nonidentifiability_witness":"h1 and h2 observationally equivalent"}
        out = configured_terminal_decision(p, e, mode="UNKNOWN_DOMAIN")
        self.assertTrue(out["accepted"], out)

    def test_blanket_abstention_on_identifiable_case_is_blocked(self):
        e = common()
        p = {"decision":"ABSTAIN","nonidentifiability_witness":"none"}
        out = configured_terminal_decision(p, e, mode="UNKNOWN_DOMAIN")
        self.assertFalse(out["accepted"])
        self.assertIn("BLANKET_ABSTENTION_ON_IDENTIFIABLE_CASE", out["errors"])

    def test_missing_provenance_blocks_every_terminal_act(self):
        e = common()
        e["provenance_complete"] = False
        e.update({
            "rule_applicability_verified": True,
            "material_exceptions_complete": True,
            "exact_reconciliation_pass": True,
        })
        p = {"decision":"CONCLUDE","claim_ids":["c"],"source_refs":["s"]}
        out = configured_terminal_decision(p, e, mode="FINANCE")
        self.assertFalse(out["accepted"])
        self.assertIn(
            "REQUIRED_VERIFIED_PREDICATE_FALSE_OR_UNKNOWN:provenance_complete",
            out["errors"],
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
