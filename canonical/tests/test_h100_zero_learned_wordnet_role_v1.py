from __future__ import annotations

import unittest
from canonical.runtime.h100_zero_learned_wordnet_role_v1 import (
    classify_lemma_role, induce_roles_from_wordnet,
)

# Minimal WordNet-format fixture tests parser semantics only. Load-bearing frozen
# challenge replay is performed independently against the pinned full WordNet bytes.
INDEX="""determinant n 1 0 1 0 100
consequence n 1 0 1 0 200
entity n 1 0 1 0 300
"""
DATA="""100 00 n 01 determinant 0 000 | a determining causal element or factor
200 00 n 01 consequence 0 000 | something that follows from an action
300 00 n 01 entity 0 000 | that which is perceived to have distinct existence
"""

class H100ZeroLearnedWordNetRoleTests(unittest.TestCase):
    def test_generic_definition_evidence_classifies_fixture(self):
        self.assertEqual(classify_lemma_role("determinant",INDEX,DATA)["role"],"INPUT")
        self.assertEqual(classify_lemma_role("consequence",INDEX,DATA)["role"],"OUTPUT")

    def test_ambiguous_fixture_abstains(self):
        out=induce_roles_from_wordnet("Entities: a, b; entity: c.",noun_index=INDEX,noun_data=DATA)
        self.assertEqual(out["status"],"ABSTAIN_DIRECTION_NOT_IDENTIFIED")

    def test_directional_fixture(self):
        out=induce_roles_from_wordnet("Determinants: a, b; consequence: c.",noun_index=INDEX,noun_data=DATA)
        self.assertEqual(out["status"],"ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"],["a","b"])
        self.assertEqual(out["target"],"c")

if __name__=="__main__":
    unittest.main(verbosity=2)
