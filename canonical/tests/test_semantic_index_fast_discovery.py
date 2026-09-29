#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "runtime"))

import capability_discovery as d


class SemanticIndexFastDiscoveryTests(unittest.TestCase):
    def test_xapian_candidates_skip_expensive_binding_evidence(self):
        rows = [
            {
                "name": "opaque-supplier",
                "description": "semantic package candidate",
                "relevance": 97,
                "acquisition_mode": "APT_XAPIAN_RELEVANCE",
            },
            {
                "name": "second-supplier",
                "description": "another semantic package candidate",
                "relevance": 83,
                "acquisition_mode": "APT_XAPIAN_RELEVANCE",
            },
        ]
        with (
            mock.patch.object(d.shutil, "which", return_value="/usr/bin/fake"),
            mock.patch.object(d, "_axi_cache_package_candidates", return_value=rows),
            mock.patch.object(d, "_apt_executable_evidence", side_effect=AssertionError("EXPENSIVE_LITERAL_PATH_CALLED")),
            mock.patch.object(d, "_batched_package_executable_evidence", side_effect=AssertionError("EXPENSIVE_RELEVANCE_BINDING_PATH_CALLED")),
            mock.patch.object(d, "_fetch_ubuntu_manpage_text", side_effect=AssertionError("REMOTE_MANPAGE_CALLED")),
        ):
            out = d.search_apt_packages(
                "Perform an unrelated semantic operation with a local package.",
                limit=2,
            )

        self.assertFalse(out["binding_performed"])
        self.assertEqual([x["name"] for x in out["candidates"]], ["opaque-supplier", "second-supplier"])
        self.assertTrue(all(x["package_relevance_source"] == "APT_XAPIAN_RELEVANCE" for x in out["candidates"]))


if __name__ == "__main__":
    unittest.main()
