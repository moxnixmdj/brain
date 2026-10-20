"""Real-environment tests for the registered Brain-owned CDP browser route."""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
import unittest
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from canonical.runtime import availability_v1
from canonical.runtime.live_brain_route_admission_v1 import ROOT, solve


BROWSER_CAPABILITY = "web.browser.rendered.capture.chromedriver"
GITHUB_URL = "https://github.com/moxnixmdj/brain"


def _cleanup_task(task_id: str, work: Path) -> None:
    shutil.rmtree(work, ignore_errors=True)
    state_dir = ROOT / "canonical/astra_runtime/state"
    for path in state_dir.glob(task_id + "__*"):
        if path.is_file():
            path.unlink()


def _assert_png(path: Path) -> None:
    raw = path.read_bytes()
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(raw) > 100


def _find_true_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return value.get(key) is True or any(_find_true_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_find_true_key(child, key) for child in value)
    return False


def _contains_value(value, target) -> bool:
    if value == target:
        return True
    if isinstance(value, dict):
        return any(_contains_value(child, target) for child in value.values())
    if isinstance(value, list):
        return any(_contains_value(child, target) for child in value)
    return False


def _browser_ready_or_skip(testcase) -> None:
    if shutil.which("chromedriver") is not None:
        testcase.skipTest("driverless CDP fallback is only exercised when ChromeDriver is absent")
    missing = availability_v1.missing(BROWSER_CAPABILITY)
    if missing:
        testcase.skipTest("real browser prerequisites unavailable: " + ", ".join(missing))


class _FormHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        html = b'''<!doctype html><html><head><title>Real Form Probe</title></head><body>
          <h1>Order form</h1><form method="post" action="/submit">
          <label for="customer">Customer name</label><input id="customer" name="customer_name">
          <label for="size">Size</label><select id="size" name="size">
            <option value="small">Small</option><option value="medium">Medium</option>
            <option value="large">Large</option></select>
          <label><input type="checkbox" name="topping" value="bacon"> Bacon topping</label>
          <button type="submit">Submit</button></form></body></html>'''
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size).decode("utf-8")
        self.server.received = urllib.parse.parse_qs(body)
        rendered = "Submitted: " + " | ".join(
            key + "=" + ",".join(values)
            for key, values in sorted(self.server.received.items())
        )
        html = ("<!doctype html><html><head><title>Submitted</title></head><body><h1>" +
                rendered + "</h1></body></html>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, fmt, *args):
        return


class LiveBrainOwnedBrowserTests(unittest.TestCase):
    def test_missing_system_tool_source_executable_is_closed_without_a_fallback(self):
        executable = "brain-test-missing-executable-" + uuid.uuid4().hex
        self.assertIsNone(shutil.which(executable))
        registry = {"synthetic.test": {"source": {"type": "system_tool", "executable": executable}}}
        self.assertEqual(availability_v1.missing("synthetic.test", registry), [executable])

    def test_registered_browser_availability_matches_real_prerequisites(self):
        registry = availability_v1.load_registry()
        entry = registry[BROWSER_CAPABILITY]
        required = list(entry.get("requires_binaries") or [])
        if shutil.which("chromedriver") is not None:
            required.append("chromedriver")
        else:
            required.extend(["python3", "node", "npm", "openssl", "sh", "curl", "tar", "nohup", "sleep", "mkdir"])
        expected = list(dict.fromkeys(name for name in required if shutil.which(name) is None))
        missing = availability_v1.missing(BROWSER_CAPABILITY, registry)
        self.assertEqual(missing, expected)
        self.assertEqual(BROWSER_CAPABILITY in availability_v1.runnable(registry), not expected)
        self.assertEqual(entry["source"]["executable"], "chromedriver")
        if shutil.which("chromedriver") is None:
            self.assertNotIn("chromedriver", missing)
            self.assertEqual(entry["adapter_module"], "browser_chromedriver")

    def test_live_solve_renders_github_and_verifies_artifacts_without_chromedriver(self):
        _browser_ready_or_skip(self)
        task_id = "TEST_LIVE_CDP_CAPTURE_" + uuid.uuid4().hex
        work = ROOT / "canonical/astra_runtime/tmp" / task_id
        work.mkdir(parents=True, exist_ok=False)
        screenshot = work / "github.png"
        result_file = work / "github.json"
        screenshot_rel = screenshot.relative_to(ROOT).as_posix()
        result_rel = result_file.relative_to(ROOT).as_posix()
        goal = (
            "Using a rendered browser, open " + GITHUB_URL +
            f" and capture the page. Save a screenshot to {screenshot_rel} "
            f"and save the result to {result_rel}."
        )
        try:
            result = solve({"task_id": task_id, "goal": goal})
            self.assertIs(result.get("pass"), True, result)
            self.assertEqual(_contains_value(result, BROWSER_CAPABILITY), True)
            self.assertEqual(result.get("model_dependency_count"), 0)
            self.assertEqual(result.get("incremental_spend_usd"), 0)
            self.assertTrue(screenshot.is_file())
            self.assertTrue(result_file.is_file())
            _assert_png(screenshot)
            observed = json.loads(result_file.read_text(encoding="utf-8"))
            self.assertIn("moxnixmdj/brain", observed["final_url"])
            self.assertIn("GitHub", observed["page_title"])
            self.assertGreater(observed["screenshot_bytes"], 100)
            self.assertEqual(observed["screenshot_sha256"], hashlib.sha256(screenshot.read_bytes()).hexdigest())
            with urllib.request.urlopen(GITHUB_URL, timeout=30) as response:
                oracle = response.read().decode("utf-8", errors="replace")
                self.assertEqual(response.status, 200)
            self.assertIn("moxnixmdj/brain", oracle)
        finally:
            _cleanup_task(task_id, work)

    def test_live_solve_operates_a_real_form_and_post_submit_state_is_independent(self):
        _browser_ready_or_skip(self)
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FormHandler)
        server.received = None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        task_id = "TEST_LIVE_CDP_FORM_" + uuid.uuid4().hex
        work = ROOT / "canonical/astra_runtime/tmp" / task_id
        work.mkdir(parents=True, exist_ok=False)
        screenshot = work / "submitted.png"
        result_file = work / "submitted.json"
        screenshot_rel = screenshot.relative_to(ROOT).as_posix()
        result_rel = result_file.relative_to(ROOT).as_posix()
        url = f"http://127.0.0.1:{server.server_port}/form"
        goal = (
            "Use a browser to open " + url +
            "; enter PROJECT BRAIN into the customer name field; choose medium size; "
            "check bacon topping; submit the form; "
            f"save a screenshot to {screenshot_rel} and a result to {result_rel}."
        )
        try:
            result = solve({"task_id": task_id, "goal": goal})
            self.assertIs(result.get("pass"), True, result)
            self.assertEqual(_contains_value(result, BROWSER_CAPABILITY), True)
            self.assertEqual(result.get("model_dependency_count"), 0)
            self.assertEqual(result.get("incremental_spend_usd"), 0)
            self.assertTrue(screenshot.is_file())
            _assert_png(screenshot)
            observed = json.loads(result_file.read_text(encoding="utf-8"))
            self.assertEqual(server.received, {
                "customer_name": ["PROJECT BRAIN"],
                "size": ["medium"],
                "topping": ["bacon"],
            })
            self.assertIn("customer_name=PROJECT BRAIN", observed["observed_text"])
            self.assertIn("size=medium", observed["observed_text"])
            self.assertIn("topping=bacon", observed["observed_text"])
            self.assertIn("/submit", observed["final_url"])
            self.assertTrue(_find_true_key(result, "interaction_verified"))
        finally:
            _cleanup_task(task_id, work)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
