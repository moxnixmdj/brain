from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import patch

from canonical.runtime.root3_subprocess_final_authorizer_adapter_v2 import (
    make_authorizer,
    verify_mediator_request,
)


def canon(value):
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")


def mediator_request():
    core={
      "schema":"PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V2",
      "api":"subprocess.run",
      "command":{"kind":"ARGV","items":[{"kind":"STRING","value":"jq"}]},
      "cwd":None,"env":None,"stdin":None,"stdout":"PIPE","stderr":"PIPE",
      "input":None,"shell":False,"text":True,"capture_output":True,
      "timeout":60,"encoding":None,"errors":None,"close_fds":None,
      "callsite":{
        "module_path":"canonical/runtime/bound_capabilities/jq_query.py",
        "lineno":41,
        "process_api":"subprocess.run",
        "function":"run",
        "effect_class":"READ_ONLY_DECLARED_QUERY",
        "registry_site_count":19,
        "runtime_join":"EXACT_PATH_LINE_API",
      },
    }
    return {**core,"request_sha256":hashlib.sha256(canon(core)).hexdigest()}


class ClassBoundAdapterV2Tests(unittest.TestCase):
    def test_exact_registry_bound_request_verifies(self):
        out=verify_mediator_request(mediator_request())
        self.assertEqual(out["callsite"]["effect_class"],"READ_ONLY_DECLARED_QUERY")

    def test_effect_class_tamper_fails_even_when_rehashed(self):
        req=mediator_request()
        req["callsite"]["effect_class"]="LOCAL_LOOPBACK_SERVICE"
        core=dict(req); core.pop("request_sha256")
        req["request_sha256"]=hashlib.sha256(canon(core)).hexdigest()
        with self.assertRaisesRegex(Exception,"CALLSITE_REGISTRY_BINDING_MISMATCH"):
            verify_mediator_request(req)

    def test_line_tamper_fails_even_when_rehashed(self):
        req=mediator_request()
        req["callsite"]["lineno"]=42
        core=dict(req); core.pop("request_sha256")
        req["request_sha256"]=hashlib.sha256(canon(core)).hexdigest()
        with self.assertRaisesRegex(Exception,"CALLSITE_REGISTRY_BINDING_MISMATCH"):
            verify_mediator_request(req)

    def test_api_mismatch_fails(self):
        req=mediator_request()
        req["callsite"]["process_api"]="subprocess.Popen"
        core=dict(req); core.pop("request_sha256")
        req["request_sha256"]=hashlib.sha256(canon(core)).hexdigest()
        with self.assertRaisesRegex(Exception,"CALLSITE_API_MISMATCH"):
            verify_mediator_request(req)

    def test_mocked_final_allow_is_class_bound(self):
        seen={}
        def provider(req):
            seen["request"]=dict(req)
            return {"placeholder":True}
        final={
          "allowed":True,"status":"ALLOW_FINAL_AUTHORIZATION",
          "grant_sha256":"g"*64,
          "authority_receipt_git_blob_sha":"a"*40,
          "composition_receipt_git_blob_sha":"b"*40,
          "authority_proof_digest":"authority-proof",
          "composition_proof_digest":"composition-proof",
        }
        auth=make_authorizer(
            mission_id="m1",capsule_head_sha256="c"*64,
            action_ref_prefix="root3-subprocess-v2",repo_root=".",
            grant_provider=provider,
        )
        with patch(
          "canonical.runtime.root3_subprocess_final_authorizer_adapter_v2.authorize_effect",
          return_value=final,
        ):
            out=auth(mediator_request())
        self.assertTrue(out["allowed"])
        self.assertEqual(out["effect_class"],"READ_ONLY_DECLARED_QUERY")
        self.assertEqual(
            seen["request"]["resource"],
            "python:subprocess.run:READ_ONLY_DECLARED_QUERY",
        )
        self.assertEqual(seen["request"]["operation"],"invoke_classified")
        self.assertEqual(
            seen["request"]["payload"]["callsite"]["lineno"],41
        )

    def test_nonfinal_allow_is_denied(self):
        auth=make_authorizer(
            mission_id="m1",capsule_head_sha256="c"*64,
            action_ref_prefix="root3-subprocess-v2",repo_root=".",
            grant_provider=lambda req: {"placeholder":True},
        )
        with patch(
          "canonical.runtime.root3_subprocess_final_authorizer_adapter_v2.authorize_effect",
          return_value={"allowed":True,"status":"ALLOW_PRECOMMIT"},
        ):
            out=auth(mediator_request())
        self.assertFalse(out["allowed"])
        self.assertIn("FINAL_AUTHORIZATION_DENIED",out["reason"])


if __name__=="__main__":
    unittest.main(verbosity=2)
