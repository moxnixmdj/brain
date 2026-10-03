from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_universal_scope_certificate_v1 import (
 REQUIRED_FACTS,derive_source_facts,prove_from_facts,verify,
)

class Tests(unittest.TestCase):
    def test_exact_live_sources_derive_universal_scope_candidate(self):
        out=verify()
        self.assertTrue(out["universal_scope_proved"],out)
        self.assertTrue(out["scope_atom_satisfied_candidate"])
        self.assertEqual(out["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])
    def test_every_load_bearing_fact_is_present(self):
        f=derive_source_facts()
        self.assertEqual(sorted(k for k in REQUIRED_FACTS if f.get(k) is not True),[],f)
    def test_any_missing_fact_fails_closed(self):
        f={k:True for k in REQUIRED_FACTS}; f[REQUIRED_FACTS[0]]=False
        out=prove_from_facts(f,transport_pass=True,bridge_pass=True,identity_pass=True)
        self.assertFalse(out["universal_scope_proved"])
        self.assertIn(REQUIRED_FACTS[0],out["missing"])
    def test_runtime_bridge_or_transport_failure_blocks_scope(self):
        f={k:True for k in REQUIRED_FACTS}
        for args in ((False,True,True),(True,False,True),(True,True,False)):
            out=prove_from_facts(f,transport_pass=args[0],bridge_pass=args[1],identity_pass=args[2])
            self.assertFalse(out["universal_scope_proved"])

if __name__=="__main__": unittest.main(verbosity=2)
