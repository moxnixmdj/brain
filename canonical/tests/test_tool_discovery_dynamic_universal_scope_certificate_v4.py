from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_dynamic_universal_scope_certificate_v4 as cert

ROOT = Path(__file__).resolve().parents[2]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ToolDiscoveryDynamicV4UniversalScopeCertificateTests(unittest.TestCase):
    def test_exact_sources_prove_program_side_universally(self):
        out = cert.verify()
        self.assertTrue(out["conditional_universal_program_proof"], out)
        self.assertTrue(out["v1_refinement_falsified"], out)
        self.assertTrue(out["v4_repair_bound"], out)
        self.assertTrue(out["target_preserved"], out)
        self.assertFalse(out["universal_target_proved"])
        self.assertFalse(out["interface_instance_verified"])
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_every_formal_premise_is_load_bearing(self):
        good = {name: True for name in cert.REQUIRED_FACTS}
        self.assertTrue(cert.prove_from_facts(good)["conditional_universal_program_proof"])
        for name in cert.REQUIRED_FACTS:
            mutant = dict(good)
            mutant[name] = False
            out = cert.prove_from_facts(mutant)
            self.assertFalse(out["conditional_universal_program_proof"], name)
            self.assertIn(name, out["missing"])

    def test_selection_before_discovery_mutation_kills_proof(self):
        source = text(cert.V4)
        marker = '''    # Load-bearing V4 repair: no route is selected while an authoritative
    # available discovery source remains unqueried. Without source lower-bound
    # guarantees, this is necessary to prove global least-cost selection.
'''
        self.assertIn(marker, source)
        # A direct mutation of the load-bearing ordering marker must destroy the
        # derived order fact rather than leave the certificate green.
        mutant = source.replace("    if sources:\n", "    if False and sources:\n", 1)
        facts = cert.derive_source_facts(mutant)
        self.assertFalse(facts["V4_DISCOVERY_PRECEDES_ANY_TOOL_PROBE_OR_SELECT"] or "if sources:" in mutant)
        out = cert.verify(v4_source_override=mutant)
        self.assertFalse(out["conditional_universal_program_proof"])

    def test_removing_queried_filter_kills_progress_premise(self):
        source = text(cert.V4)
        mutant = source.replace(
            'and str(s.get("source_id") or "") not in queried',
            'and True',
            1,
        )
        out = cert.verify(v4_source_override=mutant)
        self.assertFalse(out["conditional_universal_program_proof"])
        self.assertFalse(out["facts"]["V4_DISCOVERY_NEVER_REQUERIES_RECEIPTED_SOURCE"])

    def test_removing_tool_cost_order_kills_least_cost_premise(self):
        source = text(cert.V4)
        mutant = source.replace(
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))',
            'tools.sort(key=lambda t:str(t.get("tool_id") or ""))',
            1,
        )
        out = cert.verify(v4_source_override=mutant)
        self.assertFalse(out["conditional_universal_program_proof"])
        self.assertFalse(out["facts"]["V4_TOOL_ORDER_IS_DECLARED_COST_THEN_ID"])

    def test_stale_probe_evidence_mutation_kills_epoch_premise(self):
        source = text(cert.V4)
        mutant = source.replace(
            'and int(rec.get("epoch",-1))==epochs[tid]:',
            ':',
            1,
        )
        out = cert.verify(v4_source_override=mutant)
        self.assertFalse(out["conditional_universal_program_proof"])
        self.assertFalse(out["facts"]["V4_PROBE_EVIDENCE_IS_CURRENT_EPOCH_ONLY"])

    def test_interface_finiteness_is_load_bearing(self):
        contract = json.loads(text(cert.CONTRACT))
        contract = copy.deepcopy(contract)
        contract["required_properties"].remove(
            "FINITE_TOOL_IDENTITY_SET_PER_AUTHORITATIVE_DISCOVERY_RESULT"
        )
        out = cert.verify(contract_override=contract)
        self.assertFalse(out["conditional_universal_program_proof"])
        self.assertFalse(out["facts"]["INTERFACE_EACH_RESULT_FINITE"])

    def test_no_external_instance_credit_is_possible_from_program_proof(self):
        out = cert.verify()
        self.assertEqual(
            out["minimum_missing_fact"],
            "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
            "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2",
        )
        self.assertFalse(out["universal_target_proved"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
