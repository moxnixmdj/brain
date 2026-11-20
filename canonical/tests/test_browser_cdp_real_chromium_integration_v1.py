"""Integration test: BrowserCDP against real Chromium (not mock CDP server).

Launches real headless Chromium via real_chromium_launcher_v1 and exercises
BrowserCDP operations (snapshot, act NAVIGATE) against it.
Validates that real browser automation works end-to-end despite the
GPU/Vulkan/EGL sandbox limitation (GPU process crash doesn't affect CDP).

Zero model calls, zero network calls (beyond CDP to localhost).
"""

from __future__ import annotations

import http.server
import json
import threading
import unittest
from urllib.request import urlopen

from canonical.runtime.osworld_v21_browser_cdp_v1 import BrowserCDP
from canonical.runtime.real_chromium_launcher_v1 import launch_chromium, stop_chromium


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Minimal HTTP server handler that serves a tiny HTML page and logs nothing."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>test page</h1></body></html>")

    def log_message(self, format, *args):
        pass


class BrowserCDPRealChromiumIntegrationTests(unittest.TestCase):
    """Verify BrowserCDP works against real Chromium via CDP."""

    @classmethod
    def setUpClass(cls):
        # Start a local HTTP server so NAVIGATE has a reachable page
        cls._httpd = http.server.HTTPServer(("127.0.0.1", 0), _QuietHandler)
        cls._http_port = cls._httpd.server_address[1]
        cls._http_thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._http_thread.start()
        cls.endpoint = launch_chromium(port=9233, timeout_s=30)

    @classmethod
    def tearDownClass(cls):
        stop_chromium(port=9233)
        cls._httpd.shutdown()

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
        url = f"http://127.0.0.1:{self._http_port}/"
        result = bcdp.act({"type": "NAVIGATE", "url": url})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["page_index"], 0)
        self.assertEqual(result["after"]["url"], url)

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
