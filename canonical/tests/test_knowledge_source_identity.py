#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "astra_runtime.py"
spec = importlib.util.spec_from_file_location("astra_runtime_knowledge_source_identity", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class KnowledgeSourceIdentityTests(unittest.TestCase):
    def _path(self, name):
        return CANONICAL_ROOT / "astra_runtime" / "tmp" / name

    def _write_evidence(self, path, source_url, final_url, value, json_path=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1",
            "source_url": source_url,
            "final_url": final_url,
            "source_type": "external_json",
            "http_status": 200,
            "retrieved_at_utc": runtime.utc(),
            "body_sha256": "0" * 64,
            "json_path": list(json_path or ["args", "claim"]),
            "value": value,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.addCleanup(lambda p=path: p.unlink(missing_ok=True))

    def _assess(self, a, b, output):
        self.addCleanup(lambda p=output: p.unlink(missing_ok=True))
        return runtime._goal_action({
            "type": "assess_knowledge_consistency",
            "args": {
                "evidence_paths": [
                    str(a.relative_to(runtime.ROOT)).replace("\\", "/"),
                    str(b.relative_to(runtime.ROOT)).replace("\\", "/"),
                ],
                "output_path": str(output.relative_to(runtime.ROOT)).replace("\\", "/"),
            },
        })

    def test_duplicate_source_identity_is_insufficient(self):
        a=self._path("TEST_DUPLICATE_SOURCE_A.json")
        b=self._path("TEST_DUPLICATE_SOURCE_B.json")
        out=self._path("TEST_DUPLICATE_SOURCE_ASSESSMENT.json")
        url="https://httpbin.org/get?claim=alpha"
        self._write_evidence(a,url,url,"alpha")
        self._write_evidence(b,url,url,"alpha")
        result=self._assess(a,b,out)
        self.assertEqual(result["status"],"INSUFFICIENT")
        self.assertEqual(result["fresh_evidence_count"],2)
        self.assertEqual(result["distinct_fresh_source_identities"],1)

    def test_distinct_source_identities_can_support_same_value(self):
        a=self._path("TEST_DISTINCT_SOURCE_A.json")
        b=self._path("TEST_DISTINCT_SOURCE_B.json")
        out=self._path("TEST_DISTINCT_SOURCE_ASSESSMENT.json")
        self._write_evidence(a,"https://httpbin.org/get?claim=alpha","https://httpbin.org/get?claim=alpha","alpha")
        self._write_evidence(b,"https://httpbin.org/anything?claim=alpha","https://httpbin.org/anything?claim=alpha","alpha")
        result=self._assess(a,b,out)
        self.assertEqual(result["status"],"SUPPORTED")
        self.assertEqual(result["distinct_fresh_source_identities"],2)

    def test_redirect_aliases_collapse_to_one_final_source_identity(self):
        a=self._path("TEST_ALIAS_SOURCE_A.json")
        b=self._path("TEST_ALIAS_SOURCE_B.json")
        out=self._path("TEST_ALIAS_SOURCE_ASSESSMENT.json")
        self._write_evidence(a,"https://alias.example/source","https://example.com/data#first","alpha",["value"])
        self._write_evidence(b,"https://example.com/data","https://EXAMPLE.com:443/data#second","alpha",["value"])
        result=self._assess(a,b,out)
        self.assertEqual(result["status"],"INSUFFICIENT")
        self.assertEqual(result["distinct_fresh_source_identities"],1)


    def test_invalid_evidence_contract_cannot_create_support(self):
        a=self._path("TEST_INVALID_EVIDENCE_A.json")
        b=self._path("TEST_INVALID_EVIDENCE_B.json")
        out=self._path("TEST_INVALID_EVIDENCE_ASSESSMENT.json")
        a.parent.mkdir(parents=True,exist_ok=True)
        a.write_text(json.dumps({"value":"alpha"})+"\n",encoding="utf-8")
        b.write_text(json.dumps({"value":"alpha"})+"\n",encoding="utf-8")
        self.addCleanup(lambda: a.unlink(missing_ok=True))
        self.addCleanup(lambda: b.unlink(missing_ok=True))
        result=self._assess(a,b,out)
        self.assertEqual(result["status"],"INSUFFICIENT")
        self.assertEqual(result["evidence_count"],0)
        assessment=json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(len(assessment["invalid"]),2)
        self.assertTrue(all(x["error"]=="EVIDENCE_SCHEMA_INVALID" for x in assessment["invalid"]))


    class _FakeResponse:
        def __init__(self,url,value):
            self._url=url
            self._raw=json.dumps({"args":{"claim":value}}).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self,exc_type,exc,tb):
            return False
        def read(self,max_bytes):
            return self._raw[:max_bytes]
        def geturl(self):
            return self._url

    def _supported_assessment(self,prefix="TEST_REVALIDATE"):
        a=self._path(prefix+"_A.json")
        b=self._path(prefix+"_B.json")
        assessment=self._path(prefix+"_ASSESSMENT.json")
        self._write_evidence(a,"https://source-a.example/data","https://source-a.example/data","alpha")
        self._write_evidence(b,"https://source-b.example/data","https://source-b.example/data","alpha")
        result=self._assess(a,b,assessment)
        self.assertEqual(result["status"],"SUPPORTED")
        return a,b,assessment

    def test_materialization_revalidates_supported_sources(self):
        _,_,assessment=self._supported_assessment("TEST_REVALIDATE_SUCCESS")
        output=self._path("TEST_REVALIDATE_SUCCESS_FACT.json")
        self.addCleanup(lambda: output.unlink(missing_ok=True))
        def fake_urlopen(req,timeout=20):
            return self._FakeResponse(req.full_url,"alpha")
        with mock.patch.object(runtime.urllib.request,"urlopen",side_effect=fake_urlopen):
            result=runtime._goal_action({
                "type":"materialize_supported_knowledge",
                "args":{
                    "assessment_path":str(assessment.relative_to(runtime.ROOT)).replace("\\","/"),
                    "field_name":"claim",
                    "output_path":str(output.relative_to(runtime.ROOT)).replace("\\","/"),
                },
            })
        self.assertTrue(result["output_verified"])
        self.assertEqual(result["revalidated_evidence_count"],2)
        self.assertEqual(result["distinct_revalidated_source_identities"],2)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")),[{"claim":"alpha"}])

    def test_materialization_refuses_when_revalidation_changes(self):
        _,_,assessment=self._supported_assessment("TEST_REVALIDATE_CHANGE")
        output=self._path("TEST_REVALIDATE_CHANGE_FACT.json")
        self.addCleanup(lambda: output.unlink(missing_ok=True))
        def fake_urlopen(req,timeout=20):
            value="beta" if "source-b.example" in req.full_url else "alpha"
            return self._FakeResponse(req.full_url,value)
        with mock.patch.object(runtime.urllib.request,"urlopen",side_effect=fake_urlopen):
            result=runtime._goal_action({
                "type":"materialize_supported_knowledge",
                "args":{
                    "assessment_path":str(assessment.relative_to(runtime.ROOT)).replace("\\","/"),
                    "field_name":"claim",
                    "output_path":str(output.relative_to(runtime.ROOT)).replace("\\","/"),
                },
            })
        self.assertFalse(result["output_verified"])
        self.assertEqual(result["blocked_reason"],"KNOWLEDGE_REVALIDATION_FAILED")
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
