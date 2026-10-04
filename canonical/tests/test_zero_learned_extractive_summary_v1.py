from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime.zero_learned_extractive_summary_v1 import (
    ExtractiveSummaryError,
    summarize,
)


class ZeroLearnedExtractiveSummaryTests(unittest.TestCase):
    def setUp(self):
        self.source = (
            "Solar power converts sunlight into electricity. "
            "Solar panels now supply power to homes and businesses in many regions. "
            "Falling equipment costs have accelerated solar adoption. "
            "Grid storage helps balance solar generation after sunset. "
            "Policy and transmission constraints still affect deployment."
        )

    def test_pass_is_strict_compression_and_verbatim_source_subset(self):
        out = summarize(self.source, compression_ratio=0.4, max_sentences=2)
        self.assertEqual(out["status"], "PASS", out)
        self.assertLess(len(out["response"].encode()), len(self.source.encode()))
        self.assertTrue(out["all_output_sentences_verbatim_source_spans"])
        expected = []
        prior_end = -1
        for row in out["proof"]:
            a, b = row["source_start"], row["source_end"]
            self.assertGreaterEqual(a, prior_end)
            span = self.source[a:b]
            self.assertEqual(span, row["source_span"])
            self.assertEqual(
                row["source_span_sha256"],
                sha256(span.encode("utf-8")).hexdigest(),
            )
            expected.append(span)
            prior_end = b
        self.assertEqual(out["response"], " ".join(expected))

    def test_deterministic(self):
        a = summarize(self.source, compression_ratio=0.4, max_sentences=2)
        b = summarize(self.source, compression_ratio=0.4, max_sentences=2)
        self.assertEqual(a, b)

    def test_repeated_salient_terms_increase_selection_signal(self):
        source = (
            "Background details introduce the report. "
            "Battery storage stabilizes renewable grids and battery storage shifts solar energy into evening demand. "
            "A side note discusses office renovations. "
            "Battery storage can also reduce renewable curtailment when the grid is constrained."
        )
        out = summarize(source, compression_ratio=0.25, max_sentences=1)
        self.assertEqual(out["status"], "PASS", out)
        self.assertIn("Battery storage", out["response"])

    def test_single_sentence_fails_closed(self):
        out = summarize("Only one meaningful sentence is available.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["error"], "INSUFFICIENT_MULTI_SENTENCE_SOURCE")
        self.assertIsNone(out["response"])

    def test_short_fragments_do_not_create_fake_summary_authority(self):
        out = summarize("A. B. A substantive sentence is present.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["terminal_authority"])

    def test_quoted_sentence_boundaries_preserve_exact_source_bytes(self):
        source = (
            'Ada said, "The bridge is stable." '
            "The inspection found no visible cracking. "
            "A second inspection is scheduled next month."
        )
        out = summarize(source, compression_ratio=0.34, max_sentences=1)
        self.assertEqual(out["status"], "PASS", out)
        row = out["proof"][0]
        self.assertEqual(source[row["source_start"]:row["source_end"]], row["source_span"])

    def test_invalid_bounds_fail(self):
        with self.assertRaises(ExtractiveSummaryError):
            summarize(self.source, compression_ratio=1)
        with self.assertRaises(ExtractiveSummaryError):
            summarize(self.source, compression_ratio=0)
        with self.assertRaises(ExtractiveSummaryError):
            summarize(self.source, max_sentences=0)

    def test_zero_learned_and_zero_external_provider_accounting(self):
        out = summarize(self.source)
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["persistent_learned_bytes"], 0)
        self.assertEqual(out["external_frontier_model_calls"], 0)
        self.assertEqual(out["external_learned_capability_calls"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["terminal_cases_used"], 0)
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
