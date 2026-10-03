from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_universal_scope_certificate_v2 import (
    REQUIRED_FACTS,
    ROOT,
    derive_source_facts,
    prove_from_facts,
    verify,
)

def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

class ToolDiscoveryUniversalScopeCertificateV2Tests(unittest.TestCase):
    def setUp(self):
        self.candidate = text("canonical/runtime/tool_discovery_information_safe_candidate.py")
        self.proof_v1 = text("canonical/runtime/tool_discovery_information_safe_proof.py")
        self.proof_v2 = text("canonical/runtime/tool_discovery_information_safe_proof_v2.py")

    def test_live_exact_sources_derive_candidate_universal_scope_proof(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"], out)
        self.assertTrue(out["scope_atom_satisfied_candidate"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["preserved_180_case_sample_used_for_scope_proof"])
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_every_formal_premise_is_load_bearing(self):
        good = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_proved"], name)
            self.assertIn(name, out["missing"])

    def test_remove_total_order_kills_proof(self):
        mutant = self.candidate.replace(
            'tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))',
            'tools = list(tools)',
        )
        facts = derive_source_facts(mutant, self.proof_v1, self.proof_v2)
        self.assertFalse(facts["CANDIDATE_TOTAL_ORDERS_ELIGIBLE_TOOLS"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_remove_negative_elimination_kills_proof(self):
        mutant = self.candidate.replace("known_false = True", "known_false = False")
        facts = derive_source_facts(mutant, self.proof_v1, self.proof_v2)
        self.assertFalse(facts["CANDIDATE_REJECTS_TOOL_ON_CURRENT_NEGATIVE"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_remove_unknown_probe_progress_kills_proof(self):
        mutant = self.candidate.replace("unknown.append(cap)", "unknown.extend([])")
        facts = derive_source_facts(mutant, self.proof_v1, self.proof_v2)
        self.assertFalse(facts["CANDIDATE_PROBES_ONLY_UNKNOWN_REQUIRED_PAIR"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_stale_evidence_filter_is_load_bearing(self):
        mutant = self.candidate.replace(
            'if tid not in epochs or rec.get("epoch") != epochs[tid]:',
            'if tid not in epochs:',
        )
        facts = derive_source_facts(mutant, self.proof_v1, self.proof_v2)
        self.assertFalse(facts["CANDIDATE_FILTERS_EVIDENCE_TO_CURRENT_EPOCH"])
        self.assertFalse(facts["VERSION_CHANGE_INVALIDATES_CHANGED_TOOL_EVIDENCE"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_probe_soundness_is_load_bearing(self):
        mutant = self.proof_v1.replace(
            "supported = cap in _hidden_caps(case, stage, tid)",
            "supported = False",
        )
        facts = derive_source_facts(self.candidate, mutant, self.proof_v2)
        self.assertFalse(facts["PROBE_RECEIPT_RETURNS_EXACT_CURRENT_HIDDEN_TRUTH"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_oracle_least_cost_definition_is_load_bearing(self):
        mutant = self.proof_v1.replace("eligible.sort()", "eligible.reverse()")
        facts = derive_source_facts(self.candidate, mutant, self.proof_v2)
        self.assertFalse(facts["ORACLE_DEFINES_LEAST_COST_SUFFICIENT_ELIGIBLE_TOOL"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_no_route_escalation_guard_is_load_bearing(self):
        mutant = self.proof_v2.replace(
            '"PREMATURE_ESCALATION_WITH_UNTESTED_ROUTE"',
            '"UNTESTED_ROUTE_IGNORED"',
        )
        facts = derive_source_facts(self.candidate, self.proof_v1, mutant)
        self.assertFalse(facts["NO_SUFFICIENT_ROUTE_ESCALATION_IS_CHECKED_AFTER_NEGATIVE_EVIDENCE"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
