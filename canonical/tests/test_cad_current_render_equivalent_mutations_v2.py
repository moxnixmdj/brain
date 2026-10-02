import unittest

from canonical.runtime.cad_t0_route_specific_candidate_v1 import _parse_visible, _texts


class CadCurrentRenderEquivalentMutationTests(unittest.TestCase):
    ORIGINAL = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""

    def semantic(self, svg):
        return _parse_visible(_texts(svg))

    def test_same_y_split(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text></svg>"""
        self.assertEqual(_texts(self.ORIGINAL), _texts(mutated))
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))

    def test_word_split(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rect</text><text x="85" y="25">angle 20 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text></svg>"""
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))

    def test_numeric_token_split(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="25">FRONT: rectangle 20.5 mm x 10 mm</text><text x="10" y="45">DEPTH: 5 mm</text></svg>"""
        mutated = """<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="25">FRONT: rectangle 20.</text><text x="150" y="25">5 mm x 10 mm</text><text x="10" y="45">DEPTH: 5 mm</text></svg>"""
        self.assertEqual(_texts(original), _texts(mutated))
        self.assertEqual(self.semantic(original), self.semantic(mutated))

    def test_same_line_source_reversal(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="180" y="25"> x 10 mm</text><text x="10" y="25">FRONT: rectangle 20 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text></svg>"""
        self.assertEqual(_texts(self.ORIGINAL), _texts(mutated))
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))

    def test_nested_tspan_wrapper(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120"><g data-irrelevant="wrapper">
        <text y="25" x="10">FRONT: rectangle <tspan>20 mm x 10 mm</tspan></text></g>
        <text y="45" x="10">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text></svg>"""
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))

    def test_attributes_comments_whitespace_entities(self):
        mutated = """<svg height='120' width='640' xmlns='http://www.w3.org/2000/svg'><!-- irrelevant -->
        <text y='25' data-x='ignore' x='10'>  FRONT:   rectangle 20 mm x 10 mm  </text>
        <text y='45' x='10'>DEPTH:&#32;5 mm</text>
        <text y='65' x='10'>Three orthographic views; all dimensions nominal.</text></svg>"""
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))

    def test_line_dom_order(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text></svg>"""
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))

    def test_coordinate_spellings(self):
        mutated = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10.0" y="25.0000000001">FRONT: rectangle 20 mm</text><text x="180.0" y="25"> x 10 mm</text>
        <text x="10.000" y="45.0">DEPTH: 5 mm</text>
        <text x="10" y="65.000">Three orthographic views; all dimensions nominal.</text></svg>"""
        self.assertEqual(self.semantic(self.ORIGINAL), self.semantic(mutated))


if __name__ == "__main__":
    unittest.main(verbosity=2)
