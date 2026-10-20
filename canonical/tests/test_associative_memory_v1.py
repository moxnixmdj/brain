#!/usr/bin/env python3
"""Tests for earned-importance associative memory.

The owner asked for a creature that "memorizes and retrieves what is
important" -- explicitly NOT a strict program. The property that makes this
memory rather than a ranked list is the one under test:

    nothing declares what is important. Importance is earned by helping.

So a memory that returns the most textually similar entry is WRONG. It has to
return the one that mattered -- and it has to discover which one that was.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest

from canonical.runtime import associative_memory_v1 as mem


class MemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except OSError:
            pass

    # --- associative retrieval -------------------------------------------------

    def test_partial_cue_recalls_without_the_key(self):
        mem.remember("the barcoded label printer needs a PNG at 300dpi",
                     kind="fact", tags=["printer"], path=self.path)
        hits = mem.recall("barcode printer", path=self.path)
        self.assertEqual(len(hits), 1)
        self.assertIn("300dpi", hits[0]["content"])

    def test_no_exact_match_still_recalls(self):
        """A lookup table fails here; memory must not."""
        mem.remember("sqlite tables are created from json records",
                     kind="fact", path=self.path)
        self.assertTrue(mem.recall("making a database from JSON", path=self.path))

    def test_inflections_meet(self):
        """'decoding' must recall a procedure that says 'decode'.

        Without stem matching the two share no term at all and the memory
        cannot associate a problem with the lesson that solves it -- which is
        the one job it has.
        """
        eid = mem.remember("install zbar-tools then decode with zbarimg --raw",
                           kind="procedure", path=self.path)
        for cue in ("decoding a barcode image", "decoded the barcode",
                    "decode barcode"):
            hits = mem.recall(cue, path=self.path)
            self.assertEqual([h["id"] for h in hits], [eid], f"failed on {cue!r}")

    def test_filler_words_do_not_create_relevance(self):
        """Shared grammar is not shared meaning."""
        mem.remember("zint encodes barcodes to png", path=self.path)
        self.assertEqual(mem.recall("how to bake sourdough bread",
                                    path=self.path), [])

    def test_empty_cue_returns_nothing(self):
        mem.remember("something", path=self.path)
        self.assertEqual(mem.recall("", path=self.path), [])

    def test_unrelated_cue_does_not_recall(self):
        mem.remember("zint encodes barcodes to png", path=self.path)
        self.assertEqual(mem.recall("how to bake sourdough bread", path=self.path), [])

    def test_tag_only_cue_works(self):
        mem.remember("a fact about nothing in particular", tags=["zbar"],
                     path=self.path)
        self.assertTrue(mem.recall("zbar", path=self.path))

    # --- importance is earned, not declared ------------------------------------

    def test_helping_beats_being_similar(self):
        """The central property.

        The first entry is a better textual match for the cue. The second has
        actually helped, repeatedly. A search engine returns the first. A
        creature's memory returns the second -- and nobody told it to.
        """
        similar = mem.remember("zint writes png barcode images", kind="fact",
                               path=self.path)
        useful = mem.remember("barcode png dpi output flag contract", kind="hint",
                              path=self.path)
        for _ in range(5):
            mem.recall("barcode png", path=self.path)
            mem.credit(useful, helped=True, path=self.path)

        hits = mem.recall("barcode png output", path=self.path)
        self.assertEqual([h["id"] for h in hits], [useful, similar])

    def test_retrieval_without_credit_is_only_familiarity(self):
        """Retrieved constantly, never helped: it should NOT become important."""
        familiar = mem.remember("png barcode output", path=self.path)
        helpful = mem.remember("png barcode output flag", path=self.path)
        for _ in range(20):
            mem.recall("barcode png output", path=self.path)   # no credit given
        for _ in range(2):
            mem.recall("barcode png output", path=self.path)
            mem.credit(helpful, helped=True, path=self.path)

        hits = mem.recall("barcode png output", path=self.path)
        self.assertEqual(hits[0]["id"], helpful)

    def test_being_wrong_lowers_importance(self):
        good = mem.remember("barcode png output correct", path=self.path)
        bad = mem.remember("barcode png output wrong", path=self.path)
        for _ in range(3):
            mem.recall("barcode png output", path=self.path)
            mem.credit(bad, helped=False, path=self.path)
        mem.recall("barcode png output", path=self.path)
        mem.credit(good, helped=True, path=self.path)

        hits = mem.recall("barcode png output", path=self.path)
        self.assertEqual(hits[0]["id"], good)
        self.assertLess(hits[-1]["importance"], 1.0)

    def test_credit_on_unknown_entry_is_false(self):
        self.assertFalse(mem.credit("nope", path=self.path))

    # --- decay and forgetting --------------------------------------------------

    def test_disuse_decays_importance(self):
        eid = mem.remember("png barcode output", path=self.path)
        mem.recall("barcode png", path=self.path)
        mem.credit(eid, helped=True, path=self.path)
        before = mem.recall("barcode png output", path=self.path)[0]["importance"]

        state = mem._load(self.path)
        state["entries"][eid]["last_accessed"] -= 30 * 86400
        mem._save(state, self.path)

        after = mem.recall("barcode png output", path=self.path)[0]["importance"]
        self.assertLess(after, before)
        self.assertGreater(after, 0.0)  # decayed, not forgotten outright

    def test_forgetting_drops_the_least_important_not_the_oldest(self):
        """Evicting oldest-first would throw away everything learned early."""
        old_but_vital = mem.remember("png barcode output essential", path=self.path)
        for _ in range(5):
            mem.recall("barcode png essential", path=self.path)
            mem.credit(old_but_vital, helped=True, path=self.path)
        for i in range(6):
            mem.remember(f"png barcode noise {i} filler", path=self.path)

        dropped = mem.forget(capacity=3, path=self.path)
        self.assertNotIn(old_but_vital, dropped)

    def test_forget_respects_capacity(self):
        for i in range(10):
            mem.remember(f"png barcode item {i}", path=self.path)
        mem.forget(capacity=4, path=self.path)
        self.assertEqual(mem.stats(path=self.path)["count"], 4)

    def test_forget_under_capacity_drops_nothing(self):
        mem.remember("a", path=self.path)
        self.assertEqual(mem.forget(capacity=10, path=self.path), [])

    # --- persistence -----------------------------------------------------------

    def test_memory_survives_reload(self):
        eid = mem.remember("png barcode output contract", path=self.path)
        mem.recall("barcode png", path=self.path)
        mem.credit(eid, helped=True, path=self.path)
        again = mem.recall("barcode png output", path=self.path)
        self.assertEqual(again[0]["id"], eid)
        self.assertEqual(mem.stats(path=self.path)["credited"], 1)

    def test_stats_are_reported(self):
        mem.remember("png barcode output", path=self.path)
        s = mem.stats(path=self.path)
        self.assertEqual(s["count"], 1)
        self.assertIn("mean_importance", s)
        self.assertIn("max_importance", s)


if __name__ == "__main__":
    unittest.main()
