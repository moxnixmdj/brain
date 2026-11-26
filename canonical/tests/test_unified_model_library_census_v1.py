"""Guard the library census: the declared capability count is not the library.

Every assertion here pins a number measured on 2026-11-24 by
``canonical/tools/unified_model_library_census_v1.py``. They exist because the artifact's own
`counts` block reports 447 capabilities and that figure had been read as the library's size in
planning documents, while 176 of those ids resolve to a single 7,370-byte adapter file.
"""
from __future__ import annotations

import pathlib
import unittest

from canonical.tools.unified_model_library_census_v1 import (
    askable_phrases,
    census,
    docstring_sentence,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestAskablePhrases(unittest.TestCase):
    def test_a_slug_is_not_a_request(self):
        self.assertEqual(askable_phrases({"triggers": ["report.call_graph"]}), [])

    def test_a_shouted_status_is_not_a_request(self):
        self.assertEqual(
            askable_phrases({"triggers": ["PASS__EVERY_LIVE_OWNED_CAPABILITY"]}), []
        )

    def test_a_version_marker_is_not_a_request(self):
        self.assertEqual(askable_phrases({"triggers": ["v1"]}), [])

    def test_a_phrase_is_a_request(self):
        self.assertEqual(
            askable_phrases({"triggers": ["extract text from a pdf document"]}),
            ["extract text from a pdf document"],
        )


class TestMeasuredLibraryShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A tiny sample: this class pins the SHAPE, not the recall curve.
        cls.report = census(REPO_ROOT, sample=2, trials=1)

    def test_declared_count_is_not_the_distinct_count(self):
        report = self.report
        self.assertGreater(report["declared_capabilities"], 400)
        self.assertLess(
            report["distinct_implementations"],
            report["declared_capabilities"] * 0.70,
            "the library collapsed into fewer distinct implementations than expected; "
            "if this ever becomes false, the duplicate registration was cleaned up and the "
            "planning documents should say so",
        )

    def test_one_file_is_registered_under_many_ids(self):
        report = self.report
        self.assertGreaterEqual(
            report["largest_duplicate_group"]["ids"], 100,
            "expected one adapter file registered under >100 ids",
        )

    def test_most_capabilities_can_now_be_asked_for_in_words(self):
        """Changed on 2026-11-24: the compiler now carries each module's docstring sentence.

        This test previously asserted the defect -- that under 25% of the library was askable.
        The fix landed (L1), so it now asserts the property we want, at the level measured:
        211 of 447 declarations carry a phrase a caller could say, up from 49.
        """
        report = self.report
        self.assertGreaterEqual(
            report["askable_in_words"], 150,
            "askable share collapsed; the compiler stopped carrying descriptions",
        )

    def test_capabilities_carry_the_description_they_are_found_by(self):
        report = self.report
        self.assertGreaterEqual(
            report["described_as"], 150,
            "fewer capabilities carry a described_as field than the 188 measured",
        )
        # Self-location against the full library is lower than the isolated 98.9% because
        # sibling capabilities of one family now compete on shared family vocabulary.
        self.assertGreaterEqual(
            report["self_locating"]["share"], 0.40,
            f"self-location fell to {report['self_locating']['share']:.2f}",
        )

    def test_docstrings_are_mostly_present_but_generic(self):
        report = self.report
        self.assertGreater(report["with_docstring"], 300)
        self.assertGreater(
            report["generic_docstrings"], 100,
            "the templated adapter docstring is what makes 175 modules indistinguishable",
        )


class TestDocstringExtraction(unittest.TestCase):
    def test_reads_the_first_sentence_of_a_real_module(self):
        rec = {"provenance": {"source_path": "canonical/runtime/learn_or_read_v1.py"}}
        sentence = docstring_sentence("learn_or_read_v1", rec, REPO_ROOT)
        self.assertIsNotNone(sentence)
        self.assertIsInstance(sentence, str)
        self.assertGreater(len(sentence), 20)


if __name__ == "__main__":
    unittest.main()
