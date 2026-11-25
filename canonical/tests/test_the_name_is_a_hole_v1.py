"""Pure checks for the frame-guided name-hole generator."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import the_name_is_a_hole_v1 as name  # noqa: E402


SOURCE = '''from __future__ import annotations

def build(field_name, attr_name, partial):
    prefix = field_name + "."
    return [p for p in partial if p.startswith(prefix)]
'''


class NameHoleTests(unittest.TestCase):
    def test_instrument_compiles_and_shifts_by_one_line(self):
        instrumented, offset = name.instrument(SOURCE, name.static_name_lines(SOURCE))
        compile(instrumented, "<probe>", "exec")
        self.assertEqual(offset, 1)
        self.assertIn("import brain_recorder as _br", instrumented)

    def test_trace_frame_maps_to_source_line(self):
        scope = {"field_name": {"str": "homeAddress"}, "attr_name": {"str": "address"}}
        holes = name.name_holes(SOURCE, {"4": scope})
        self.assertIn("field_name", [hole["name"] for hole in holes])
        self.assertEqual([h["line"] for h in holes if h["name"] == "field_name"], [4])

    def test_alignment_prefers_a_value_the_current_one_cannot_explain(self):
        specs = ["address.zip_code", "homeAddress"]
        self.assertGreater(name.alignment("address", "homeAddress", specs),
                           name.alignment("Springfield", "homeAddress", specs))
        self.assertEqual(name.alignment("homeAddress", "homeAddress", specs), -1000)

    def test_candidates_come_from_the_observed_frame_only(self):
        hole = {"name": "field_name", "value": "homeAddress",
                "scope": {"attr_name": {"str": "address"}, "partial": {"str": "('address.zip_code',)"}}}
        found = [c[0] for c in name.candidates(hole, ["address.zip_code"])]
        self.assertIn("attr_name", found)
        self.assertNotIn("field_name", found)

    def test_spec_strings_read_the_failing_test_not_the_diff(self):
        text = '''def test_x():\n    assert load(partial=("address.zip_code",)) == "Springfield"\n'''
        specs = name.spec_strings(text, "tests/test_x.py::Test::test_x[address]")
        self.assertIn("address.zip_code", specs)
        self.assertIn("Springfield", specs)


if __name__ == "__main__":
    unittest.main()
