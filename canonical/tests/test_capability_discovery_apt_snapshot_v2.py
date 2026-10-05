from __future__ import annotations

import importlib.util
import inspect
import json
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = CANONICAL_ROOT / "runtime" / "capability_discovery.py"
spec = importlib.util.spec_from_file_location("capability_discovery_apt_snapshot_v2_target", PATH)
discovery = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = discovery
spec.loader.exec_module(discovery)

class AptSnapshotDiscoveryV2Tests(unittest.TestCase):
    def records(self):
        return [
            {
                "Package": "zbar-tools",
                "Version": "0.23.92-1",
                "SHA256": "1"*64,
                "Description": "QR code and bar code scanner decoder utilities",
                "Architecture": "amd64",
            },
            {
                "Package": "zbar-tools",
                "Version": "0.23.93-4build3",
                "SHA256": "2"*64,
                "Description": "QR code and bar code scanner decoder utilities",
                "Architecture": "amd64",
            },
            {
                "Package": "noise",
                "Version": "1.0",
                "SHA256": "3"*64,
                "Description": "unrelated package",
                "Architecture": "all",
            },
        ]

    def test_debian_version_ordering_core_cases(self):
        cmp = discovery._debian_version_compare
        self.assertLess(cmp("1.0~rc1", "1.0"), 0)
        self.assertGreater(cmp("1:1.0", "2.0"), 0)
        self.assertGreater(cmp("1.0-2", "1.0-1"), 0)
        self.assertGreater(cmp("1.0+git1", "1.0"), 0)
        self.assertEqual(cmp("1.01", "1.1"), 0)

    def test_snapshot_search_selects_highest_content_addressed_version(self):
        with mock.patch.object(discovery, "_apt_snapshot_package_records", return_value=self.records()):
            out = discovery._legacy_search_apt_packages("decode barcode image", limit=20)
        cand = next(x for x in out["candidates"] if x["name"] == "zbar-tools")
        self.assertEqual(cand["version"], "0.23.93-4build3")
        self.assertEqual(cand["archive_sha256"], "2"*64)
        self.assertIn("barcode", cand["matched_terms"])
        self.assertIn("decode", cand["matched_terms"])
        self.assertEqual(out["metadata_route"]["candidate_version_rule"], "HIGHEST_DEBIAN_VERSION_WITH_UNIQUE_SHA256")

    def test_same_package_version_with_conflicting_hashes_is_rejected(self):
        records = self.records() + [{
            "Package": "zbar-tools",
            "Version": "0.23.93-4build3",
            "SHA256": "f"*64,
            "Description": "QR code and bar code scanner decoder utilities",
            "Architecture": "amd64",
        }]
        with mock.patch.object(discovery, "_apt_snapshot_package_records", return_value=records):
            out = discovery._legacy_search_apt_packages("decode barcode image", limit=20)
        self.assertNotIn("zbar-tools", [x["name"] for x in out["candidates"]])
        self.assertTrue(any(x.get("error") == "APT_SNAPSHOT_VERSION_HASH_AMBIGUOUS:zbar-tools:0.23.93-4build3" for x in out["errors"]))

    def test_snapshot_fallback_requires_no_apt_cache_binary(self):
        with mock.patch.object(discovery, "_search_apt_packages_full_metadata", return_value=None), \
             mock.patch.object(discovery, "_apt_snapshot_package_records", return_value=self.records()), \
             mock.patch.object(discovery.shutil, "which", return_value=None), \
             mock.patch.object(discovery.sys, "platform", "linux"):
            out = discovery.search_apt_packages("decode barcode image", limit=20)
        self.assertEqual(out["source"], "APT_CATALOG")
        self.assertIn("zbar-tools", [x["name"] for x in out["candidates"]])

    def test_legacy_snapshot_fallback_contains_no_process_creation(self):
        source = inspect.getsource(discovery._legacy_search_apt_packages)
        self.assertNotIn("subprocess.", source)

    def test_capability_discovery_module_contains_no_subprocess_calls(self):
        tree_source = PATH.read_text(encoding="utf-8")
        self.assertNotIn("subprocess.run(", tree_source)
        self.assertNotIn("subprocess.Popen(", tree_source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
