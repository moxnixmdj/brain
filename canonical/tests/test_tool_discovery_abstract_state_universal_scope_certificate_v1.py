from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_abstract_state_universal_scope_certificate_v1 as p

class Tests(unittest.TestCase):
    def test_source_facts_hold(self):
        facts=p.derive_source_facts()
        self.assertEqual(sorted(k for k,v in facts.items() if not v),[])

    def test_exact_abstract_state_count(self):
        self.assertEqual(p.TOTAL_STATES,104976)

    def test_exhaustive_candidate_equivalence_and_induction(self):
        out=p.exhaustive_check()
        self.assertTrue(out["pass"],out["failures"][:3])
        self.assertEqual(out["checked"],104976)
        self.assertGreater(out["probe_states"],0)
        self.assertGreater(out["select_states"],0)
        self.assertGreater(out["escalate_states"],0)
        self.assertEqual(out["probe_successor_checks"],2*out["probe_states"])

    def test_representative_unsafe_terminal_claims_are_rejected(self):
        values=(None,None,None,None,None,None,None,None)
        self.assertFalse(p._terminal_sound(values,15,{"action":"SELECT","tool_id":"T1"}))
        self.assertFalse(p._terminal_sound(values,15,{"action":"ESCALATE","reason":"x"}))

    def test_full_certificate_is_zero_reality(self):
        out=p.verify()
        self.assertTrue(out["universal_scope_proved"],out)
        self.assertEqual(out["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["uses_empirical_generalization"])
        self.assertEqual(out["terminal_cases_replayed"],0)
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
