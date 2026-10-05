from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime import root3_two_class_attempt_authorizer_v1 as auth
from canonical.runtime import root3_subprocess_mediator_v2 as mediator


def rehash(req):
    core=dict(req); core.pop("request_sha256",None)
    req["request_sha256"]=mediator._sha(core)
    return req


def read_request():
    callsite={
      "module_path":"canonical/runtime/bound_capabilities/jq_query.py",
      "lineno":41,
      "process_api":"subprocess.run",
      "function":"run",
      "effect_class":"READ_ONLY_DECLARED_QUERY",
      "registry_site_count":18,
      "runtime_join":"EXACT_PATH_LINE_API",
    }
    return mediator._request(
      "subprocess.run",
      (["jq","-r",".x","/tmp/in.json"],),
      {"text":True,"capture_output":True,"timeout":60},
      callsite,
    )


def temp_request():
    td=tempfile.mkdtemp(prefix="project-brain-ocr-")
    callsite={
      "module_path":"canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",
      "lineno":29,
      "process_api":"subprocess.run",
      "function":"run",
      "effect_class":"TEMPORARY_FILESYSTEM_TRANSFORM",
      "registry_site_count":18,
      "runtime_join":"EXACT_PATH_LINE_API",
    }
    req=mediator._request(
      "subprocess.run",
      (["pdftoppm","-f","1","-l","50","-r","300","-png","/tmp/input.pdf",str(pathlib.Path(td)/"page")],),
      {"text":True,"capture_output":True,"timeout":180},
      callsite,
    )
    return req


class TwoClassAttemptAuthorizerTests(unittest.TestCase):
    def test_exact_read_only_allows(self):
        out=auth.authorize(read_request())
        self.assertTrue(out["allowed"])
        self.assertEqual(out["effect_class"],"READ_ONLY_DECLARED_QUERY")

    def test_exact_temp_allows(self):
        out=auth.authorize(temp_request())
        self.assertTrue(out["allowed"])
        self.assertEqual(out["effect_class"],"TEMPORARY_FILESYSTEM_TRANSFORM")
        self.assertEqual(out["callsite"]["profile"],"PDF_RASTER_EPHEMERAL_OUTPUT")

    def test_request_tamper_without_rehash_denies(self):
        req=temp_request(); req["timeout"]=179
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"REQUEST_HASH_MISMATCH")

    def test_temp_option_tamper_with_rehash_denies(self):
        req=temp_request()
        req["command"]["items"][7]["value"]="-jpeg"
        rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"TEMP_OPTIONS_INVALID")

    def test_temp_output_prefix_tamper_denies(self):
        req=temp_request()
        req["command"]["items"][9]["value"]="/tmp/not-approved/page"
        rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"TEMP_OUTPUT_PREFIX_INVALID")

    def test_registry_drift_denies(self):
        req=read_request(); req["callsite"]["registry_site_count"]=19; rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"REGISTRY_SITE_COUNT_MISMATCH")

    def test_other_class_denies(self):
        req=read_request(); req["callsite"]["effect_class"]="PACKAGE_ENV_MUTATION"; rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"EFFECT_CLASS_NOT_AUTHORIZED")

    def test_custom_env_denies(self):
        req=read_request(); req["env"]={"key_count":1,"binding_sha256":"a"*64}; rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"CUSTOM_ENV_FORBIDDEN")

    def test_unbounded_read_timeout_denies(self):
        req=read_request(); req["timeout"]=181; rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"TIMEOUT_OUT_OF_RANGE")

    def test_temp_wrong_callsite_denies(self):
        req=temp_request(); req["callsite"]["lineno"]=30; rehash(req)
        out=auth.authorize(req)
        self.assertFalse(out["allowed"])
        self.assertEqual(out["reason"],"CALLSITE_NOT_VERIFIED_TEMP")


if __name__=="__main__":
    unittest.main(verbosity=2)
