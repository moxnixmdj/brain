#!/usr/bin/env python3
"""Pinned tests for the held-out transfer measurement.

The point of these tests is not that the numbers are good. It is that the record says exactly
what the run found, including the negative result on the utc class.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import held_out_transfer_20261112_v1 as H

FIXTURE = ROOT / "canonical/tests/fixtures/held_out_transfer_v1.json"
RECORD = ROOT / "canonical/verification/HELD_OUT_TRANSFER_PRS_20261112_V1.json"


class Measured(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_the_pep585_transfer_is_the_one_pinned(self):
        pep = self.record["by_kind"]["pep585"]
        self.assertEqual((pep["base"]["right"], pep["base"]["developers_changes"]), (64, 525))
        self.assertEqual((pep["alias"]["right"], pep["alias"]["developers_changes"]), (197, 525))
        self.assertAlmostEqual(pep["base"]["coverage"], 0.121905, places=6)
        self.assertAlmostEqual(pep["alias"]["coverage"], 0.375238, places=6)
        self.assertAlmostEqual(pep["alias"]["precision"], 0.763566, places=6)
        self.assertEqual(pep["alias"]["wrong_changes"], 52)
        self.assertEqual(pep["alias"]["gain_right"], 133)

    def test_the_utc_transfer_is_the_negative_result_it_was(self):
        utc = self.record["by_kind"]["utc"]
        self.assertEqual((utc["base"]["right"], utc["base"]["developers_changes"]), (35, 410))
        self.assertEqual(utc["alias"]["right"], utc["base"]["right"])
        self.assertAlmostEqual(utc["base"]["coverage"], 0.085366, places=6)
        self.assertAlmostEqual(utc["base"]["precision"], 0.479452, places=6)
        self.assertEqual(utc["alias"]["gain_right"], 0)

    def test_the_two_pull_requests_that_transfer_are_named(self):
        rows = self.record["per_pull_request"]
        self.assertEqual(rows["VHDL/pyVHDLModel#204"]["alias"]["right"], 108)
        self.assertEqual(rows["yaalalabs/agent-kernel#825"]["alias"]["right"], 79)
        self.assertEqual(rows["ncouture/AirTell#200"]["alias"]["right"], 0)
        self.assertEqual(rows["agencyenterprise/draft-detective#858"]["alias"]["right"], 10)

    def test_the_design_corpus_is_excluded_by_name(self):
        names = {row["name"] for row in json.loads(RECORD.read_text(encoding="utf-8"))}
        self.assertFalse(names & set(H.DESIGN))
        self.assertEqual(len(names), 8)

    def test_the_project_module_upper_bound_is_recorded(self):
        assumed = self.record["by_mode"]["assumed"]["by_kind"]
        utc = assumed["utc"]["base"]
        self.assertEqual((utc["right"], utc["developers_changes"]), (140, 410))
        self.assertAlmostEqual(utc["coverage"], 0.341463, places=6)
        self.assertAlmostEqual(utc["precision"], 0.606061, places=6)
        self.assertEqual(utc["wrong_changes"], 65)
        rows = self.record["by_mode"]["assumed"]["per_pull_request"]
        self.assertEqual(rows["zkaelxz/U00#1831"]["base"]["right"], 72)
        self.assertEqual(rows["mborchuk/ContaAutonomo#121"]["base"]["right"], 30)

    def test_a_tiny_pull_request_is_measured_without_a_crash(self):
        files = [
            {"path": "a.py", "before": "from typing import List\n\ndef f(x: List[int]) -> None: ...\n",
             "after": "from typing import List\n\ndef f(x: list[int]) -> None: ...\n"},
            {"path": "b.py", "before": "from typing import List\n\ndef g(y: List[str]) -> None: ...\n",
             "after": "from typing import List\n\ndef g(y: list[str]) -> None: ...\n"},
        ]
        row = H.one_pull_request(files)
        self.assertEqual(row["files"], 2)
        self.assertGreaterEqual(row["alias"]["right"], row["base"]["right"])


if __name__ == "__main__":
    unittest.main()
