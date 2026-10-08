from __future__ import annotations
import json, unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_pypi_provenance_direct_adequacy_v1 as prov

ROOT=Path(__file__).resolve().parents[2]
SEL=ROOT/"canonical/astra_runtime/tmp/PYPI_PROVENANCE_VERIFY_SELECTION.json"
META=ROOT/"canonical/astra_runtime/tmp/PYPI_PROVENANCE_VERIFY_METADATA.json"
OUT=ROOT/"canonical/astra_runtime/tmp/R2_PYPI_PROVENANCE_REPORT.json"
GOAL=("Audit PyPI provenance using selection "
      "canonical/astra_runtime/tmp/PYPI_PROVENANCE_VERIFY_SELECTION.json, metadata "
      "canonical/astra_runtime/tmp/PYPI_PROVENANCE_VERIFY_METADATA.json, and save the verified report to "
      "canonical/astra_runtime/tmp/R2_PYPI_PROVENANCE_REPORT.json.")

class R2PypiProvenanceDirectAdequacyV1Tests(unittest.TestCase):
    def tearDown(self):
        if OUT.exists(): OUT.unlink()

    def test_preflight_binds_canonical_fixture(self):
        out=prov.preflight({"task_id":"p","goal":GOAL})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["capability_id"],prov.CAPABILITY_ID)
        self.assertEqual(out["project"],"pypdf")
        self.assertEqual(out["version"],"6.19.0")
        self.assertEqual(out["recorded_hash"],"7e5d6e730e7dae87d560a2cee218b852f6498c8be61966f3cd02ead971e48d14")
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_not_applicable(self):
        out=prov.preflight({"task_id":"x","goal":GOAL+" Then install it."})
        self.assertFalse(out["matched"])

    @patch.object(prov.pypi_provenance_audit,"run")
    def test_independent_hash_equality_commits(self,producer):
        pf=prov.preflight({"task_id":"ok","goal":GOAL})
        def fake(*args,**kwargs):
            report={
              "schema":"PROJECT_BRAIN_PYPI_PROVENANCE_AUDIT_V1",
              "capability_id":pf["audited_capability_id"],
              "project":pf["project"],
              "pinned_version":pf["version"],
              "wheel_filename":pf["wheel_filename"],
              "recorded_hash":pf["recorded_hash"],
              "live_metadata_hash":pf["recorded_hash"],
              "downloaded_artifact_hash":pf["recorded_hash"],
              "metadata_url":pf["metadata_url"],
              "verified":True
            }
            OUT.write_text(json.dumps(report),encoding="utf-8")
            return {
              "verified":True,"report_path":pf["report_path"],
              "capability_id":pf["audited_capability_id"],
              "recorded_hash":pf["recorded_hash"],
              "live_metadata_hash":pf["recorded_hash"],
              "downloaded_artifact_hash":pf["recorded_hash"]
            }
        producer.side_effect=fake
        independent=lambda p:{
          "verified":True,"producer_independent":True,
          "recorded_hash":p["recorded_hash"],
          "live_metadata_hash":p["recorded_hash"],
          "downloaded_artifact_hash":p["recorded_hash"],
          "artifact_bytes":395480
        }
        out=prov.run({"task_id":"ok","goal":GOAL},independent_verifier=independent)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["transaction_committed"])

    @patch.object(prov.pypi_provenance_audit,"run")
    def test_independent_hash_mismatch_rolls_back(self,producer):
        pf=prov.preflight({"task_id":"bad","goal":GOAL})
        OUT.write_bytes(b'{"old":true}')
        def fake(*args,**kwargs):
            report={
              "capability_id":pf["audited_capability_id"],"project":pf["project"],
              "pinned_version":pf["version"],"wheel_filename":pf["wheel_filename"],
              "recorded_hash":pf["recorded_hash"],"live_metadata_hash":pf["recorded_hash"],
              "downloaded_artifact_hash":pf["recorded_hash"],"metadata_url":pf["metadata_url"],
              "verified":True
            }
            OUT.write_text(json.dumps(report),encoding="utf-8")
            return {
              "verified":True,"report_path":pf["report_path"],
              "capability_id":pf["audited_capability_id"],
              "recorded_hash":pf["recorded_hash"],
              "live_metadata_hash":pf["recorded_hash"],
              "downloaded_artifact_hash":pf["recorded_hash"]
            }
        producer.side_effect=fake
        independent=lambda p:{
          "verified":False,"producer_independent":True,
          "recorded_hash":p["recorded_hash"],
          "live_metadata_hash":p["recorded_hash"],
          "downloaded_artifact_hash":"0"*64
        }
        out=prov.run({"task_id":"bad","goal":GOAL},independent_verifier=independent)
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(OUT.read_bytes(),b'{"old":true}')

if __name__=="__main__":
    unittest.main(verbosity=2)
