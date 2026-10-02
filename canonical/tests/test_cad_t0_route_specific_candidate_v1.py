import unittest

from canonical.runtime.cad_t0_geometry_population import generate_case, public_case
from canonical.runtime.cad_t0_oracle_adapter import prepare_hidden_case, observe_candidate
from canonical.runtime.cad_t0_multiplex_scorer import score_case
from canonical.runtime.cad_t0_route_specific_candidate_v1 import solve_with_result, _texts, _parse_visible


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


class CadT0RenderEquivalentMutationSuiteTests(unittest.TestCase):
    ORIGINAL = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""

    def _semantic(self, svg):
        rows = _texts(svg)
        return _parse_visible(rows)

    def test_same_y_node_split_preserves_rows_and_semantics(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(_texts(self.ORIGINAL), _texts(mutated))
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))

    def test_word_split_without_source_whitespace_preserves_semantics(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rect</text><text x="85" y="25">angle 20 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))

    def test_same_line_source_order_reversal_uses_rendered_x_order(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="180" y="25"> x 10 mm</text><text x="10" y="25">FRONT: rectangle 20 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(_texts(self.ORIGINAL), _texts(mutated))
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))

    def test_nested_tspan_and_wrapper_do_not_change_inference(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <g data-irrelevant="wrapper">
          <text y="25" x="10">FRONT: rectangle <tspan>20 mm x 10 mm</tspan></text>
        </g>
        <text y="45" x="10">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))

    def test_attribute_quote_order_comment_and_whitespace_changes_are_inert(self):
        mutated = """<svg height='120' width='640' xmlns='http://www.w3.org/2000/svg'>
        <!-- source-only comment -->
        <text y='25' data-x='ignore' x='10'>  FRONT:   rectangle 20 mm x 10 mm  </text>
        <text y='45' x='10'>DEPTH:&#32;5 mm</text>
        <text y='65' x='10'>Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))

    def test_rendered_line_dom_order_change_does_not_change_semantic_parse(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
        </svg>"""
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))

    def test_equivalent_numeric_coordinate_spellings_preserve_grouping(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10.0" y="25.0000000001">FRONT: rectangle 20 mm</text>
        <text x="180.0" y="25"> x 10 mm</text>
        <text x="10.000" y="45.0">DEPTH: 5 mm</text>
        <text x="10" y="65.000">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(self._semantic(self.ORIGINAL), self._semantic(mutated))


if __name__ == "__main__":
    unittest.main()
