"""Tests for the typed capability surface.

The surface is DERIVED from the registry, so these tests assert properties of the derivation
rather than a frozen list.  A new capability that cannot be typed must fail here, not ship.
"""
from __future__ import annotations

import unittest

from canonical.runtime import capability_type_surface_v1 as ts


class SurfaceTotalityTests(unittest.TestCase):
    def test_every_capability_has_a_signature(self):
        sigs = ts.signatures()
        self.assertEqual(len(sigs), len(ts.load_registry()))
        self.assertTrue(all(isinstance(v, dict) for v in sigs.values()))

    def test_no_unknown_types(self):
        """An unknown slot would be an untyped hole in the interface; the surface must be total."""
        self.assertEqual(ts.unknowns(), {})

    def test_every_declared_slot_is_read_by_its_adapter_closure(self):
        self.assertEqual(ts.unconsumed_slots(), {})

    def test_signatures_are_derived_not_declared(self):
        """Nothing in the registry carries a hand-written type; the surface computes them."""
        for entry in ts.load_registry().values():
            self.assertNotIn("input_types", entry)
            self.assertNotIn("signature", entry)


class TypeDerivationTests(unittest.TestCase):
    def test_path_morphology(self):
        self.assertEqual(ts.type_of("output_path"), ts.PATH_OUTPUT)
        self.assertEqual(ts.type_of("result_path"), ts.PATH_OUTPUT)
        self.assertEqual(ts.type_of("report_path"), ts.PATH_OUTPUT)
        self.assertEqual(ts.type_of("json_path"), ts.PATH_FILE)
        self.assertEqual(ts.type_of("source_root"), ts.PATH_DIR)
        self.assertEqual(ts.type_of("test_paths"), ts.PATH_LIST)

    def test_scalar_morphology(self):
        self.assertEqual(ts.type_of("x_value"), ts.NUMBER)
        self.assertEqual(ts.type_of("major"), ts.NUMBER)
        self.assertEqual(ts.type_of("authoritative"), ts.BOOL)
        self.assertEqual(ts.type_of("test_argv"), ts.ARGV)
        self.assertEqual(ts.type_of("label"), ts.STRING)

    def test_unknown_is_fail_closed(self):
        self.assertEqual(ts.type_of("totally_made_up_slot"), ts.UNKNOWN)


class ChartTickTypeTests(unittest.TestCase):
    """The defect this surface exists to make impossible.

    `chart.raster.scene_graph.v1` was typed NUMBER_LIST by the plain-goal compiler while its
    axis calibration unpacks (pixel, value) PAIRS.  The router therefore selected the capability
    and execution then failed -- counted as "reachable", never exercised.
    """

    def test_ticks_are_pair_lists_not_number_lists(self):
        sig = ts.signatures()["chart.raster.scene_graph.v1"]
        self.assertEqual(sig["x_ticks"], ts.PAIR_LIST)
        self.assertEqual(sig["y_ticks"], ts.PAIR_LIST)

    def test_the_old_binding_is_rejected(self):
        sig = ts.signatures()["chart.raster.scene_graph.v1"]
        errors = ts.check(sig, {"path": "c.png", "x_ticks": [0, 1, 2], "y_ticks": [0, 5, 10]})
        self.assertTrue(any("x_ticks" in e for e in errors))
        self.assertTrue(any("y_ticks" in e for e in errors))

    def test_correctly_typed_anchors_are_accepted(self):
        sig = ts.signatures()["chart.raster.scene_graph.v1"]
        errors = ts.check(sig, {
            "path": "c.png",
            "x_ticks": [[100, 0.0], [300, 2.0], [500, 4.0]],
            "y_ticks": [[400, 0.0], [240, 2.0], [80, 4.0]],
        })
        self.assertEqual(errors, [])

    def test_pair_list_parser(self):
        self.assertEqual(ts._pair_list("[[100, 0.0], [300, 2.0]]"), [[100, 0.0], [300, 2.0]])

    def test_bare_number_list_is_not_silently_promoted_to_anchors(self):
        self.assertIsNone(ts._pair_list("[0, 1, 2]"))


class TypeCheckTests(unittest.TestCase):
    def setUp(self):
        self.sig = {"path": ts.PATH_FILE, "x_value": ts.NUMBER, "label": ts.STRING}

    def test_well_typed_call_is_accepted(self):
        self.assertEqual(ts.check(self.sig, {"path": "a.png", "x_value": 3.5, "label": "A"}), [])

    def test_missing_slot_is_named(self):
        errors = ts.check(self.sig, {"path": "a.png"})
        self.assertIn("MISSING_SLOT:x_value:NUMBER", errors)
        self.assertIn("MISSING_SLOT:label:STRING", errors)

    def test_undeclared_slot_is_rejected(self):
        self.assertIn("UNDECLARED_SLOT:bogus", ts.check(self.sig, {
            "path": "a.png", "x_value": 1, "label": "A", "bogus": 1}))

    def test_boolean_is_not_a_number(self):
        errors = ts.check({"n": ts.NUMBER}, {"n": True})
        self.assertTrue(any("TYPE_MISMATCH" in e for e in errors))

    def test_unknown_type_accepts_nothing(self):
        self.assertTrue(ts.check({"x": ts.UNKNOWN}, {"x": "anything"}))

    def test_zero_input_capability_is_a_valid_signature(self):
        """No operands is a type, not a defect: () -> Assessment."""
        self.assertEqual(ts.signatures()["terminal.kstar.root.assess.stdlib"], {})


class CompositionTests(unittest.TestCase):
    def test_a_path_producer_satisfies_a_path_consumer(self):
        producer = {"provides": ["archive.tar_gz.create_from_manifest", "output.path"]}
        self.assertTrue(ts.composable(producer, {"archive_path": ts.PATH_FILE}, "archive_path"))

    def test_a_path_producer_does_not_satisfy_a_number_consumer(self):
        producer = {"provides": ["output.path"]}
        self.assertFalse(ts.composable(producer, {"x_value": ts.NUMBER}, "x_value"))

    def test_undeclared_slot_is_not_composable(self):
        self.assertFalse(ts.composable({"provides": ["output.path"]}, {"a": ts.PATH_FILE}, "b"))


class ParserTests(unittest.TestCase):
    def test_number_and_list(self):
        self.assertEqual(ts._number("3.5"), 3.5)
        self.assertEqual(ts._number("-2"), -2)
        self.assertEqual(ts._number_list("[0, 1, 2]"), [0, 1, 2])

    def test_bool_argv_kv(self):
        self.assertIs(ts._bool("true"), True)
        self.assertIs(ts._bool("no"), False)
        self.assertEqual(ts._argv('"python3 -m unittest"'), ["python3", "-m", "unittest"])
        self.assertEqual(ts._kv("x=2, y=3"), {"x": 2, "y": 3})

    def test_json_text_parses_quoted_json(self):
        self.assertEqual(ts._json_text("'{\"a\": 1}'"), {"a": 1})

    def test_json_text_falls_back_to_the_raw_string(self):
        self.assertEqual(ts._json_text("'not json'"), "not json")

    def test_json_text_ignores_unquoted_text(self):
        self.assertIsNone(ts._json_text("{\"a\": 1}"))

    def test_string_unquoted(self):
        self.assertEqual(ts._string("Alpha"), "Alpha")

    def test_path_file_requires_an_extension(self):
        self.assertEqual(ts._path_file("a/b/c.png"), "a/b/c.png")
        self.assertIsNone(ts._path_file("no extension here"))


if __name__ == "__main__":
    unittest.main()
