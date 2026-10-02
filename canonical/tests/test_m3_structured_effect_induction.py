import unittest
from canonical.runtime.m3_structured_effect_induction import Observation, induce_effect_model

class Tests(unittest.TestCase):
    def test_argument_effect(self):
        out=induce_effect_model([
            Observation({"v":1},{"x":0},{"x":1}),
            Observation({"v":2},{"x":9},{"x":2}),
        ])
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["effects"][0]["kind"],"SET_FROM_ARG")

    def test_fixed_delta(self):
        out=induce_effect_model([
            Observation({},{"n":1},{"n":3}),
            Observation({},{"n":5},{"n":7}),
        ])
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["effects"][0]["kind"],"ADD_CONSTANT")

    def test_irregular_change(self):
        out=induce_effect_model([
            Observation({},{"x":1},{"x":2}),
            Observation({},{"x":3},{"x":9}),
        ])
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["unresolved_changed_keys"],["x"])

if __name__=="__main__":
    unittest.main()
