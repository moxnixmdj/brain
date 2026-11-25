"""Inverse-pair completion, tested on the case that motivated it.

`real_fix_pairs_20261119_V1.json` has 87 execution-verified fixes; 54% need an
INSERT the existing grammar cannot perform, and 12 of those invent a callable.
Those callables come in inverse pairs, and a pair is constrained by an executable
property. These tests check that the constraint is real and that the refusals are
not softened to make the numbers look better.
"""
from __future__ import annotations

import unittest

from canonical.swe_kernel import inverse_completion_v1 as ic


class DetectPairTests(unittest.TestCase):
    def test_dunder_writer_finds_its_reader(self):
        self.assertEqual("__setstate__", ic.detect_pair("__getstate__")["missing"])
        self.assertEqual("__setstate__", ic.detect_pair("__reduce_ex__")["missing"])

    def test_named_stem_pair_is_recognised(self):
        """_point_state / _point_from_state both appear in the real corpus."""
        self.assertEqual("_point_from_state", ic.detect_pair("_point_state")["missing"])
        self.assertEqual(
            "_intervals_from_state", ic.detect_pair("_intervals_state")["missing"]
        )

    def test_a_helper_with_no_inverse_is_not_pretended_into_one(self):
        """_splice_operand and _join_markers are the real 12-case pair that is NOT
        an inverse pair; claiming otherwise would inflate the reachable set."""
        self.assertIsNone(ic.detect_pair("_splice_operand"))
        self.assertIsNone(ic.detect_pair("_join_markers"))


class ReaderShapeTests(unittest.TestCase):
    def test_arity_is_read_off_the_writer_not_chosen(self):
        out = ic.synthesise_reader(
            "__getstate__", [("x>=1", True, (True, None)), ("y", None, (False, False))]
        )
        self.assertEqual("PASS__READER_DETERMINED", out["status"])
        self.assertEqual(3, out["shape"]["arity"])

    def test_optionality_is_not_mistaken_for_a_shape_change(self):
        """bool | None is one field. An earlier version refused this and was wrong."""
        out = ic.synthesise_reader("__getstate__", [("a", True), ("b", None)])
        self.assertEqual("PASS__READER_DETERMINED", out["status"])
        self.assertEqual(2, out["shape"]["arity"])

    def test_ragged_arity_refuses_because_no_single_reader_fits(self):
        out = ic.synthesise_reader("__getstate__", [("a", True), ("b", True, None)])
        self.assertEqual("REFUSED__WRITER_NOT_DETERMINED", out["status"])

    def test_mapping_payload_names_the_fields(self):
        out = ic.synthesise_reader(
            "__getstate__", [{"name": "a", "n": 1}, {"name": "b", "n": 2}]
        )
        self.assertEqual("PASS__READER_DETERMINED", out["status"])
        self.assertEqual(["n", "name"], out["shape"]["field_names"])

    def test_no_payload_refuses(self):
        self.assertEqual(
            "REFUSED__WRITER_NOT_DETERMINED",
            ic.synthesise_reader("__getstate__", [])["status"],
        )


class RefusalTests(unittest.TestCase):
    def test_unknown_name_refuses_rather_than_inventing(self):
        out = ic.synthesise_reader("_join_markers", [("a",)])
        self.assertEqual("REFUSED__NO_INVERSE_CONSTRAINT", out["status"])
        self.assertIsNone(out["source"])

    def test_the_claim_is_bounded(self):
        out = ic.synthesise_reader("__getstate__", [("a", 1)])
        self.assertEqual("THE_SHAPE_ONE_READER_MUST_ACCEPT", out["shape"]["claim"])
        self.assertEqual("A_CORRECT_READER_WAS_FOUND", out["not_claimed"])
        self.assertEqual("NONE", out["authority"])


class RoundtripPropertyTests(unittest.TestCase):
    """The property is the only thing allowed to accept a reader."""

    class Req:
        def __init__(self, name, prereleases, overrides):
            self.name, self.prereleases, self.overrides = name, prereleases, overrides

        def __eq__(self, other):
            return vars(self) == vars(other)

    def _samples(self):
        return [
            self.Req("x>=1", True, (True, None)),
            self.Req("y", None, (False, False)),
        ]

    def test_a_correct_reader_has_zero_residual(self):
        samples = self._samples()

        def save(s):
            return (s.name, s.prereleases, s.overrides)

        def load(payload):
            out = self.Req.__new__(self.Req)
            out.name, out.prereleases, out.overrides = payload
            return out

        result = ic.roundtrip_residual(save, load, samples)
        self.assertTrue(result["holds"])
        self.assertEqual(0, result["residual"])

    def test_the_pre_fix_reader_is_caught(self):
        """The bug a03bde12 actually fixed: the loader dropped the third element."""
        samples = self._samples()

        def save(s):
            return (s.name, s.prereleases, s.overrides)

        def load(payload):
            out = self.Req.__new__(self.Req)
            out.name, out.prereleases, out.overrides = payload[0], payload[1], None
            return out

        result = ic.roundtrip_residual(save, load, samples)
        self.assertFalse(result["holds"])
        self.assertEqual(2, result["residual"])
        self.assertEqual("mismatch", result["failures"][0]["stage"])

    def test_a_list_payload_that_compares_equal_is_still_a_type_change(self):
        result = ic.roundtrip_residual(lambda x: [x], lambda p: tuple(p), [(1, 2)])
        self.assertFalse(result["holds"])

    def test_a_writer_that_raises_is_reported_not_crashed(self):
        def save(_):
            raise RuntimeError("cannot write")

        result = ic.roundtrip_residual(save, lambda p: p, [1])
        self.assertEqual("save", result["failures"][0]["stage"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
