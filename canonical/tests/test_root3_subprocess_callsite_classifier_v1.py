from __future__ import annotations

import base64
import io
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import capability_discovery as discovery
from canonical.runtime.bound_capabilities import browser_chromedriver as browser
from canonical.runtime.bound_capabilities import jq_query
from canonical.runtime.root3_subprocess_callsite_classifier_v1 import (
    RuntimeCallsiteClassificationError,
    classify_frame_chain,
    detect_effect_class,
)
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED


class _FakePopen:
    def __init__(self, stdout_text=""):
        self.stdout = io.StringIO(stdout_text)
        self.returncode = 0
        self.terminated = False
        self.killed = False
    def wait(self, timeout=None):
        return self.returncode
    def terminate(self):
        self.terminated = True
    def kill(self):
        self.killed = True


class RuntimeCallsiteClassifierTests(unittest.TestCase):
    def test_registry_is_exact_19_site_universe(self):
        self.assertEqual(len(EXPECTED), 19)
        self.assertEqual(
            sum(1 for k in EXPECTED if k[2] == "subprocess.run"), 18
        )
        self.assertEqual(
            sum(1 for k in EXPECTED if k[2] == "subprocess.Popen"), 1
        )

    def test_direct_unregistered_test_call_fails_closed(self):
        with self.assertRaises(
            RuntimeCallsiteClassificationError,
            msg="a caller outside the frozen 19-site map must never inherit a class",
        ):
            detect_effect_class("subprocess.run")

    def test_unsupported_api_fails_closed(self):
        with self.assertRaisesRegex(
            RuntimeCallsiteClassificationError, "PROCESS_API_UNSUPPORTED"
        ):
            classify_frame_chain("os.system", None)

    def test_real_jq_run_site_runtime_joins_read_only_class(self):
        seen = {}
        def fake_run(*args, **kwargs):
            seen.update(detect_effect_class("subprocess.run"))
            return subprocess.CompletedProcess(
                args=args[0] if args else [],
                returncode=0,
                stdout="ok\n",
                stderr="",
            )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "in.json").write_text('{"x":1}\n', encoding="utf-8")
            with patch.object(jq_query.subprocess, "run", side_effect=fake_run):
                out = jq_query.run(
                    {
                        "input_path": "in.json",
                        "output_path": "out.txt",
                        "filter": ".",
                    },
                    root,
                )
            self.assertTrue(out["output_verified"])
        self.assertEqual(
            seen,
            {
                "module_path": "canonical/runtime/bound_capabilities/jq_query.py",
                "lineno": 41,
                "process_api": "subprocess.run",
                "function": "run",
                "effect_class": "READ_ONLY_DECLARED_QUERY",
                "registry_site_count": 19,
                "runtime_join": "EXACT_PATH_LINE_API",
            },
        )

    def test_deleted_apt_helper_popen_path_is_process_free(self):
        import inspect
        source = inspect.getsource(discovery._apt_contents_executable_owners)
        self.assertNotIn("subprocess.", source)

    def test_real_chromedriver_popen_site_runtime_joins_loopback_class(self):
        seen = {}
        png = b"\x89PNG\r\n\x1a\n" + (b"x" * 200)
        def fake_popen(*args, **kwargs):
            seen.update(detect_effect_class("subprocess.Popen"))
            return _FakePopen()
        def fake_json(method, url, payload=None, timeout=30):
            if url.endswith("/status"):
                return {"value": {"ready": True}}
            if url.endswith("/session") and method == "POST":
                return {"value": {"sessionId": "s"}}
            if url.endswith("/url") and method == "GET":
                return {"value": "https://example.test/"}
            if url.endswith("/title"):
                return {"value": "Example"}
            if url.endswith("/execute/sync"):
                return {"value": {"text": "hello", "width": 800, "height": 800, "ready": "complete"}}
            if url.endswith("/screenshot"):
                return {"value": base64.b64encode(png).decode("ascii")}
            return {}
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            with patch.object(browser, "_free_port", return_value=43210), \
                 patch.object(browser, "_json_request", side_effect=fake_json), \
                 patch.object(browser.subprocess, "Popen", side_effect=fake_popen):
                out = browser.run(
                    {
                        "url": "https://example.test/",
                        "screenshot_path": "shot.png",
                        "result_path": "result.json",
                    },
                    root,
                )
            self.assertTrue(out["output_verified"])
        self.assertEqual(
            seen["module_path"],
            "canonical/runtime/bound_capabilities/browser_chromedriver.py",
        )
        self.assertEqual(seen["lineno"], 50)
        self.assertEqual(seen["process_api"], "subprocess.Popen")
        self.assertEqual(seen["effect_class"], "LOCAL_LOOPBACK_SERVICE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
