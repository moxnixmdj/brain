from __future__ import annotations
import json,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import r2_ror_authority_identity_direct_adequacy_v1 as ror

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical/astra_runtime/tmp"
INP=TMP/"R2_ROR_AUTHORITY_INPUT.json"
OUT=TMP/"R2_ROR_AUTHORITY_OUT.json"
GOAL=("Verify ROR authority identity for candidate in "
      "canonical/astra_runtime/tmp/R2_ROR_AUTHORITY_INPUT.json and save the verified authority identity to "
      "canonical/astra_runtime/tmp/R2_ROR_AUTHORITY_OUT.json.")

class R2RorAuthorityIdentityDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        INP.write_text(json.dumps({"candidate":{"final_url":"https://www.worldbank.org/ext/en/home"}}),encoding="utf-8")
        if OUT.exists(): OUT.unlink()
    def tearDown(self):
        for p in (INP,OUT):
            if p.exists(): p.unlink()

    def test_preflight_binds_exact_single_candidate(self):
        out=ror.preflight({"task_id":"p","goal":GOAL})
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["candidate_host"],"worldbank.org")
        self.assertEqual(out["capability_id"],ror.CAPABILITY_ID)
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_not_applicable(self):
        out=ror.preflight({"task_id":"x","goal":GOAL+" Then trust every claim."})
        self.assertFalse(out["matched"])

    def test_multi_candidate_envelope_fails_closed(self):
        INP.write_text(json.dumps({"candidate":{"url":"https://worldbank.org"},"other":{}}),encoding="utf-8")
        out=ror.preflight({"task_id":"bad","goal":GOAL})
        self.assertTrue(out["matched"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("EXACT_SINGLE_CANDIDATE_ENVELOPE_REQUIRED",out["reason"])

    @patch.object(ror.source_authority_binding_ror,"bind_candidate")
    def test_independent_identity_match_commits(self,producer):
        producer.return_value={
            "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
            "output_verified":True,"candidate_host":"worldbank.org","matched_domain":"worldbank.org",
            "ror_id":"https://ror.org/05vnc7p04","organization_name":"World Bank",
            "organization_types":["funder"],"verification_method":"ROR_V2_EXACT_ACTIVE_DOMAIN_BINDING"
        }
        independent=lambda host:{
            "producer_independent":True,"verified":True,"host":host,
            "ror_id":"https://ror.org/05vnc7p04","organization_name":"World Bank",
            "organization_types":["funder"],"ror_domains":["worldbank.org"],
            "response_sha256":"a"*64
        }
        out=ror.run({"task_id":"ok","goal":GOAL},independent_provider=independent)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["transaction_committed"])
        self.assertEqual(out["ror_id"],"https://ror.org/05vnc7p04")

    @patch.object(ror.source_authority_binding_ror,"bind_candidate")
    def test_independent_identity_mismatch_rolls_back(self,producer):
        OUT.write_bytes(b'{"old":true}')
        producer.return_value={
            "status":"AUTHORITY_IDENTITY_VERIFIED","authority_status":"VERIFIED",
            "output_verified":True,"candidate_host":"worldbank.org","matched_domain":"worldbank.org",
            "ror_id":"https://ror.org/05vnc7p04","organization_name":"World Bank",
            "organization_types":[],"verification_method":"ROR_V2_EXACT_ACTIVE_DOMAIN_BINDING"
        }
        independent=lambda host:{
            "producer_independent":True,"verified":True,"host":host,
            "ror_id":"https://ror.org/000000000","organization_name":"Different",
            "organization_types":[],"ror_domains":["worldbank.org"]
        }
        out=ror.run({"task_id":"bad","goal":GOAL},independent_provider=independent)
        self.assertFalse(out["pass"])
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(OUT.read_bytes(),b'{"old":true}')

if __name__=="__main__":
    unittest.main(verbosity=2)
