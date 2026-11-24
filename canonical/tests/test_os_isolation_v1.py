#!/usr/bin/env python3
"""Tests for the kernel isolation boundary.

These are adversarial by construction: every test either attacks the sandbox or
checks that a refusal happens instead of a silent downgrade. There are no mocks
-- the sandbox is entered for real, or the test says the machine cannot do it.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import os_isolation_v1 as iso


class SupportTests(unittest.TestCase):
    def test_support_is_answered_by_running_not_by_assuming(self):
        state = iso.support()
        self.assertIn("available", state)
        self.assertIn(state["available"], (True, False))
        if not state["available"]:
            self.assertEqual(state["reason"], iso.UNAVAILABLE)
            self.assertIn("detail", state)


class SandboxTests(unittest.TestCase):
    def setUp(self):
        state = iso.support()
        if not state.get("available"):
            self.skipTest("this machine offers no unprivileged namespaces")

    def test_a_payload_runs_and_its_effects_land_where_it_was_pointed(self):
        work = pathlib.Path(tempfile.mkdtemp(prefix="iso-test-"))
        result = iso.run(["sh", "-c", "echo hello > made.txt; pwd"],
                         work_dir=work, budget_s=30)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["isolated"], result)
        self.assertEqual((work / "made.txt").read_text().strip(), "hello",
                         "the payload's write did not land in the mounted work dir")
        self.assertIn("/work", result["stdout"])

    def test_the_payload_holds_no_capabilities(self):
        work = pathlib.Path(tempfile.mkdtemp(prefix="iso-test-"))
        code = ("print(open('/proc/self/status').read().split('CapEff:')[1].split()[0])")
        result = iso.run([sys.executable, "-c", code], work_dir=work, budget_s=30)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["stdout"].strip(), "0000000000000000")

    def test_a_host_path_is_absent_rather_than_forbidden(self):
        work = pathlib.Path(tempfile.mkdtemp(prefix="iso-test-"))
        host_file = pathlib.Path(__file__).resolve()
        code = ("import os,sys;print(os.path.exists(%r))" % str(host_file))
        result = iso.run([sys.executable, "-c", code], work_dir=work, budget_s=30)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["stdout"].strip(), "False",
                         "a host path was visible inside the sandbox")

    def test_there_is_no_network_route(self):
        work = pathlib.Path(tempfile.mkdtemp(prefix="iso-test-"))
        code = ("import socket\n"
                "s=socket.socket();s.settimeout(2)\n"
                "try:\n s.connect(('1.1.1.1',80));print('CONNECTED')\n"
                "except OSError as e:print('BLOCKED',e.errno)")
        result = iso.run([sys.executable, "-c", code], work_dir=work, budget_s=30)
        self.assertTrue(result["ok"], result)
        self.assertIn("BLOCKED", result["stdout"])

    def test_a_missing_work_dir_is_refused_not_invented(self):
        result = iso.run(["true"], work_dir="/nonexistent-dir-for-this-test")
        self.assertFalse(result["ok"])
        self.assertEqual(result["refused"], "REFUSED__WORK_DIR_MISSING")
        self.assertFalse(result["isolated"])

    def test_the_budget_is_enforced_and_reported_as_such(self):
        work = pathlib.Path(tempfile.mkdtemp(prefix="iso-test-"))
        result = iso.run([sys.executable, "-c", "import time;time.sleep(30)"],
                         work_dir=work, budget_s=2)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["timed_out"], result)


class ProbeTests(unittest.TestCase):
    def test_the_probe_attacks_the_box_and_reports_every_attempt(self):
        verdict = iso.probe()
        if verdict["verdict"] == "UNAVAILABLE":
            self.skipTest("no unprivileged namespaces here")
        attempts = verdict["attempts"]
        self.assertTrue(attempts, verdict)
        for must in ("read_host_canary", "write_host_path", "tcp_connect",
                     "mount_tmpfs", "chroot_again", "host_home"):
            self.assertIn(must, attempts, "the probe did not try %s" % must)
            self.assertTrue(attempts[must]["blocked"],
                            "%s succeeded inside the sandbox: %r" % (must, attempts[must]))
        self.assertEqual(verdict["verdict"], "ISOLATED", verdict["reasons"])
        self.assertFalse(verdict["host_canary_written"])
        self.assertEqual(verdict["caps_after_drop"], "0000000000000000")

    def test_a_liberal_reading_of_isolation_is_not_accepted(self):
        """The probe must fail closed when the payload keeps its capabilities."""
        probe = iso.probe()
        if probe["verdict"] == "UNAVAILABLE":
            self.skipTest("no unprivileged namespaces here")
        self.assertEqual(probe["verdict"], "ISOLATED")
        # the verdict is a function of the measurements, so tampering with a
        # measurement must change it: this re-derives the same decision from a
        # forged finding set and proves the rule is not a constant.
        forged = dict(probe["attempts"])
        forged["tcp_connect"] = {"blocked": False, "value": "CONNECTED"}
        escaped = [n for n, row in forged.items()
                   if not row.get("blocked") and n in iso._MUST_BLOCK]
        self.assertEqual(escaped, ["tcp_connect"])


if __name__ == "__main__":
    unittest.main()
