from __future__ import annotations

import unittest

from canonical.runtime.semantic_extractive_summarizer_v1 import (
    ExtractiveSummaryError,
    summarize,
)


class SemanticExtractiveSummarizerV1Tests(unittest.TestCase):
    def test_selected_sentences_are_exact_source_spans(self):
        source = (
            "Mars is the fourth planet from the Sun. "
            "It has two small moons. "
            "Mars has a thin atmosphere and an iron-rich surface. "
            "Many spacecraft have studied Mars."
        )
        out = summarize(source, 2)
        self.assertEqual(out["status"], "PASS__SOURCE_PRESERVING_EXTRACTIVE_SUMMARY")
        self.assertEqual(out["selected_sentence_count"], 2)
        self.assertEqual(out["source_sentence_count"], 4)
        self.assertTrue(out["source_preservation_proved"])
        for item in out["selected_spans"]:
            self.assertEqual(source[item["start"]:item["end"]], item["text"])
            self.assertIn(item["text"], source)

    def test_is_deterministic(self):
        source = (
            "Alpha systems reduce latency. "
            "Beta systems increase latency. "
            "Alpha systems also reduce queue depth."
        )
        self.assertEqual(summarize(source, 1), summarize(source, 1))

    def test_short_source_is_returned_without_invention(self):
        source = "Only one source sentence is present."
        out = summarize(source, 3)
        self.assertEqual(out["summary"], source)
        self.assertEqual(out["selected_sentence_count"], 1)
        self.assertEqual(out["compressed_sentence_count"], 0)

    def test_newline_boundaries_preserve_exact_text(self):
        source = "First fact is here.\nSecond fact is here.\nThird fact is different."
        out = summarize(source, 2)
        for item in out["selected_spans"]:
            self.assertEqual(source[item["start"]:item["end"]], item["text"])

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaisesRegex(ExtractiveSummaryError, "TEXT_REQUIRED"):
            summarize("", 2)
        with self.assertRaisesRegex(ExtractiveSummaryError, "MAX_SENTENCES_OUT_OF_RANGE"):
            summarize("A sentence.", 0)
        with self.assertRaisesRegex(ExtractiveSummaryError, "MAX_SENTENCES_OUT_OF_RANGE"):
            summarize("A sentence.", 21)


if __name__ == "__main__":
    unittest.main(verbosity=2)
