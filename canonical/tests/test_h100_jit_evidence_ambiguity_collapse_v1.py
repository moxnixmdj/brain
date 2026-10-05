import unittest

from canonical.runtime import h100_conditional_information_state_bound_v1 as info
from canonical.runtime import h100_jit_lexical_role_v1 as lexical


class JITEvidenceAmbiguityCollapseTests(unittest.TestCase):
    def test_no_evidence_two_world_bound_is_half(self):
        self.assertEqual(info.success_upper_bound([2],0),0.5)

    def test_jit_evidence_partition_allows_zero_bit_perfect_identification(self):
        self.assertEqual(info.success_upper_bound([1,1],0),1.0)
        self.assertEqual(info.minimum_bits_for_target([1,1],1.0),0)

    def test_world_input_resolves_exactly(self):
        knowledge={
            "anchors":{"input":"input","target":"output"},
            "edges":[["novelcue","predictor"],["predictor","input"]],
        }
        out=lexical.induce_roles(
            [
                {"cue":"novelcue","fields":["x"]},
                {"cue":"output","fields":["y"]},
            ],
            knowledge,
        )
        self.assertEqual(out["status"],"ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"],["x"])
        self.assertEqual(out["target"],"y")
        self.assertEqual(out["persistent_learned_bytes"],0)

    def test_world_target_resolves_exactly(self):
        knowledge={
            "anchors":{"input":"input","target":"output"},
            "edges":[["novelcue","response"],["response","output"]],
        }
        out=lexical.induce_roles(
            [
                {"cue":"input","fields":["x"]},
                {"cue":"novelcue","fields":["y"]},
            ],
            knowledge,
        )
        self.assertEqual(out["status"],"ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"],["x"])
        self.assertEqual(out["target"],"y")
        self.assertEqual(out["persistent_learned_bytes"],0)

    def test_information_substitution_delta(self):
        before=info.success_upper_bound([2],0)
        after=info.success_upper_bound([1,1],0)
        self.assertEqual(after-before,0.5)
        self.assertEqual(after,1.0)


if __name__=="__main__":
    unittest.main(verbosity=2)
