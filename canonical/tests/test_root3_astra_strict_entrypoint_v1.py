from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from canonical.runtime import root3_astra_strict_entrypoint_v1 as entry
from canonical.runtime import root3_read_only_process_authorizer_v1 as authmod
from canonical.runtime import root3_subprocess_mediator_v2 as mediator


class AstraStrictEntrypointTests(unittest.TestCase):
    def tearDown(self):
        try:
            mediator.uninstall()
        except Exception:
            subprocess.run = mediator._ORIGINAL_RUN
            subprocess.Popen = mediator._ORIGINAL_POPEN
            mediator._AUTHORIZER = None
            mediator._AUTHORITY_ID = None
            mediator._CLASS_EXECUTORS = {}
            mediator._INSTALLED = False

    def _request(self, callsite, command):
        return mediator._request(
            "subprocess.run",
            (command,),
            {"text": True, "capture_output": True, "timeout": 60},
            callsite,
        )

    def test_read_only_exact_current_request_is_authorized(self):
        request = self._request(
            {
                "module_path": "canonical/runtime/bound_capabilities/jq_query.py",
                "lineno": 41,
                "process_api": "subprocess.run",
                "function": "run",
                "effect_class": "READ_ONLY_DECLARED_QUERY",
                "registry_site_count": 18,
                "runtime_join": "EXACT_PATH_LINE_API",
            },
            ["jq", ".", "input.json"],
        )
        verdict = authmod.make_authorizer()(request)
        self.assertTrue(verdict["allowed"], verdict)
        self.assertEqual(verdict["effect_class"], "READ_ONLY_DECLARED_QUERY")
        self.assertEqual(len(verdict["authorization_sha256"]), 64)

    def test_non_read_only_exact_current_request_is_denied(self):
        request = self._request(
            {
                "module_path": "canonical/runtime/astra_runtime.py",
                "lineno": 595,
                "process_api": "subprocess.run",
                "function": "_ensure_pypi_dependency",
                "effect_class": "PACKAGE_ENV_MUTATION",
                "registry_site_count": 18,
                "runtime_join": "EXACT_PATH_LINE_API",
            },
            ["python", "-V"],
        )
        verdict = authmod.make_authorizer()(request)
        self.assertFalse(verdict["allowed"])
        self.assertEqual(verdict["reason"], "EFFECT_CLASS_NOT_READ_ONLY_DECLARED_QUERY")

    def test_bound_blob_drift_denies(self):
        request = self._request(
            {
                "module_path": "canonical/runtime/bound_capabilities/jq_query.py",
                "lineno": 41,
                "process_api": "subprocess.run",
                "function": "run",
                "effect_class": "READ_ONLY_DECLARED_QUERY",
                "registry_site_count": 18,
                "runtime_join": "EXACT_PATH_LINE_API",
            },
            ["jq", ".", "input.json"],
        )
        with patch.object(authmod, "_current_blobs", return_value={}):
            verdict = authmod.make_authorizer()(request)
        self.assertFalse(verdict["allowed"])
        self.assertEqual(verdict["reason"], "READ_ONLY_AUTHORITY_BOUND_BLOB_DRIFT")

    def test_entrypoint_installs_before_loading_astra(self):
        observed = []
        def fake_astra_main():
            observed.append(("astra_main", mediator.status()["installed"]))
            return 17
        original_loader = entry._load_astra_main
        try:
            entry._load_astra_main = lambda: (
                observed.append(("load_astra", mediator.status()["installed"]))
                or fake_astra_main
            )
            rc = entry.run()
        finally:
            entry._load_astra_main = original_loader
        self.assertEqual(rc, 17)
        self.assertEqual(observed, [("load_astra", True), ("astra_main", True)])
        self.assertEqual(
            mediator.status()["bound_effect_class_executors"],
            ["READ_ONLY_DECLARED_QUERY"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
