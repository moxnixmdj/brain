from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import scientific_artifact_contract_v1 as a

def verified_result():
    return {
        "status":"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",
        "verified":True,
        "family":"SHARED_PERIOD_FITTING",
        "verification":{"pass":True},
        "result":{
            "period":9.0,
            "score":0.001,
            "fits":[
                {"source":"a","r2":0.99,"rmse":0.1},
                {"source":"b","r2":0.98,"rmse":0.2},
            ],
        },
    }

def specs():
    return [
        {"relative_path":"result.json","format":"json","value_path":"result"},
        {"relative_path":"tables/fits.csv","format":"csv","rows_path":"result.fits",
         "columns":[{"name":"source","path":"source"},{"name":"r2","path":"r2"},{"name":"rmse","path":"rmse"}]},
        {"relative_path":"report.md","format":"markdown","title":"Scientific result",
         "fields":[{"label":"Family","path":"family"},{"label":"Period","path":"result.period"},{"label":"Verified","path":"verification.pass"}]},
    ]

class ScientificArtifactContractV1Tests(unittest.TestCase):
    def test_compile_three_declared_formats(self):
        out=a.compile_artifacts(verified_result(),specs())
        self.assertEqual(out["status"],"COMPILED",out)
        self.assertEqual(out["artifact_count"],3)
        for row in out["artifacts"]:
            self.assertEqual(hashlib.sha256(row["bytes"]).hexdigest(),row["sha256"])
            self.assertGreater(row["byte_count"],0)

    def test_materialize_and_readback_exact(self):
        with tempfile.TemporaryDirectory() as td:
            out=a.materialize_artifacts(verified_result(),specs(),td)
            self.assertEqual(out["status"],"PASS__DECLARED_SCIENTIFIC_ARTIFACTS_MATERIALIZED_AND_VERIFIED",out)
            self.assertEqual(out["artifact_count"],3)
            result=json.loads((Path(td)/"result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["period"],9.0)
            csv_text=(Path(td)/"tables/fits.csv").read_text(encoding="utf-8")
            self.assertEqual(csv_text.splitlines()[0],"source,r2,rmse")
            self.assertIn("a,0.99,0.1",csv_text)
            md=(Path(td)/"report.md").read_text(encoding="utf-8")
            self.assertIn("- Period: 9.0",md)

    def test_unverified_source_fails_closed(self):
        raw=verified_result(); raw["verified"]=False
        out=a.compile_artifacts(raw,specs())
        self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","VERIFIED_RESULT_REQUIRED"))

    def test_path_escape_fails_closed(self):
        bad=[{"relative_path":"../escape.json","format":"json","value_path":"result"}]
        out=a.compile_artifacts(verified_result(),bad)
        self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","ARTIFACT_PATH_INVALID"))

    def test_missing_value_path_fails_closed(self):
        bad=[{"relative_path":"x.json","format":"json","value_path":"result.not_here"}]
        out=a.compile_artifacts(verified_result(),bad)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(out["reason"].startswith("VALUE_PATH_MISSING:"))

    def test_duplicate_output_path_fails_closed(self):
        bad=[
            {"relative_path":"x.json","format":"json","value_path":"result"},
            {"relative_path":"x.json","format":"json","value_path":"verification"},
        ]
        out=a.compile_artifacts(verified_result(),bad)
        self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","ARTIFACT_PATH_DUPLICATE"))

if __name__=="__main__":
    unittest.main(verbosity=2)
