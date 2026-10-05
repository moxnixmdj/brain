from __future__ import annotations

import subprocess
import types
import unittest
from unittest import mock

from canonical.runtime import tb4_buildkite_zero_case_preflight_v1 as preflight


def cp(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


class TB4BuildkiteZeroCasePreflightTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"BUILDKITE": "true", "BUILDKITE_BUILD_ID": "b", "BUILDKITE_JOB_ID": "j"}, clear=False)
    @mock.patch.object(preflight, "_compose_smoke", return_value=(True, {"up_returncode": 0, "down_returncode": 0}))
    @mock.patch.object(preflight, "_ram_total_bytes", return_value=32 * 1024**3)
    @mock.patch.object(preflight.os, "cpu_count", return_value=8)
    @mock.patch.object(preflight.shutil, "disk_usage")
    @mock.patch.object(preflight, "_run")
    def test_full_substrate_pass(self, run, disk_usage, cpu_count, ram, compose):
        disk_usage.return_value = types.SimpleNamespace(
            total=158 * 1024**3,
            used=20 * 1024**3,
            free=138 * 1024**3,
        )
        run.side_effect = [
            cp("27.0.0"),
            cp("2.29.0"),
            cp("docker-ok"),
        ]
        out = preflight.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["terminal_cases_consumed"], 0)
        self.assertIn("BILLING_HARD_STOP_NOT_PROVED_BY_INSIDE_JOB_TELEMETRY", out["hard_nonclaims"])

    @mock.patch.dict("os.environ", {"BUILDKITE": "true"}, clear=False)
    @mock.patch.object(preflight, "_compose_smoke", return_value=(True, {}))
    @mock.patch.object(preflight, "_ram_total_bytes", return_value=32 * 1024**3)
    @mock.patch.object(preflight.os, "cpu_count", return_value=4)
    @mock.patch.object(preflight.shutil, "disk_usage")
    @mock.patch.object(preflight, "_run")
    def test_underprovisioned_cpu_fails_closed(self, run, disk_usage, cpu_count, ram, compose):
        disk_usage.return_value = types.SimpleNamespace(
            total=158 * 1024**3,
            used=20 * 1024**3,
            free=138 * 1024**3,
        )
        run.side_effect = [cp("27.0.0"), cp("2.29.0"), cp("docker-ok")]
        out = preflight.evaluate()
        self.assertFalse(out["pass"])
        self.assertFalse(out["checks"]["cpu_ge_8"])

    @mock.patch.dict("os.environ", {}, clear=True)
    @mock.patch.object(preflight, "_compose_smoke", return_value=(True, {}))
    @mock.patch.object(preflight, "_ram_total_bytes", return_value=32 * 1024**3)
    @mock.patch.object(preflight.os, "cpu_count", return_value=8)
    @mock.patch.object(preflight.shutil, "disk_usage")
    @mock.patch.object(preflight, "_run")
    def test_non_buildkite_execution_fails_closed(self, run, disk_usage, cpu_count, ram, compose):
        disk_usage.return_value = types.SimpleNamespace(
            total=158 * 1024**3,
            used=20 * 1024**3,
            free=138 * 1024**3,
        )
        run.side_effect = [cp("27.0.0"), cp("2.29.0"), cp("docker-ok")]
        out = preflight.evaluate()
        self.assertFalse(out["pass"])
        self.assertFalse(out["checks"]["buildkite_environment"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
