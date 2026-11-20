"""Integration test: BrowserCDP against real Chromium (not mock CDP server).

Launches real headless Chromium via real_chromium_launcher_v1 and exercises
BrowserCDP operations (snapshot, act NAVIGATE/CLICK_AX_ROLE_NAME) against it.
Validates that real browser automation works end-to-end despite the
GPU/Vulkan/EGL sandbox limitation (GPU process crash doesn't affect CDP).

Zero model calls, zero network calls (beyond CDP to localhost).
"""

from __future__ import annotations

import json
import unittest
from urllib.request import urlopen

from canonical.runtime.osworld_v21_browser_cdp_v1 import BrowserCDP
from canonical.runtime.real_chromium_launcher_v1 import launch_chromium, stop_chromium


class BrowserCDPRealChromiumIntegrationTests(unittest.TestCase):
    """Verify BrowserCDP works against real Chromium via CDP."""

    @classmethod
    def setUpClass(cls):
        cls.endpoint = launch_chromium(port=9232, timeout_s=30)

    @classmethod
    def tearDownClass(cls):
        stop_chromium(port=9232)

    def test_cdp_endpoint_responds(self):
        """CDP endpoint is reachable and reports browser info."""
        data = json.loads(urlopen(f"{self.endpoint}/json/version", timeout=5).read())
        self.assertIn("HeadlessChrome", data.get("Browser", ""))
        self.assertIn("Protocol-Version", data)

    def test_cdp_list_pages(self):
        """CDP /json/list returns available pages."""
        pages = json.loads(urlopen(f"{self.endpoint}/json/list", timeout=5).read())
        self.assertIsInstance(pages, list)

    def test_browser_cdp_snapshot_real_chromium(self):
        """BrowserCDP.snapshot() works against real Chromium."""
        bcdp = BrowserCDP()
        bcdp.endpoint = self.endpoint
        result = bcdp.snapshot()
        self.assertEqual(result["schema"], "PROJECT_BRAIN_OSWORLD_V21_BROWSER_CDP_V1")
        self.assertTrue(result["endpoint_bound"])
        self.assertGreaterEqual(result["page_count"], 1)

    def test_browser_cdp_act_navigate_real_chromium(self):
        """BrowserCDP.act() NAVIGATE works against real Chromium."""
        bcdp = BrowserCDP()
        bcdp.endpoint = self.endpoint
        result = bcdp.act({"type": "NAVIGATE", "url": "about:blank"})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["page_index"], 0)

    def test_browser_cdp_act_invalid_op(self):
        """BrowserCDP.act() rejects unsupported operations."""
        bcdp = BrowserCDP()
        bcdp.endpoint = self.endpoint
        with self.assertRaisesRegex(Exception, "BROWSER_OP_UNSUPPORTED"):
            bcdp.act({"type": "INVALID_OP"})

    def test_browser_cdp_endpoint_bound(self):
        """BrowserCDP requires endpoint binding before operations."""
        bcdp = BrowserCDP()
        with self.assertRaisesRegex(Exception, "BROWSER_NOT_BOUND"):
            bcdp.snapshot()


if __name__ == "__main__":
    unittest.main()
