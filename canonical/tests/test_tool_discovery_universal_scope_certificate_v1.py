from __future__ import annotations

import json
import unittest

from canonical.runtime.tool_discovery_universal_scope_certificate_v1 import (
    REQUIRED_FACTS,
    ROOT,
    derive_source_facts,
    prove_from_facts,
    verify,
)


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def data(rel: str):
    return json.loads(text(rel))


class ToolDiscoveryUniversalScopeCertificateV1Tests(unittest.TestCase):
    def setUp(self):
        self.candidate = text("canonical/runtime/tool_discovery_information_safe_candidate.py")
        self.v1 = text("canonical/runtime/tool_discovery_information_safe_proof.py")
        self.v2 = text("canonical/runtime/tool_discovery_information_safe_proof_v2.py")
        self.binding = data("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
        self.protocol = data("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")

    def facts(self, candidate=None, v1=None, v2=None, binding=None, protocol=None):
        return derive_source_facts(
            self.candidate if candidate is None else candidate,
            self.v1 if v1 is None else v1,
            self.v2 if v2 is None else v2,
            self.binding if binding is None else binding,
            self.protocol if protocol is None else protocol,
        )

    def test_live_exact_sources_prove_universal_frozen_protocol_scope(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"], out)
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(out["target_predicate"], "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertFalse(out["source_180_of_180_load_bearing"])
        self.assertFalse(out["internet_wide_tool_identity_completeness_claim"])
        self.assertEqual(out["acceptance_credit_delta"], 0)

    def test_every_formal_fact_is_load_bearing(self):
        good = {name: True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_proved"], name)
            self.assertIn(name, out["missing"])

    def test_removing_authorization_filter_kills_scope_fact(self):
        mutant = self.candidate.replace(
            'if t.get("available") is True and t.get("authorized") is True',
            'if t.get("available") is True',
        )
        facts = self.facts(candidate=mutant)
        self.assertFalse(facts["POLICY_FILTERS_TO_AVAILABLE_AUTHORIZED_TOOLS"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_removing_cost_order_kills_optimality_fact(self):
        mutant = self.candidate.replace(
            'tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))',
            'tools.sort(key=lambda t: str(t.get("tool_id") or ""))',
        )
        facts = self.facts(candidate=mutant)
        self.assertFalse(facts["POLICY_ORDERS_ELIGIBLE_TOOLS_BY_COST_THEN_ID"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_accepting_stale_receipts_kills_epoch_fact(self):
        mutant = self.candidate.replace(
            'if tid not in epochs or rec.get("epoch") != epochs[tid]:',
            'if tid not in epochs:',
        )
        facts = self.facts(candidate=mutant)
        self.assertFalse(facts["POLICY_USES_CURRENT_EPOCH_EVIDENCE_ONLY"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_selecting_before_unknowns_resolved_kills_sufficiency_fact(self):
        mutant = self.candidate.replace(
            'if unknown:\n            return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}',
            'if unknown:\n            return {"action": "SELECT", "tool_id": tid}',
        )
        facts = self.facts(candidate=mutant)
        self.assertFalse(facts["POLICY_PROBES_ONLY_UNKNOWN_REQUIRED_CAPABILITY"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_removing_premature_escalation_guard_kills_no_route_fact(self):
        mutant = self.v2.replace(
            'if not any(negatives):',
            'if False:',
        )
        facts = self.facts(v2=mutant)
        self.assertFalse(facts["V2_REJECTS_PREMATURE_ESCALATION"])
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])

    def test_hiding_tool_ids_from_candidate_breaks_frozen_scope_binding(self):
        binding = json.loads(json.dumps(self.binding))
        binding["information_boundary"]["candidate_visible"].remove("TOOL_IDS_AND_DECLARED_COSTS")
        facts = self.facts(binding=binding)
        self.assertFalse(
            facts["FROZEN_PROTOCOL_EXPOSES_TOOL_IDS_COSTS_AUTHORIZATION_AND_VERSION_EVENTS"]
        )
        self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
