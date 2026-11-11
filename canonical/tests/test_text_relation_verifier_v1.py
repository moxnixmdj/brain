#!/usr/bin/env python3
"""The relation verifier must say NO to a wrong program, not just YES to a right one.

A verifier tested only on correct outputs is a rubber stamp. Every test here that
asserts True is paired with one that asserts False for a program the machine
would otherwise have been happy with -- above all the NULL POLICY, "copy the
input", which satisfies every relation on an input that cannot discriminate.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tv = _load("canonical.runtime.text_relation_verifier_v1",
           "canonical/runtime/text_relation_verifier_v1.py")

DISCRIMINATING = "banana\napple\n\ncherry\napple\ndate\nelderberry\n"


class RelationKindTests(unittest.TestCase):
    def test_questions_are_not_relations(self):
        # relation_kind is deliberately PERMISSIVE: "unique" is a relation, and the
        # word appears in "the unique lines of the file a.txt" too. What keeps a
        # question a question is admits(), which also requires an output artifact
        # and a text suffix -- tested in AdmitsTests. Asserting on relation_kind
        # here would be testing the wrong function.
        for goal in ("count the lines in a.txt", "the different lines of a.txt"):
            self.assertIsNone(tv.relation_kind(goal), goal)

    def test_a_question_containing_a_relation_word_is_still_not_admitted(self):
        self.assertEqual(tv.relation_kind("the unique lines of the file a.txt"), "unique")
        self.assertFalse(tv.admits("the unique lines of the file a.txt", ".txt"))

    def test_verbs_needing_an_oracle_are_never_relations(self):
        for goal in ("summarize notes.txt into out.txt", "translate a.txt into b.txt",
                     "rewrite notes.txt into out.md", "explain a.txt into out.txt"):
            self.assertIsNone(tv.relation_kind(goal), goal)

    def test_reverse_is_two_operations(self):
        self.assertEqual(tv.relation_kind("reverse each line of a.txt into b.txt"),
                         "reverse_each_line")
        self.assertEqual(tv.relation_kind("reverse the lines of a.txt into b.txt"),
                         "reverse_lines")


class AdmitsTests(unittest.TestCase):
    def test_a_question_with_no_output_is_not_admitted_even_when_it_names_a_suffix(self):
        # '.txt' here belongs to the INPUT. This exact case shipped broken once.
        self.assertFalse(tv.admits("the unique lines of the file a.txt", ".txt"))

    def test_a_construction_with_an_output_is_admitted(self):
        self.assertTrue(tv.admits("sort notes.txt into sorted.txt", ".txt"))

    def test_non_text_suffixes_are_never_admitted_here(self):
        self.assertFalse(tv.admits("sort notes.txt into sorted.gz", ".gz"))


class DiscriminatesTests(unittest.TestCase):
    def test_the_real_environment_seed_cannot_discriminate(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "input.txt"
            p.write_bytes(b"brain computer env sample\n")   # computer_env_v1's seed
            self.assertFalse(tv.discriminates("reverse the lines of x into y.txt", p)[0])

    def test_the_probe_seed_discriminates_for_every_relation(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "input.txt"
            p.write_bytes(tv.probe_seed()["input.txt"])
            for goal in ("sort x.txt into y.txt", "reverse each line of x.txt into y.txt",
                         "reverse the lines of x.txt into y.txt",
                         "deduplicate x.txt into y.txt", "uppercase x.txt into y.txt",
                         "head 3 x.txt into y.txt", "strip blank lines x.txt into y.txt"):
                self.assertTrue(tv.discriminates(goal, p)[0], goal)


class VerdictTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self._tmp.name)
        self.src = self.d / "s.txt"
        self.src.write_text(DISCRIMINATING)

    def tearDown(self):
        self._tmp.cleanup()

    def _out(self, text):
        p = self.d / "out.txt"
        p.write_text(text)
        return p

    def _src_lines(self):
        return tv._lines(self.src.read_bytes())

    def test_sort_accepts_a_sorted_permutation(self):
        # Expectation is built from the SOURCE's own lines, so the test cannot
        # disagree with the verifier about what a trailing newline means.
        want = "\n".join(sorted(self._src_lines())) + "\n"
        self.assertTrue(tv.verdict("sort s.txt into out.txt", self.src, self._out(want))[0])

    def test_sort_rejects_a_dropped_blank_line(self):
        # Every line of the input must survive, including the empty one.
        want = "\n".join(sorted(l for l in self._src_lines() if l)) + "\n"
        self.assertFalse(tv.verdict("sort s.txt into out.txt", self.src, self._out(want))[0])

    def test_sort_rejects_the_identity(self):
        self.assertFalse(tv.verdict("sort s.txt into out.txt", self.src,
                                    self._out(DISCRIMINATING))[0])

    def test_sort_rejects_a_lost_or_invented_line(self):
        for bad in ("apple\napple\nbanana\ncherry\ndate\n",
                    "apple\napple\nbanana\ncherry\ndate\nelderberry\nzebra\n"):
            self.assertFalse(tv.verdict("sort s.txt into out.txt", self.src,
                                        self._out(bad))[0], bad)

    def test_per_line_reverse_accepts_rev_and_rejects_line_order(self):
        self.assertTrue(tv.verdict("reverse each line of s.txt into out.txt", self.src,
                                   self._out("ananab\nelppa\n\nyrrehc\nelppa\netad\nyrrebredle\n"))[0])
        self.assertFalse(tv.verdict("reverse each line of s.txt into out.txt", self.src,
                                    self._out("elderberry\ndate\napple\n"))[0])

    def test_line_order_reverse_accepts_tac_and_rejects_per_line(self):
        self.assertTrue(tv.verdict("reverse the lines of s.txt into out.txt", self.src,
                                   self._out("elderberry\ndate\napple\ncherry\n\napple\nbanana\n"))[0])
        self.assertFalse(tv.verdict("reverse the lines of s.txt into out.txt", self.src,
                                    self._out("ananab\nelppa\n\nyrrehc\nelppa\netad\nyrrebredle\n"))[0])

    def test_dedupe_rejects_a_non_adjacent_duplicate(self):
        # The first version of the check only compared NEIGHBOURS and passed this.
        self.assertFalse(tv.verdict("deduplicate s.txt into out.txt", self.src,
                                    self._out(DISCRIMINATING))[0])
        self.assertTrue(tv.verdict("deduplicate s.txt into out.txt", self.src,
                                   self._out("banana\napple\n\ncherry\ndate\nelderberry\n"))[0])

    def test_dedupe_rejects_reordering(self):
        self.assertFalse(tv.verdict("deduplicate s.txt into out.txt", self.src,
                                    self._out("apple\nbanana\ncherry\ndate\nelderberry\n"))[0])

    def test_degenerate_source_is_refused_before_comparison(self):
        one = self.d / "one.txt"
        one.write_bytes(b"brain computer env sample\n")
        same = self.d / "same.txt"
        same.write_bytes(b"brain computer env sample\n")
        self.assertFalse(tv.verdict("reverse the lines of one.txt into same.txt", one, same)[0])
        # and the reason names the real problem, not the comparison
        self.assertIn("SOURCE_CANNOT_DISCRIMINATE",
                      tv.verdict("reverse the lines of one.txt into same.txt", one, same)[1])

    def test_source_name_is_read_before_the_output_word(self):
        self.assertEqual(tv.probe_seed_name("sort notes.txt into sorted.txt"), "notes.txt")
        self.assertEqual(tv.probe_seed_name("deduplicate emails.txt into unique.txt"), "emails.txt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
