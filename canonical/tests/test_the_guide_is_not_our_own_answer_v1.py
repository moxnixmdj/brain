#!/usr/bin/env python3
"""The instant-knowledge tier must not answer from our own results.

Measured 2026-11-24: asked to archive a file into `out.tar.gz` inside a sandbox
that had this repository mounted read-only, `local_guide_v1.lookup` returned
`canonical/governance/EXPLORE_CHANNEL_STATE_20261019_V1.md` -- a record of an
earlier run of the same goal, containing the plan that worked. On any machine
that carries our own receipts, the "guide" is the answer key, and reading it
would be self-answering.

A guide is the ENVIRONMENT's documentation. Records of this system's own outcomes
are excluded unless a caller asks for them explicitly and labels them contaminated.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import local_guide_v1 as lg

QUERY = "compress the input into out.gz"
ANSWER = ("# Session record\n\n"
          "| Goal | Plan found | Verification |\n|---|---|---|\n"
          "| `compress the input into out.gz` | `['run_gzip']` | ROUND_TRIP_OK |\n"
          "The compress the input into out.gz goal was solved by the gzip program, "
          "and the archive was verified by a round trip of the compress step.\n")


class OwnRecordTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="guide-contam-"))

    def _write(self, rel: str, body: str) -> pathlib.Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_a_receipt_is_classified_as_our_own_record(self):
        for rel in ("canonical/verification/RESULT_V1.json.md",
                    "canonical/evidence/x.md",
                    "docs/MY_RECEIPT_20261124_V1.md",
                    "canonical/astra_runtime/state/notes.md"):
            self.assertTrue(lg.is_own_record(pathlib.Path(rel)), rel)
        for rel in ("README.md", "canonical/runtime/local_guide_v1.py",
                    "docs/GUIDE_FOR_TOOL.md"):
            self.assertFalse(lg.is_own_record(pathlib.Path(rel)), rel)

    def test_the_answer_key_is_not_served_as_a_guide(self):
        self._write("canonical/governance/EXPLORE_CHANNEL_STATE_20261019_V1.md", ANSWER)
        found = lg.lookup(QUERY, root=self.root)
        self.assertEqual(found["status"], lg.OPEN_NOT_FOUND,
                         "a record of our own result answered the goal: %r"
                         % (found.get("documents"),))

    def test_a_real_guide_in_the_same_tree_is_still_served(self):
        self._write("canonical/governance/EXPLORE_CHANNEL_STATE_20261019_V1.md", ANSWER)
        self._write("docs/COMPRESSING_FILES.md",
                    "# Compressing files\n\n"
                    "To compress the input into out.gz, run the compress program on "
                    "the input file and keep the output under the name you were given.\n")
        found = lg.lookup(QUERY, root=self.root)
        self.assertEqual(found["status"], lg.PASS)
        paths = [d.get("path") for d in found["documents"]]
        self.assertTrue(all("STATE_20261019" not in str(p) for p in paths), paths)

    def test_reading_our_records_is_possible_only_by_asking(self):
        self._write("canonical/governance/EXPLORE_CHANNEL_STATE_20261019_V1.md", ANSWER)
        found = lg.lookup(QUERY, root=self.root, include_own_records=True)
        self.assertEqual(found["status"], lg.PASS,
                         "the contamination guard is a blanket refusal, not a boundary")
        paths = [str(d.get("path")) for d in found["documents"]]
        self.assertTrue(any("EXPLORE_CHANNEL_STATE_20261019" in p for p in paths), paths)


if __name__ == "__main__":
    unittest.main()
