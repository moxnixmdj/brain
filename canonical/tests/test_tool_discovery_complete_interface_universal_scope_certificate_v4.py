from __future__ import annotations
import unittest
from pathlib import Path

from canonical.runtime.tool_discovery_complete_interface_universal_scope_certificate_v4 import (
    REQUIRED_FACTS, derive_source_facts, prove_from_facts
)

ROOT=Path(__file__).resolve().parents[2]


class Tests(unittest.TestCase):
    def test_current_candidate_structural_facts_close(self):
        text=(ROOT/"canonical/runtime/tool_discovery_complete_interface_candidate_v4.py").read_text()
        facts=derive_source_facts(text)
        self.assertEqual(sorted(k for k,v in facts.items() if not v),[])
        out=prove_from_facts(facts)
        self.assertTrue(out["universal_scope_proved"])
        self.assertEqual(out["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["uses_empirical_generalization"])

    def test_each_missing_premise_fails_closed(self):
        full={x:True for x in REQUIRED_FACTS}
        for name in REQUIRED_FACTS:
            mutated=dict(full); mutated[name]=False
            out=prove_from_facts(mutated)
            self.assertFalse(out["universal_scope_proved"],name)
            self.assertIn(name,out["missing"])

    def test_scope_atom_is_exact_tool_discovery_atom(self):
        out=prove_from_facts({x:True for x in REQUIRED_FACTS})
        self.assertEqual(out["target_predicate"],"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertIn("TOOL_DISCOVERY_PROTOCOL",out["scope_atom"])

if __name__=="__main__":
    unittest.main(verbosity=2)
