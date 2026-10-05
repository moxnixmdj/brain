from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from canonical.runtime import root3_strict_current_bootstrap_v2 as bootstrap
from canonical.runtime import root3_subprocess_mediator_v2 as mediator


class StrictBootstrapV2Tests(unittest.TestCase):
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

    @staticmethod
    def allow(_request):
        return {"allowed": True, "authorization_sha256": "a" * 64}

    def _install(self):
        ro = lambda context: ("RO", context)
        tmp = lambda context: ("TMP", context)
        with patch.object(bootstrap.read_only, "make_executor", return_value=ro), \
             patch.object(bootstrap.temp_transform, "make_executor", return_value=tmp):
            return bootstrap.install_current(self.allow, authority_id="TEST")

    def test_installs_exactly_two_verified_executor_classes(self):
        out = self._install()
        self.assertEqual(out["process_site_count"], 18)
        self.assertEqual(
            set(out["bound_effect_classes"]),
            {"READ_ONLY_DECLARED_QUERY", "TEMPORARY_FILESYSTEM_TRANSFORM"},
        )
        self.assertEqual(
            set(out["denied_effect_classes"]),
            set(bootstrap.CLASSES)
            - {"READ_ONLY_DECLARED_QUERY", "TEMPORARY_FILESYSTEM_TRANSFORM"},
        )
        self.assertTrue(out["run_guard_active"])
        self.assertTrue(out["popen_guard_active"])

    def test_unregistered_direct_process_fails_before_authorizer(self):
        seen = []
        def auth(request):
            seen.append(request)
            return {"allowed": True, "authorization_sha256": "a" * 64}
        ro = lambda context: context
        tmp = lambda context: context
        with patch.object(bootstrap.read_only, "make_executor", return_value=ro), \
             patch.object(bootstrap.temp_transform, "make_executor", return_value=tmp):
            bootstrap.install_current(auth, authority_id="TEST")
            with self.assertRaisesRegex(
                mediator.ProcessEffectDenied,
                "SUBPROCESS_CALLSITE_CLASSIFICATION_DENIED",
            ):
                subprocess.run(["never", "runs"])
        self.assertEqual(seen, [])

    def test_other_five_classes_remain_fail_closed(self):
        self._install()
        fake_callsite = {
            "module_path": "canonical/runtime/astra_runtime.py",
            "lineno": 595,
            "process_api": "subprocess.run",
            "function": "_ensure_pypi_dependency",
            "effect_class": "PACKAGE_ENV_MUTATION",
            "registry_site_count": 18,
            "runtime_join": "EXACT_PATH_LINE_API",
        }
        with patch.object(mediator, "_classify", return_value=fake_callsite):
            with self.assertRaisesRegex(
                mediator.ProcessEffectDenied,
                "PROCESS_EFFECT_CLASS_EXECUTOR_NOT_BOUND:PACKAGE_ENV_MUTATION",
            ):
                subprocess.run(["python", "-V"])

    def test_process_universe_drift_fails_before_install(self):
        with patch.object(bootstrap, "EXPECTED", {}):
            with self.assertRaisesRegex(bootstrap.BootstrapError, "PROCESS_UNIVERSE_DRIFT"):
                bootstrap.install_current(self.allow, authority_id="TEST")
        self.assertFalse(mediator.status()["installed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
