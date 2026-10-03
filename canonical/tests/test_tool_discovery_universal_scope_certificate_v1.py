from __future__ import annotations

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


class ToolDiscoveryUniversalScopeCertificateV1Tests(unittest.TestCase):
    def setUp(self):
        self.manifest = text(
            "canonical/runtime/tool_discovery_complete_authority_manifest_v1.py"
        )
        self.v4 = text(
            "canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
        )

    def _base(self):
        facts = derive_source_facts(self.manifest, self.v4)
        facts.update({
            "FROZEN_PROTOCOL_IS_HIDDEN_TOOL_ECOSYSTEM_TRANSFER": True,
            "FROZEN_TARGET_REQUIRES_LEAST_COST_AND_TRANSFER": True,
            "UNIVERSAL_FORMAL_SCOPE_IS_ADMISSIBLE_BASIS": True,
            "PRIOR_V4_REPAIR_INDEPENDENTLY_VERIFIED": True,
        })
        return facts

    def test_live_exact_sources_derive_universal_scope_candidate(self):
        out = verify()
        self.assertTrue(out["universal_scope_proved"], out)
        self.assertTrue(out["scope_atom_satisfied_candidate"])
        self.assertEqual(out["basis_kind"], "UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(
            out["target_predicate"],
            "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        )
        self.assertFalse(out["uses_empirical_generalization"])
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

    def test_partition_exactness_mutation_kills_scope(self):
        mutant = self.manifest.replace(
            "if set(partition_members) != set(ids):",
            "if False:",
            1,
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["MANIFEST_EXACT_DISJOINT_COVER"])
        base = self._base()
        base.update(facts)
        self.assertFalse(prove_from_facts(base)["universal_scope_proved"])

    def test_public_field_boundary_mutation_kills_scope(self):
        mutant = self.manifest.replace(
            '{"tool_id", "cost", "available", "authorized", "epoch", "meta"}',
            '{"tool_id", "cost", "available", "authorized", "epoch", "meta", "capabilities"}',
            1,
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["MANIFEST_PUBLIC_FIELDS_ONLY"])
        base = self._base()
        base.update(facts)
        self.assertFalse(prove_from_facts(base)["universal_scope_proved"])

    def test_discovery_first_mutation_kills_scope(self):
        mutant = self.v4.replace("if sources:", "if False and sources:", 1)
        facts = derive_source_facts(self.manifest, mutant)
        # Structural ordering still exists, but progress/action semantics are
        # intentionally broken and therefore a load-bearing fact must fail.
        self.assertFalse(facts["V4_DISCOVERY_PROGRESS_IS_FINITE"])
        base = self._base()
        base.update(facts)
        self.assertFalse(prove_from_facts(base)["universal_scope_proved"])

    def test_cost_order_mutation_kills_scope(self):
        mutant = self.v4.replace(
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))',
            'tools.sort(key=lambda t:str(t.get("tool_id") or ""))',
            1,
        )
        facts = derive_source_facts(self.manifest, mutant)
        self.assertFalse(facts["V4_GLOBAL_COST_ORDER"])
        base = self._base()
        base.update(facts)
        self.assertFalse(prove_from_facts(base)["universal_scope_proved"])

    def test_current_epoch_filter_mutation_kills_scope(self):
        mutant = self.v4.replace(
            'int(rec.get("epoch",-1))==epochs[tid]',
            'True',
            1,
        )
        facts = derive_source_facts(self.manifest, mutant)
        self.assertFalse(facts["V4_CURRENT_EPOCH_EVIDENCE_ONLY"])
        base = self._base()
        base.update(facts)
        self.assertFalse(prove_from_facts(base)["universal_scope_proved"])

    def test_receipt_binding_mutation_kills_scope(self):
        mutant = self.manifest.replace(
            'if receipt.get("authority_sha256") != public.get("_interface_authority_sha256"):',
            'if False:',
            1,
        )
        facts = derive_source_facts(mutant, self.v4)
        self.assertFalse(facts["DISCOVERY_RECEIPTS_CONTENT_BOUND"])
        base = self._base()
        base.update(facts)
        self.assertFalse(prove_from_facts(base)["universal_scope_proved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
