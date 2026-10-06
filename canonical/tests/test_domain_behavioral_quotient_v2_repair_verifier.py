from __future__ import annotations
import copy
import json
import unittest
from pathlib import Path
from canonical.runtime.domain_behavioral_quotient_v2_repair_verifier import (
    DomainQuotientRepairError, verify, BIOLOGY, VISION_FAMILY, VISION_TRANSFORM
)

ROOT=Path(__file__).resolve().parents[2]
V1_PATH=ROOT/"canonical/governance/OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V1.json"
V2_PATH=ROOT/"canonical/governance/OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V2.json"
V1_SHA="101f6766913ae31168c9d11be0f10e5b2a0b3bec"
CX_SHA="f303a29fa9de86e95cdf62ea0af85f22e52d7271"

def docs():
    return json.loads(V1_PATH.read_text()), json.loads(V2_PATH.read_text())

class RepairVerifierTests(unittest.TestCase):
    def test_current_repair_passes(self):
        v1,v2=docs()
        out=verify(v1,v2,v1_blob_sha=V1_SHA,counterexample_blob_sha=CX_SHA)
        self.assertFalse(out["semantic_losslessness_proved"])
        self.assertEqual(out["terminal_credit_delta"],0)

    def test_nonbiology_drift_fails(self):
        v1,v2=docs()
        x=copy.deepcopy(v2)
        row=next(r for r in x["mappings"] if r["surface"]=="CYBERSECURITY")
        row["new_family_required"]=True
        with self.assertRaises(DomainQuotientRepairError):
            verify(v1,x,v1_blob_sha=V1_SHA,counterexample_blob_sha=CX_SHA)

    def test_extra_biology_family_fails(self):
        v1,v2=docs()
        x=copy.deepcopy(v2)
        row=next(r for r in x["mappings"] if r["surface"]==BIOLOGY)
        row["existing_family_union"].append("INVENTED_FAMILY")
        with self.assertRaises(DomainQuotientRepairError):
            verify(v1,x,v1_blob_sha=V1_SHA,counterexample_blob_sha=CX_SHA)

    def test_credit_inflation_fails(self):
        v1,v2=docs()
        x=copy.deepcopy(v2)
        x["accounting"]["capability_credit_delta"]=1
        with self.assertRaises(DomainQuotientRepairError):
            verify(v1,x,v1_blob_sha=V1_SHA,counterexample_blob_sha=CX_SHA)

if __name__=="__main__":
    unittest.main(verbosity=2)
