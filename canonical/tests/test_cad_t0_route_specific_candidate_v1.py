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


    def test_render_equivalent_svg_text_node_split_preserves_semantics(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        split_equivalent = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        from canonical.runtime.cad_t0_route_specific_candidate_v1 import _texts, _parse_visible

        original_candidate, original_contract = _parse_visible(_texts(original))
        split_candidate, split_contract = _parse_visible(_texts(split_equivalent))

        self.assertEqual(_texts(split_equivalent)[0], "FRONT: rectangle 20 mm x 10 mm")
        self.assertEqual(split_candidate, original_candidate)
        self.assertEqual(split_contract, original_contract)


if __name__ == "__main__":
    unittest.main()
