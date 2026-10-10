from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FABRIC = ROOT / "canonical/runtime/unified_cognitive_fabric_v1.py"


class UnifiedFabricCertifiedRouteSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FABRIC.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_static_constructor_import_is_present(self):
        self.assertIn(
            "from canonical.runtime import certified_reached_escape_state_constructor_v1 as certified_reached_escape_state",
            self.source,
        )

    def test_engine_descriptor_names_constructor_not_raw_kernel(self):
        self.assertIn(
            '"REACHED_ESCAPE_STATE": "certified_reached_escape_state_constructor_v1.construct"',
            self.source,
        )
        self.assertNotIn(
            '"REACHED_ESCAPE_STATE": "reached_escape_state_kernel_v1.evaluate"',
            self.source,
        )

    def test_reached_escape_dispatch_calls_constructor(self):
        found = False
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.If):
                continue
            text = ast.get_source_segment(self.source, node.test) or ""
            if 'mode == "REACHED_ESCAPE_STATE"' not in text:
                continue
            body = "\n".join(
                ast.get_source_segment(self.source, item) or ""
                for item in node.body
            )
            self.assertIn(
                "certified_reached_escape_state.construct(payload)",
                body,
            )
            self.assertNotIn("reached_escape_state.evaluate(payload)", body)
            found = True
            break
        self.assertTrue(found, "REACHED_ESCAPE_STATE dispatch branch not found")

    def test_raw_kernel_import_is_not_used_by_fabric_dispatch(self):
        self.assertNotIn(
            "from canonical.runtime import reached_escape_state_kernel_v1 as reached_escape_state",
            self.source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
