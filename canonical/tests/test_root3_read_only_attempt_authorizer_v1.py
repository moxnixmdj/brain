from __future__ import annotations

import copy
import unittest

from canonical.runtime import root3_read_only_attempt_authorizer_v1 as auth
from canonical.runtime import root3_subprocess_mediator_v2 as mediator


def make_request():
    callsite = {
        "module_path": "canonical/runtime/bound_capabilities/jq_query.py",
        "lineno": 41,
        "process_api": "subprocess.run",
        "function": "run",
        "effect_class": "READ_ONLY_DECLARED_QUERY",
        "registry_site_count": 18,
        "runtime_join": "EXACT_PATH_LINE_API",
    }
    return mediator._request(
        "subprocess.run",
        (["jq", "-r", ".x", "/tmp/in.json"],),
        {"text": True, "capture_output": True, "timeout": 60},
        callsite,
    )


class ReadOnlyAttemptAuthorizerTests(unittest.TestCase):
    def test_exact_supported_request_allows(self):
        out = auth.authorize(make_request())
        self.assertTrue(out["allowed"])
        self.assertEqual(out["status"], "ALLOW_REQUEST_BOUND_READ_ONLY_ATTEMPT")
        self.assertEqual(len(out["authorization_sha256"]), 64)

    def test_request_tamper_denies(self):
        req = make_request()
        req["timeout"] = 61
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "REQUEST_HASH_MISMATCH")

    def test_unknown_callsite_denies(self):
        req = make_request()
        req["callsite"]["lineno"] = 999
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "CALLSITE_NOT_VERIFIED_READ_ONLY")

    def test_non_read_only_class_denies(self):
        req = make_request()
        req["callsite"]["effect_class"] = "ARBITRARY_COMMAND_EXECUTION"
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "EFFECT_CLASS_MISMATCH")

    def test_forged_function_denies(self):
        req = make_request()
        req["callsite"]["function"] = "forged"
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "CALLSITE_FUNCTION_MISMATCH")

    def test_registry_count_drift_denies(self):
        req = make_request()
        req["callsite"]["registry_site_count"] = 19
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "REGISTRY_SITE_COUNT_MISMATCH")

    def test_runtime_join_drift_denies(self):
        req = make_request()
        req["callsite"]["runtime_join"] = "OTHER"
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "RUNTIME_JOIN_MISMATCH")

    def test_custom_env_denies(self):
        req = make_request()
        req["env"] = {"key_count": 1, "binding_sha256": "a" * 64}
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "CUSTOM_ENV_FORBIDDEN")

    def test_shell_denies(self):
        req = make_request()
        req["shell"] = True
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "SHELL_FORBIDDEN")

    def test_unbounded_timeout_denies(self):
        req = make_request()
        req["timeout"] = 181
        core = dict(req); core.pop("request_sha256")
        req["request_sha256"] = mediator._sha(core)
        out = auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"], "TIMEOUT_OUT_OF_RANGE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
