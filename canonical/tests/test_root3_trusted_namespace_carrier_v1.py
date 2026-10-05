from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from canonical.runtime import root3_subprocess_mediator_v2 as med
from canonical.runtime import zero_ambient_namespace_launcher_v1 as launcher


class TrustedNamespaceCarrierTests(unittest.TestCase):
    def tearDown(self):
        try:
            med.uninstall()
        except Exception:
            pass

    def test_carrier_denied_when_mediator_not_installed(self):
        with self.assertRaisesRegex(
            med.ProcessEffectDenied, "NAMESPACE_CARRIER_REQUIRES_INSTALLED_MEDIATOR"
        ):
            med.run_namespace_carrier({})

    def test_carrier_denied_outside_executor_even_when_installed(self):
        def auth(_request):
            return {"allowed": False}

        med.install(auth, authority_id="test")
        with self.assertRaisesRegex(
            med.ProcessEffectDenied, "NAMESPACE_CARRIER_OUTSIDE_CLASS_EXECUTOR_FORBIDDEN"
        ):
            med.run_namespace_carrier({})

    def test_executor_seam_uses_frozen_original_popen_only(self):
        seen = {}
        original_authorize = med._authorize

        def fake_authorize(api, args, kwargs):
            return {
                "effect_class": "READ_ONLY_DECLARED_QUERY",
                "callsite": {"effect_class": "READ_ONLY_DECLARED_QUERY"},
            }

        def fake_run_confined(policy, *, popen_impl=None):
            seen["policy"] = policy
            seen["popen_impl"] = popen_impl
            return {"status": "SYNTHETIC_PASS"}

        def executor(_context):
            return med.run_namespace_carrier({"synthetic": True})

        try:
            med._authorize = fake_authorize
            with mock.patch.object(launcher, "run_confined", side_effect=fake_run_confined):
                med.install(
                    lambda _request: {"allowed": False},
                    authority_id="test",
                    class_executors={"READ_ONLY_DECLARED_QUERY": executor},
                )
                out = med._execute("subprocess.run", (["/usr/bin/true"],), {})
            self.assertEqual(out, {"status": "SYNTHETIC_PASS"})
            self.assertEqual(seen["policy"], {"synthetic": True})
            self.assertIs(seen["popen_impl"], med._ORIGINAL_POPEN)
            self.assertIsNot(seen["popen_impl"], med._guarded_popen)
        finally:
            med._authorize = original_authorize

    def test_launcher_rejects_noncallable_spawn_injection(self):
        with tempfile.TemporaryDirectory() as td:
            policy = {
                "argv": ["/usr/bin/true"],
                "input_dir": td,
                "limits": {},
            }
            if __import__("os").geteuid() == 0:
                policy["host_uid"] = 65534
                policy["host_gid"] = 65534
            with self.assertRaisesRegex(
                launcher.NamespaceConfinementError, "POPEN_IMPL_NOT_CALLABLE"
            ):
                launcher.run_confined(policy, popen_impl=object())


if __name__ == "__main__":
    unittest.main(verbosity=2)
