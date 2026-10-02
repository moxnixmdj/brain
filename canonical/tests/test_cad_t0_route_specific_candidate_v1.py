import unittest

from canonical.runtime.cad_t0_geometry_population import generate_case, public_case
from canonical.runtime.cad_t0_oracle_adapter import prepare_hidden_case, observe_candidate
from canonical.runtime.cad_t0_multiplex_scorer import score_case
from canonical.runtime.cad_t0_route_specific_candidate_v1 import solve_with_result


class CadT0RouteSpecificCandidateTests(unittest.TestCase):
    def _run(self, seed, slot):
        hidden = generate_case(seed, slot)
        public = public_case(hidden)
        candidate, result = solve_with_result(public)
        prepared = prepare_hidden_case(hidden)
        observation = observe_candidate(prepared, candidate, result)
        verdict = score_case(prepared, candidate, observation)
        self.assertTrue(verdict["pass"], {
            "slot": slot,
            "family": hidden["_oracle"]["family"],
            "candidate": candidate,
            "observation": observation,
            "verdict": verdict,
        })
        self.assertNotIn("_oracle", candidate)

    def test_all_eight_frozen_geometry_families(self):
        for slot in range(8):
            with self.subTest(slot=slot):
                self._run(123456789 + slot * 101, slot)

    def test_second_cycle_all_families(self):
        for slot in range(8, 16):
            with self.subTest(slot=slot):
                self._run(987654321 + slot * 313, slot)


if __name__ == "__main__":
    unittest.main()
