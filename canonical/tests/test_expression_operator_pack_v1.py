#!/usr/bin/env python3
"""Pinned tests for the two expression operators and their measured worth."""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import expression_operator_pack_v1 as P

FIXTURE = ROOT / "canonical/tests/fixtures/expression_operator_pack_measure_v1.json"


class MethodRename(unittest.TestCase):
    def test_one_rename_is_learned_and_applied_with_the_new_arity(self):
        mapping = P.method_renames("logger.warn('x')\n", "logger.warning('x')\n")
        self.assertEqual(mapping, {("logger", "warn"): "warning"})
        text, count = P.apply_method_renames("logger.warn('y', extra=1)\n", mapping)
        self.assertEqual(count, 1)
        self.assertIn("logger.warning('y', extra=1)", text)

    def test_a_rename_that_changes_an_argument_is_not_learned(self):
        self.assertEqual(P.method_renames("self.assertEquals(a, b)\n", "self.assertEqual(a, b, msg)\n"), {})

    def test_a_bare_name_is_only_renamed_when_the_target_defines_the_new_name(self):
        """A bare name must also be a documented alias, so the guard is tested with a real pair."""
        mapping = P.method_renames("failUnless(1)\n", "assertTrue(1)\n")
        self.assertEqual(mapping, {(None, "failUnless"): "assertTrue"})
        self.assertEqual(P.apply_method_renames("failUnless(2)\n", mapping), (None, 0))
        text, count = P.apply_method_renames("assertTrue = lambda x: x\nfailUnless(2)\n", mapping)
        self.assertEqual(count, 1)
        self.assertIn("assertTrue(2)", text)

    def test_a_rename_between_two_names_that_are_not_one_function_is_refused(self):
        """The defect this operator shipped with, kept as a test so it cannot come back.

        `assertEquals -> assertEqual` and `yaml.load -> safe_load` have the same shape: one
        attribute renamed, arguments untouched, neither a re-export. Applying the second rewrites
        `yaml.load(h, Loader=yaml.FullLoader)` into `yaml.safe_load(h, Loader=yaml.FullLoader)`,
        which cannot run -- `safe_load` takes no `Loader`. The organ refuses it for that reason,
        and this operator has to refuse it for the same reason.
        """
        before = "import yaml\n\n\ndef s(h):\n    return yaml.load(h)\n"
        after = before.replace("load(", "safe_load(")
        self.assertEqual(P.method_renames(before, after), {},
                         "a rename between two different functions must not be learned")
        # and the same shape, which IS one function, is still learned
        self.assertEqual(P.method_renames("self.assertEquals(a, b)\n", "self.assertEqual(a, b)\n"),
                         {("self", "assertEquals"): "assertEqual"})

    def test_every_learned_rename_is_on_the_documented_alias_list(self):
        from canonical.swe_kernel.taught_actions import kept_under_an_old_name_v1 as kept
        for before, after in (("logger.warn('x')\n", "logger.warning('x')\n"),
                              ("self.assertRaisesRegexp(E, r, f)\n", "self.assertRaisesRegex(E, r, f)\n"),
                              ("self.assertEquals(a, b)\n", "self.assertEqual(a, b)\n")):
            for (_, old), new in P.method_renames(before, after).items():
                self.assertTrue(kept.alias_of(old, new), "%s -> %s is not a kept name" % (old, new))

    def test_a_different_receiver_is_not_renamed(self):
        mapping = P.method_renames("a.warn('x')\n", "a.warning('x')\n")
        self.assertEqual(P.apply_method_renames("b.warn('x')\n", mapping), (None, 0))


class FString(unittest.TestCase):
    def test_a_prefix_concatenation_becomes_one_formatted_value(self):
        self.assertTrue(P.shows_fstring_change("message = 'a' + value\n", "message = f'a{value}'\n"))
        text, count = P.apply_fstring("message = 'b' + other\n")
        self.assertEqual(count, 1)
        self.assertIn("f'b{other}'", text)

    def test_a_suffix_concatenation_keeps_the_order(self):
        text, count = P.apply_fstring("message = value + 's'\n")
        self.assertEqual(count, 1)
        self.assertIn("f'{value}s'", text)

    def test_two_constants_and_containers_are_not_converted(self):
        self.assertEqual(P.apply_fstring("message = 'a' + 'b'\n"), (None, 0))
        self.assertEqual(P.apply_fstring("message = 'a' + (x, y)\n"), (None, 0))

    def test_the_operator_is_gated_on_the_example_showing_an_fstring_change(self):
        before, after = "message = 'a' + value\n", "message = f'a{value}'\n"
        self.assertTrue(P.apply_pack("message = 'b' + other\n", before, after,
                                     ("fstring",))["did"].get("fstring"))
        self.assertIsNone(P.apply_pack("message = 'b' + other\n", "x = 1\n", "x = 2\n",
                                       ("fstring",))["text"])


class Pack(unittest.TestCase):
    def test_rename_applies_independently_of_the_fstring_gate(self):
        before, after = "logger.warn(x)\n", "logger.warning(x)\n"
        got = P.apply_pack("logger.warn(y)\n", before, after, ("rename",))
        self.assertEqual(got["did"], {"rename": 1})
        self.assertIn("logger.warning(y)", got["text"])

    def test_the_pack_writes_nothing_when_no_operator_applies(self):
        self.assertIsNone(P.apply_pack("value = 1\n", "x = 1\n", "y = 2\n")["text"])


class Measured(unittest.TestCase):
    def test_the_recorded_measurement_is_the_one_pinned(self):
        record = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], "EXPRESSION_OPERATOR_PACK_MEASURE_V1")
        self.assertEqual(record["authority"], "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT")
        base = record["summary"]["base"]
        self.assertEqual((base["right"], base["developers_changes"]), (268, 1674))
        self.assertAlmostEqual(base["coverage"], 0.160096, places=6)
        self.assertAlmostEqual(base["precision"], 0.924138, places=6)
        rename = record["summary"]["rename"]
        self.assertEqual(rename["right"], 391)
        self.assertAlmostEqual(rename["coverage"], 0.233572, places=6)
        self.assertAlmostEqual(rename["precision"], 0.946731, places=6)
        fstring = record["summary"]["fstring"]
        self.assertEqual(fstring["right"], 363)
        self.assertAlmostEqual(fstring["precision"], 0.728916, places=6)
        both = record["summary"]["both"]
        self.assertEqual(both["right"], 486)
        self.assertAlmostEqual(both["coverage"], 0.290323, places=6)
        self.assertAlmostEqual(both["precision"], 0.782609, places=6)
        self.assertEqual(len(record["per_pull_request"]), 15)
        rows = record["per_pull_request"]
        self.assertEqual(rows["RedHatInsights/advisor-backend#80"]["rename"]["right"], 55)
        self.assertEqual(rows["torproject/stem#155"]["rename"]["right"], 45)
        self.assertEqual(rows["nipy/nibabel#1609"]["fstring"]["right"], 55)
        self.assertEqual(rows["jupyter/jupyter-sphinx#301"]["fstring"]["right"], 42)
        self.assertEqual(rows["arigatoexpress/Project-Go-Forward#483"]["fstring"]["right"], 41)
        self.assertEqual(rows["kuangjiafa/automagician#55"]["both"]["right"], 0)


if __name__ == "__main__":
    unittest.main()
