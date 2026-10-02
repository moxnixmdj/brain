import unittest

from canonical.runtime.cad_t0_route_specific_candidate_v1 import _parse_visible, _texts


class CadSourceStructureAntishortcutRepairTests(unittest.TestCase):
    ORIGINAL = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm x 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""
    SPLIT_EQUIVALENT = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
    <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
    <text x="10" y="45">DEPTH: 5 mm</text>
    <text x="10" y="65">Three orthographic views; all dimensions nominal.</text>
    </svg>"""

    def test_render_equivalent_node_split_reconstructs_same_rows(self):
        self.assertEqual(_texts(self.ORIGINAL), _texts(self.SPLIT_EQUIVALENT))

    def test_render_equivalent_node_split_preserves_semantic_parse(self):
        a_candidate, a_contract = _parse_visible(_texts(self.ORIGINAL))
        b_candidate, b_contract = _parse_visible(_texts(self.SPLIT_EQUIVALENT))
        self.assertEqual(a_candidate, b_candidate)
        self.assertEqual(a_contract, b_contract)


    def test_split_inside_numeric_token_is_render_equivalent(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20.5 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        </svg>"""
        split = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20.</text><text x="150" y="25">5 mm x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        </svg>"""
        self.assertEqual(_texts(original), _texts(split))
        self.assertEqual(_parse_visible(_texts(original)), _parse_visible(_texts(split)))

    def test_dom_source_order_does_not_override_rendered_x_order(self):
        original = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="10" y="25">FRONT: rectangle 20 mm</text><text x="180" y="25"> x 10 mm</text>
        <text x="10" y="45">DEPTH: 5 mm</text>
        </svg>"""
        reordered = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">
        <text x="180" y="25"> x 10 mm</text><text x="10" y="45">DEPTH: 5 mm</text><text x="10" y="25">FRONT: rectangle 20 mm</text>
        </svg>"""
        self.assertEqual(_texts(original), _texts(reordered))
        self.assertEqual(_parse_visible(_texts(original)), _parse_visible(_texts(reordered)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
