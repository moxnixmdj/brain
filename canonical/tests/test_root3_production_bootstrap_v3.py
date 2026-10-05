from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import root3_subprocess_mediator_v3 as m
from canonical.runtime import root3_two_class_attempt_authorizer_v2 as auth
from canonical.runtime import root3_strict_current_bootstrap_v3 as boot
from canonical.runtime import astra_root3_strict_runtime_v1 as launcher
from canonical.runtime.bound_capabilities import jq_query


class Root3ProductionBootstrapV3Tests(unittest.TestCase):
    def tearDown(self):
        try:
            m.uninstall()
        except Exception:
            subprocess.run = m._ORIGINAL_RUN
            subprocess.Popen = m._ORIGINAL_POPEN
            m._AUTHORIZER = None
            m._AUTHORITY_ID = None
            m._CLASS_EXECUTORS = {}
            m._INSTALLED = False

    def test_unknown_process_caller_denied_before_authorizer(self):
        seen = []
        def allow(req):
            seen.append(req)
            return {"allowed": True, "authorization_sha256": "a" * 64}
        m.install(allow, authority_id="TEST")
        with self.assertRaisesRegex(
            m.ProcessEffectDenied, "SUBPROCESS_CALLSITE_CLASSIFICATION_DENIED"
        ):
            subprocess.run(["never", "runs"])
        self.assertEqual(seen, [])

    def test_verified_jq_site_reaches_only_bound_read_executor(self):
        auth_seen = []
        exec_seen = []
        def allow(req):
            auth_seen.append(req)
            return {"allowed": True, "authorization_sha256": "b" * 64}
        def executor(ctx):
            exec_seen.append(ctx)
            return subprocess.CompletedProcess(
                args=ctx["args"][0], returncode=0, stdout='{"x":1}\n', stderr=""
            )
        m.install(
            allow,
            authority_id="TEST",
            class_executors={"READ_ONLY_DECLARED_QUERY": executor},
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "in.json").write_text('{"x":1}\n', encoding="utf-8")
            out = jq_query.run(
                {"input_path":"in.json","output_path":"out.txt","filter":"."},
                root,
            )
            self.assertTrue(out["output_verified"])
        self.assertEqual(len(auth_seen), 1)
        self.assertEqual(len(exec_seen), 1)
        cs = auth_seen[0]["callsite"]
        self.assertGreater(cs["registry_site_count"], 18)
        self.assertEqual(len(cs["registry_sha256"]), 64)
        self.assertEqual(cs["runtime_join"], "EXACT_PATH_LINE_INTERCEPTION_API")

    def test_strict_authorizer_allows_exact_verified_read_only_request(self):
        status = __import__(
            "canonical.runtime.root3_subprocess_callsite_classifier_v2",
            fromlist=["registry_status"],
        ).registry_status()
        callsite = {
            "module_path":"canonical/runtime/bound_capabilities/jq_query.py",
            "lineno":41,
            "process_api":"subprocess.run",
            "source_api":"subprocess.run",
            "function":"run",
            "effect_class":"READ_ONLY_DECLARED_QUERY",
            "classification_provenance":"PRESERVED_LEGACY_VERIFIED_MAPPING",
            "registry_site_count":status["registry_site_count"],
            "registry_sha256":status["registry_sha256"],
            "runtime_join":"EXACT_PATH_LINE_INTERCEPTION_API",
        }
        req = m._request(
            "subprocess.run",
            (["jq","-r",".x","/tmp/in.json"],),
            {"text":True,"capture_output":True,"timeout":60},
            callsite,
        )
        out = auth.authorize(req)
        self.assertTrue(out["allowed"])
        self.assertEqual(out["effect_class"], "READ_ONLY_DECLARED_QUERY")

    def test_strict_authorizer_denies_new_default_arbitrary_class(self):
        status = __import__(
            "canonical.runtime.root3_subprocess_callsite_classifier_v2",
            fromlist=["registry_status"],
        ).registry_status()
        callsite = {
            "module_path":"canonical/runtime/apt_cli_probe.py",
            "lineno":16,
            "process_api":"subprocess.run",
            "source_api":"subprocess.run",
            "function":"main",
            "effect_class":"ARBITRARY_COMMAND_EXECUTION",
            "classification_provenance":"CONSERVATIVE_DEFAULT_DENY_UNTIL_NARROWER_CLASS_PROVED",
            "registry_site_count":status["registry_site_count"],
            "registry_sha256":status["registry_sha256"],
            "runtime_join":"EXACT_PATH_LINE_INTERCEPTION_API",
        }
        req = m._request(
            "subprocess.run",
            (["apt-get","--version"],),
            {"text":True,"capture_output":True,"timeout":10},
            callsite,
        )
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "EFFECT_CLASS_NOT_AUTHORIZED")

    def test_bootstrap_binds_only_two_verified_classes(self):
        fake_read = lambda ctx: ("read", ctx)
        fake_temp = lambda ctx: ("temp", ctx)
        captured = {}
        def fake_install(authorizer, *, authority_id, class_executors):
            captured["executors"] = dict(class_executors)
            return {
                "bound_effect_class_executors": sorted(class_executors),
                "unbound_effect_classes": sorted(
                    boot.CLASSES - set(class_executors)
                ),
                "run_guard_active": True,
                "popen_guard_active": True,
                "registry": boot.classifier.registry_status(),
            }
        with patch.object(boot.read_only, "make_executor", return_value=fake_read), \
             patch.object(boot.temp_transform, "make_executor", return_value=fake_temp), \
             patch.object(boot.mediator, "install", side_effect=fake_install):
            out = boot.install_current(
                lambda req: {"allowed":False}, authority_id="TEST"
            )
        self.assertEqual(
            set(captured["executors"]),
            {"READ_ONLY_DECLARED_QUERY","TEMPORARY_FILESYSTEM_TRANSFORM"},
        )
        self.assertGreater(out["process_site_count"], 18)
        self.assertFalse(out["authority_widening"])

    def test_launcher_installs_guard_before_importing_astra(self):
        events = []
        class FakeAstra:
            __file__ = "canonical/runtime/astra_runtime.py"
            @staticmethod
            def main():
                events.append("astra-main")
                return 0
        def fake_install(*args, **kwargs):
            events.append("install")
            return {"run_guard_active":True,"popen_guard_active":True}
        def fake_import(name):
            self.assertEqual(events, ["install"])
            self.assertEqual(name, "canonical.runtime.astra_runtime")
            events.append("import-astra")
            return FakeAstra
        with patch.object(launcher.bootstrap, "install_current", side_effect=fake_install), \
             patch.object(launcher.importlib, "import_module", side_effect=fake_import):
            rc = launcher.main([
                "canonical/astra_runtime/missions/test.json"
            ])
        self.assertEqual(rc, 0)
        self.assertEqual(events, ["install","import-astra","astra-main"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
