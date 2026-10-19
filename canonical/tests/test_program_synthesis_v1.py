#!/usr/bin/env python3
"""A program is only accepted once the artifact is really there.

Synthesis that returns plausible-looking source without running it is not
synthesis, it is autocomplete. These tests execute every candidate and check
the bytes it produced -- and for formats that can be read back, they read
them back.

Sabotage: make a candidate claim success without producing the file and most
of these fail.
"""

from __future__ import annotations

import gzip
import json
import os
import pathlib
import struct
import tempfile
import unittest
import zipfile

from canonical.runtime import program_synthesis_v1 as ps

SAMPLE = "brain synthesis sample"


class SynthesisCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-synth-test-")
        self.old_state = ps.STATE_PATH
        ps.STATE_PATH = os.path.join(self.tmp, "state.json")

    def tearDown(self) -> None:
        ps.STATE_PATH = self.old_state
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, goal: str, content: str = SAMPLE):
        """Synthesise into a real directory we can inspect afterwards."""
        work = pathlib.Path(self.tmp) / "work"
        work.mkdir(parents=True, exist_ok=True)
        return ps.synthesize(goal, content=content, workdir=work), work


# --------------------------------------------------------------------------- #
# the artifact must really exist and really be that format
# --------------------------------------------------------------------------- #
class EffectTests(SynthesisCase):
    def test_a_gzip_goal_produces_a_real_gzip_file(self):
        r, work = self.make("compress the report into out.gz")
        self.assertTrue(r["pass"], r)
        out = pathlib.Path(r["output_path"])
        self.assertTrue(out.is_file())
        self.assertEqual(out.read_bytes()[:2].hex(), "1f8b")

    def test_the_gzip_round_trips_back_to_the_content(self):
        """The strongest check there is: read it back and compare."""
        r, _ = self.make("compress the report into out.gz", content="round trip me")
        with gzip.open(r["output_path"], "rt", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "round trip me")

    def test_a_zip_goal_produces_a_real_zip(self):
        r, _ = self.make("bundle the files into out.zip")
        self.assertTrue(r["pass"], r)
        self.assertEqual(pathlib.Path(r["output_path"]).read_bytes()[:4].hex(),
                         "504b0304")
        with zipfile.ZipFile(r["output_path"]) as zf:
            self.assertEqual(zf.namelist(), ["content.txt"])
            self.assertEqual(zf.read("content.txt").decode("utf-8"), SAMPLE)

    def test_a_png_goal_produces_a_real_png(self):
        """A PNG was previously written empty. It must be a real one."""
        r, _ = self.make("render a tiny out.png")
        self.assertTrue(r["pass"], r)
        raw = pathlib.Path(r["output_path"]).read_bytes()
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"),
                        "not a PNG signature")
        width, height = struct.unpack(">II", raw[16:24])
        self.assertEqual((width, height), (1, 1))
        self.assertIn(b"IEND", raw)

    def test_a_json_goal_produces_parseable_json(self):
        r, _ = self.make("save the results to out.json")
        self.assertTrue(r["pass"], r)
        data = json.loads(pathlib.Path(r["output_path"]).read_text())
        self.assertEqual(data["content"], SAMPLE)

    def test_a_bz2_goal_produces_a_bz2_file(self):
        r, _ = self.make("make out.bz2 from the data")
        self.assertTrue(r["pass"], r)
        import bz2
        with bz2.open(r["output_path"], "rt", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), SAMPLE)

    def test_a_tar_goal_produces_a_tar_file(self):
        r, _ = self.make("archive it as out.tar")
        self.assertTrue(r["pass"], r)
        import tarfile
        with tarfile.open(r["output_path"]) as tf:
            self.assertEqual(tf.getnames(), ["content.txt"])

    def test_every_declared_format_can_actually_be_produced(self):
        """The table is a claim. Each entry pays for itself here."""
        for suffix in ps.suffixes():
            with self.subTest(suffix=suffix):
                r = ps.synthesize("produce out" + suffix, content=SAMPLE)
                self.assertTrue(r["pass"], "%s: %s" % (suffix, r))


# --------------------------------------------------------------------------- #
# honesty
# --------------------------------------------------------------------------- #
class HonestyTests(SynthesisCase):
    def test_a_format_with_no_candidate_is_refused_not_faked(self):
        r = ps.synthesize("do the thing as out.pdf")
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], "OPEN__NO_CANDIDATE_FOR_FORMAT")
        self.assertNotIn(".pdf", ps.suffixes(),
                         "a pdf candidate now exists, so refusing is a lie")

    def test_a_goal_naming_no_output_format_is_refused(self):
        r = ps.synthesize("extract text from a pdf file")
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], "OPEN__NO_OUTPUT_FORMAT_IN_GOAL")

    def test_candidates_that_did_not_work_are_reported(self):
        r, _ = self.make("compress into out.gz")
        self.assertTrue(r["trials"])
        for row in r["trials"]:
            self.assertIn("candidate", row)
            self.assertIn("worked", row)

    def test_the_winner_really_ran(self):
        r, _ = self.make("compress into out.gz")
        winner = [row for row in r["trials"] if row["worked"]]
        self.assertEqual(len(winner), 1)
        self.assertEqual(winner[0]["returncode"], 0)
        self.assertNotEqual(winner[0]["duration_s"], 0)


# --------------------------------------------------------------------------- #
# memory: the point of learning is not to do it twice
# --------------------------------------------------------------------------- #
class OracleTests(SynthesisCase):
    """The oracle itself. If these break, nothing above means anything."""

    def test_a_missing_file_is_not_an_effect(self):
        ok, why = ps.check_effect(pathlib.Path(self.tmp) / "nope.gz", ".gz")
        self.assertFalse(ok)
        self.assertEqual(why, "NO_OUTPUT")

    def test_an_empty_file_is_not_an_effect(self):
        empty = pathlib.Path(self.tmp) / "empty.gz"
        empty.write_bytes(b"")
        ok, why = ps.check_effect(empty, ".gz")
        self.assertFalse(ok, "an empty file proved nothing")
        self.assertEqual(why, "NO_OUTPUT")

    def test_a_file_of_the_wrong_format_is_refused(self):
        wrong = pathlib.Path(self.tmp) / "wrong.gz"
        wrong.write_text("this is not gzip at all")
        ok, why = ps.check_effect(wrong, ".gz")
        self.assertFalse(ok, "a text file was accepted as gzip")
        self.assertTrue(str(why).startswith("MAGIC_MISMATCH"), why)

    def test_the_right_format_is_accepted(self):
        import gzip as _gzip
        good = pathlib.Path(self.tmp) / "good.gz"
        with _gzip.open(good, "wt", encoding="utf-8") as fh:
            fh.write("x")
        ok, why = ps.check_effect(good, ".gz")
        self.assertTrue(ok, why)
        self.assertEqual(why, "ROUND_TRIP_OK")

    def test_a_broken_candidate_is_skipped_and_the_search_continues(self):
        """Put a candidate that writes nothing at the FRONT. The machine must
        reject it and keep looking, not accept the first thing it tried."""
        saved = list(ps.CANDIDATES[".gz"])
        ps.CANDIDATES[".gz"] = [("broken_writes_nothing", "pass\n")] + saved
        try:
            r = ps.synthesize("compress into out.gz")
            self.assertTrue(r["pass"], r)
            self.assertNotEqual(r.get("name"), "broken_writes_nothing")
            first = r["trials"][0]
            self.assertEqual(first["candidate"], "broken_writes_nothing")
            self.assertFalse(first["worked"], "the broken candidate was accepted")
        finally:
            ps.CANDIDATES[".gz"] = saved

    def test_a_candidate_that_crashes_is_reported_not_hidden(self):
        saved = list(ps.CANDIDATES[".gz"])
        ps.CANDIDATES[".gz"] = [("crasher", "raise RuntimeError('boom')\n")] + saved
        try:
            r = ps.synthesize("compress into out.gz")
            first = r["trials"][0]
            self.assertEqual(first["candidate"], "crasher")
            self.assertFalse(first["ran"], "a crash was reported as a run")
        finally:
            ps.CANDIDATES[".gz"] = saved


class RoundTripTests(SynthesisCase):
    """A file that merely exists has proved nothing."""

    def test_a_text_file_is_not_accepted_as_a_database(self):
        fake = pathlib.Path(self.tmp) / "fake.db"
        fake.write_text("this is not a database")
        ok, why = ps.check_effect(fake, ".db")
        self.assertFalse(ok, "a text file was accepted as sqlite")
        self.assertEqual(why, "NOT_READABLE_AS_.db")

    def test_a_real_sqlite_file_is_accepted(self):
        import sqlite3
        real = pathlib.Path(self.tmp) / "real.db"
        c = sqlite3.connect(real)
        c.execute("create table t (x)")
        c.commit()
        c.close()
        ok, why = ps.check_effect(real, ".db")
        self.assertTrue(ok, why)

    def test_malformed_json_is_refused(self):
        bad = pathlib.Path(self.tmp) / "bad.json"
        bad.write_text("not json {")
        ok, why = ps.check_effect(bad, ".json")
        self.assertFalse(ok, "malformed json was accepted")
        self.assertEqual(why, "NOT_READABLE_AS_.json")

    def test_malformed_gzip_is_refused_even_without_the_magic(self):
        bad = pathlib.Path(self.tmp) / "bad.gz"
        bad.write_bytes(b"\x1f\x8b" + b"garbage that is not deflate")
        ok, why = ps.check_effect(bad, ".gz")
        self.assertFalse(ok, "a fake gzip header was accepted")

    def test_a_truncated_png_is_refused(self):
        r, _ = self.make("render a tiny out.png")
        self.assertTrue(r["pass"], r)
        raw = pathlib.Path(r["output_path"]).read_bytes()
        cut = pathlib.Path(self.tmp) / "cut.png"
        cut.write_bytes(raw[:20])          # signature, no IEND, bad IHDR
        ok, why = ps.check_effect(cut, ".png")
        self.assertFalse(ok, "a truncated PNG was accepted")

    def test_every_format_the_table_claims_has_a_way_to_be_checked(self):
        """A format with neither a magic number nor a round-trip is a format
        the machine cannot tell from any other pile of bytes."""
        for suffix in ps.suffixes():
            with self.subTest(suffix=suffix):
                has_magic = ps._magic_for(suffix) is not None
                has_round = suffix in ps._ROUND_TRIP
                self.assertTrue(has_magic or has_round,
                                "%s cannot be verified at all" % suffix)


class MemoryTests(SynthesisCase):
    def test_a_second_identical_goal_comes_from_memory(self):
        first = ps.synthesize_or_recall("compress the report into out.gz")
        self.assertFalse(first.get("from_memory"))
        second = ps.synthesize_or_recall("compress the report into out.gz")
        self.assertTrue(second.get("from_memory"))
        self.assertEqual(second["status"], "PASS__RECALLED_VERIFIED_PROGRAM")

    def test_recall_returns_the_program_that_was_verified(self):
        ps.synthesize_or_recall("compress the report into out.gz")
        known = ps.recall(".gz")
        self.assertIsNotNone(known)
        self.assertIn("gzip", known["source"])
        self.assertTrue(known["verified_sha256"])

    def test_nothing_is_remembered_from_a_failure(self):
        """Remembering a program that never worked would poison the memory."""
        ps.synthesize_or_recall("do the thing as out.pdf")
        self.assertIsNone(ps.recall(".pdf"))

    def test_a_failure_is_not_remembered_even_when_it_carries_source(self):
        ps.remember({"pass": False, "status": "OPEN__NO_CANDIDATE_FOR_FORMAT",
                     "suffix": ".pdf", "source": "definitely not verified"})
        self.assertIsNone(ps.recall(".pdf"),
                          "an unverified program was stored as knowledge")

    def test_memory_survives_a_fresh_module_state(self):
        ps.synthesize_or_recall("bundle the files into out.zip")
        state = json.loads(pathlib.Path(ps.STATE_PATH).read_text())
        self.assertIn(".zip", state["learned"])
