from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r10_detection_completeness_falsifier_v1 as f

ROOT=Path(__file__).resolve().parents[2]
GUARD=ROOT/"canonical/runtime/professional_quality_r10_execution_guard_v1.py"
SCOPE=ROOT/"canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_V2_GATE_VERIFY_20261010_V1.json"
ENFORCEMENT=ROOT/"canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_GUARD_VERIFY_20261010_V1.json"

def load(p): return json.loads(p.read_text())

class Tests(unittest.TestCase):
    def docs(self): return load(SCOPE),load(ENFORCEMENT)

    def test_current_exact_evidence_is_falsified_as_property_truth_sufficient(self):
        s,e=self.docs()
        out=f.evaluate(guard_path=GUARD,whole_leaf_scope_verification=s,enforcement_verification=e)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["falsified"])
        self.assertEqual(out["exact_missing_certificate"],"R10_OBSERVATION_TO_DEFEATER_TOTALITY_CERTIFICATE")
        self.assertTrue(out["countermodel"]["same_guard_visible_observation"])
        self.assertTrue(out["countermodel"]["different_property_truth"])
        self.assertFalse(out["new_primitive_required"])

    def test_scope_incompleteness_does_not_support_this_falsifier(self):
        s,e=self.docs(); s=deepcopy(s); s["consequence"]["whole_leaf_scope_complete"]=False
        out=f.evaluate(guard_path=GUARD,whole_leaf_scope_verification=s,enforcement_verification=e)
        self.assertEqual(out["reason"],"WHOLE_LEAF_SCOPE_COMPLETE_REQUIRED")

    def test_detection_interface_drift_fails_closed(self):
        s,e=self.docs()
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"g.py"; p.write_text("def evaluate(*, detected_defeater_ids=()):\n    return {}\n")
            out=f.evaluate(guard_path=p,whole_leaf_scope_verification=s,enforcement_verification=e)
        self.assertEqual(out["reason"],"GUARD_DETECTION_INTERFACE_DRIFT")

    def test_unverified_totality_claim_does_not_defeat_countermodel(self):
        s,e=self.docs()
        cert={"schema":f.TOTALITY_SCHEMA,"leaf_id":f.LEAF_ID,"claim_id":f.CLAIM_ID,"all_material_false_certification_states_observable_or_safe":True}
        verify={"schema":f.TOTALITY_VERIFY_SCHEMA,"leaf_id":f.LEAF_ID,"claim_id":f.CLAIM_ID,"pass":True,"independent":False,"semantic_totality_verified":True}
        out=f.evaluate(guard_path=GUARD,whole_leaf_scope_verification=s,enforcement_verification=e,totality_certificate=cert,totality_verification=verify)
        self.assertTrue(out["falsified"])

    def test_independently_verified_totality_defeats_this_specific_countermodel(self):
        s,e=self.docs()
        cert={"schema":f.TOTALITY_SCHEMA,"leaf_id":f.LEAF_ID,"claim_id":f.CLAIM_ID,"all_material_false_certification_states_observable_or_safe":True}
        verify={"schema":f.TOTALITY_VERIFY_SCHEMA,"leaf_id":f.LEAF_ID,"claim_id":f.CLAIM_ID,"pass":True,"independent":True,"semantic_totality_verified":True}
        out=f.evaluate(guard_path=GUARD,whole_leaf_scope_verification=s,enforcement_verification=e,totality_certificate=cert,totality_verification=verify)
        self.assertFalse(out["falsified"])
        self.assertEqual(out["status"],"NOT_FALSIFIED__INDEPENDENT_DETECTION_TOTALITY_BOUND")

if __name__=="__main__": unittest.main(verbosity=2)
