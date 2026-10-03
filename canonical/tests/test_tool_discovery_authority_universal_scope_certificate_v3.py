from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_authority_universal_scope_certificate_v3 import (
    REQUIRED_FACTS,
    _load,
    _text,
    derive_source_facts,
    prove_from_facts,
    verify,
)


def _ctx():
    return {
        "relation": _load("canonical/governance/TOOL_DISCOVERY_AUTHORITY_COMPLETE_SCOPE_RELATION_V2.json"),
        "protocol": _load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        "v5": _text("canonical/runtime/tool_discovery_authority_complete_candidate_v5.py"),
    }


class ToolDiscoveryAuthorityUniversalScopeV3Tests(unittest.TestCase):
    def test_live_exact_sources_compose_universal_scope_proof(self):
        out=verify()
        self.assertEqual(out["source_blob_drift"],[])
        self.assertTrue(out["universal_scope_proved"],out)
        self.assertTrue(out["scope_atom_satisfied_candidate"],out)
        self.assertEqual(out["interface_basis_kind"],"AUTHORITY_DERIVED_COMPLETE_DISCOVERY_INTERFACE")
        self.assertEqual(out["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

    def test_every_composed_premise_is_load_bearing(self):
        good={name:True for name in REQUIRED_FACTS}
        self.assertTrue(prove_from_facts(good)["universal_scope_proved"])
        for name in REQUIRED_FACTS:
            mutant=dict(good)
            mutant[name]=False
            out=prove_from_facts(mutant)
            self.assertFalse(out["universal_scope_proved"],name)
            self.assertIn(name,out["missing"])

    def test_adapter_mutations_kill_their_premises(self):
        c=_ctx()
        downstream={
            "universal_scope_proved":True,
            "scope_atom_satisfied_candidate":True,
            "basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF",
            "uses_empirical_generalization":False,
        }

        mutant=c["v5"].replace(
            'derived["discovery_registry"] = registry',
            'derived.setdefault("discovery_registry", registry)',
        )
        facts=derive_source_facts(mutant,c["relation"],c["protocol"],downstream)
        self.assertFalse(facts["CALLER_REGISTRY_SUBSET_CANNOT_HIDE_SOURCE"])

        mutant=c["v5"].replace(
            'raw.get("result_semantics") != "EXHAUSTIVE_CURRENT_TOOL_LIST"',
            'False',
        )
        facts=derive_source_facts(mutant,c["relation"],c["protocol"],downstream)
        self.assertFalse(facts["ONLY_EXHAUSTIVE_SOURCE_ACTIONS_ADMITTED"])

        mutant=c["v5"].replace(
            'declared = authority.get("action_manifest_sha256")',
            'declared = expected',
        )
        facts=derive_source_facts(mutant,c["relation"],c["protocol"],downstream)
        self.assertFalse(facts["AUTHORITY_MANIFEST_BINDS_ALL_ACTIONS"])

    def test_downstream_v4_proof_is_load_bearing(self):
        c=_ctx()
        bad={
            "universal_scope_proved":False,
            "scope_atom_satisfied_candidate":False,
            "basis_kind":"UNIVERSAL_FORMAL_SCOPE_PROOF",
            "uses_empirical_generalization":False,
        }
        facts=derive_source_facts(c["v5"],c["relation"],c["protocol"],bad)
        self.assertFalse(facts["DOWNSTREAM_V4_UNIVERSAL_ROUTING_PROOF"])


if __name__=="__main__":
    unittest.main(verbosity=2)
