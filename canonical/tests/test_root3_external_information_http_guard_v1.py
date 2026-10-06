from __future__ import annotations

import types
import unittest
import urllib.request
from unittest import mock

from canonical.runtime import root3_external_information_http_guard_v1 as guard
from canonical.runtime import root3_production_astra_launcher_v1 as launcher


class HTTPGuardTests(unittest.TestCase):
    def fake_astra(self):
        calls = []

        def original(request, timeout=20, *args, **kwargs):
            calls.append((request, timeout, args, kwargs))
            return "TRANSPORTED"

        request_ns = types.SimpleNamespace(urlopen=original)
        urllib_ns = types.SimpleNamespace(request=request_ns)
        astra = types.SimpleNamespace(
            _bridge_aware_urlopen=original,
            urllib=urllib_ns,
        )

        def activate():
            astra.urllib.request.urlopen = astra._bridge_aware_urlopen

        astra._activate_external_http_bridge = activate
        return astra, calls

    def test_post_is_denied_before_transport(self):
        astra, calls = self.fake_astra()
        guard.install(astra)
        req = urllib.request.Request("https://example.invalid/", data=b"x", method="POST")
        with self.assertRaisesRegex(
            guard.ExternalInformationHTTPGuardError,
            "EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:POST",
        ):
            astra._bridge_aware_urlopen(req)
        self.assertEqual(calls, [])

    def test_delete_without_body_is_denied_before_transport(self):
        astra, calls = self.fake_astra()
        guard.install(astra)
        req = urllib.request.Request("https://example.invalid/", method="DELETE")
        with self.assertRaisesRegex(
            guard.ExternalInformationHTTPGuardError,
            "EXTERNAL_INFORMATION_HTTP_METHOD_FORBIDDEN:DELETE",
        ):
            astra._bridge_aware_urlopen(req)
        self.assertEqual(calls, [])

    def test_get_with_body_is_denied_before_transport(self):
        astra, calls = self.fake_astra()
        guard.install(astra)
        req = urllib.request.Request("https://example.invalid/", data=b"x", method="GET")
        with self.assertRaisesRegex(
            guard.ExternalInformationHTTPGuardError,
            "EXTERNAL_INFORMATION_HTTP_BODY_FORBIDDEN",
        ):
            astra._bridge_aware_urlopen(req)
        self.assertEqual(calls, [])

    def test_get_and_head_are_allowed(self):
        astra, calls = self.fake_astra()
        guard.install(astra)
        self.assertEqual(astra._bridge_aware_urlopen("https://example.invalid/"), "TRANSPORTED")
        req = urllib.request.Request("https://example.invalid/", method="HEAD")
        self.assertEqual(astra._bridge_aware_urlopen(req), "TRANSPORTED")
        self.assertEqual(len(calls), 2)

    def test_activation_reinstalls_guard_and_install_is_idempotent(self):
        astra, calls = self.fake_astra()
        first = guard.install(astra)
        guarded = astra._bridge_aware_urlopen
        astra.urllib.request.urlopen = lambda *a, **k: "BYPASS"
        astra._activate_external_http_bridge()
        self.assertIs(astra.urllib.request.urlopen, guarded)
        second = guard.install(astra)
        self.assertEqual(first["request_body_allowed"], False)
        self.assertEqual(second["status"], "ALREADY_INSTALLED")
        self.assertEqual(calls, [])

    def test_production_loader_installs_http_guard_after_astra_import(self):
        astra, calls = self.fake_astra()
        with (
            mock.patch.object(
                launcher.bootstrap,
                "install_current",
                return_value={"run_guard_active": True, "popen_guard_active": True},
            ),
            mock.patch.object(
                launcher.bootstrap.mediator,
                "status",
                return_value={"run_guard_active": True, "popen_guard_active": True},
            ),
            mock.patch.object(launcher.importlib, "import_module", return_value=astra),
        ):
            loaded = launcher.load_astra_after_root3_install()
        self.assertIs(loaded, astra)
        req = urllib.request.Request("https://example.invalid/", data=b"x", method="POST")
        with self.assertRaises(guard.ExternalInformationHTTPGuardError):
            astra._bridge_aware_urlopen(req)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
