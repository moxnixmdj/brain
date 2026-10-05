from __future__ import annotations

import copy
import unittest

from canonical.runtime import root3_subprocess_mediator_v2 as mediator
from canonical.runtime.root3_read_only_current_authorizer_v1 import (
    AUTHORITY_ID,
    authorize,
)


READ_ONLY_CALLSITE = {
    "module_path": "canonical/runtime/bound_capabilities/jq_query.py",
    "lineno": 41,
    "process_api": "subprocess.run",
    "function": "query_json",
    "effect_class": "READ_ONLY_DECLARED_QUERY",
    "registry_site_count": 18,
    "runtime_join": "EXACT_PATH_LINE_API",
}

DENIED_CALLSITE = {
    "module_path": "canonical/runtime/astra_runtime.py",
    "lineno": 325,
    "process_api": "subprocess.run",
    "function": "run_shell",
    "effect_class": "ARBITRARY_COMMAND_EXECUTION",
    "registry_site_count": 18,
    "runtime_join": "EXACT_PATH_LINE_API",
}


def request(callsite):
    return mediator._request(
        "subprocess.run",
        (["jq", ".", "/tmp/input.json"],),
        {"capture_output": True, "text": True},
        callsite,
    )


class Tests(unittest.TestCase):
    def test_exact_read_only_request_allowed(self):
        verdict = authorize(request(READ_ONLY_CALLSITE))
        self.assertTrue(verdict["allowed"], verdict)
        self.assertEqual(verdict["authority_id"], AUTHORITY_ID)
        self.assertEqual(verdict["effect_class"], "READ_ONLY_DECLARED_QUERY")
        self.assertRegex(verdict["authorization_sha256"], r"^[0-9a-f]{64}$")

    def test_non_read_only_class_denied(self):
        verdict = authorize(request(DENIED_CALLSITE))
        self.assertFalse(verdict["allowed"], verdict)

    def test_tampered_hash_denied(self):
        req = request(READ_ONLY_CALLSITE)
        req["command"] = ["jq", "-r", ".", "/tmp/input.json"]
        verdict = authorize(req)
        self.assertFalse(verdict["allowed"], verdict)
        self.assertIn("CONTENT_HASH_MISMATCH", verdict["reason"])

    def test_unknown_callsite_denied(self):
        req = request(READ_ONLY_CALLSITE)
        core = copy.deepcopy(req)
        core["callsite"]["lineno"] = 999999
        core.pop("request_sha256")
        req2 = mediator._request(
            "subprocess.run",
            (["jq", ".", "/tmp/input.json"],),
            {"capture_output": True, "text": True},
            core["callsite"],
        )
        verdict = authorize(req2)
        self.assertFalse(verdict["allowed"], verdict)
        self.assertIn("CALLSITE_REGISTRY_BINDING_MISMATCH", verdict["reason"])

    def test_extra_field_denied(self):
        req = request(READ_ONLY_CALLSITE)
        req["surprise"] = True
        verdict = authorize(req)
        self.assertFalse(verdict["allowed"], verdict)
        self.assertIn("FIELD_SET_INVALID", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
