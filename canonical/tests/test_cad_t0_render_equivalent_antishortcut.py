import unittest

from canonical.runtime.cad_t0_route_specific_candidate_v1 import _texts, _parse_visible


class CadRenderEquivalentAntishortcutTests(unittest.TestCase):
    def _parse(self, svg):
        return _parse_visible(_texts(svg))[0]

    def test_same_line_split_across_text_nodes_is_invariant(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        split = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
        </svg>"""
        self.assertEqual(_texts(original), _texts(split))
        self.assertEqual(self._parse(original)["constraint_graph"], self._parse(split)["constraint_graph"])

    def test_split_inside_numeric_token_is_invariant(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="25">FRONT: rectangle 20.5 mm x 10 mm</text><text x="10" y="45">DEPTH: 5 mm</text></svg>"""
        split = """<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="25">FRONT: rectangle 20.</text><text x="140" y="25">5 mm x 10 mm</text><text x="10" y="45">DEPTH: 5 mm</text></svg>"""
        self.assertEqual(_texts(original), _texts(split))
        self.assertEqual(self._parse(original)["constraint_graph"], self._parse(split)["constraint_graph"])

    def test_source_order_irrelevant_when_geometry_orders_fragments(self):
        split_reordered = """<svg xmlns="http://www.w3.org/2000/svg"><text x="180" y="25"> x 10 mm</text><text x="10" y="45">DEPTH: 5 mm</text><text x="10" y="25">FRONT: rectangle 20 mm</text></svg>"""
        self.assertEqual(_texts(split_reordered), ["FRONT: rectangle 20 mm x 10 mm", "DEPTH: 5 mm"])


if __name__ == "__main__":
    unittest.main()
