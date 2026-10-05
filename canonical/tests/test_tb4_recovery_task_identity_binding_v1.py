from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.tb4_recovery_task_identity_binding_v1 import evaluate
ROOT=Path(__file__).resolve().parents[2]
CUT=json.loads((ROOT/"canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json").read_text())
MAN=json.loads((ROOT/"canonical/governance/TB4_RECOVERY_TASK_IDENTITY_MANIFEST_20261006_V1.json").read_text())
class Tests(unittest.TestCase):
    def test_exact_eight_bind(self):
        out=evaluate(CUT,MAN)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["task_identity_bound"])
        self.assertEqual(out["task_count"],8)
        self.assertFalse(out["protocol_equivalence_bound"])
        self.assertEqual(out["terminal_credit_delta"],0)
    def test_missing_task_fails(self):
        m=copy.deepcopy(MAN); m["tasks"].pop()
        self.assertFalse(evaluate(CUT,m)["pass"])
    def test_wrong_blob_shape_fails(self):
        m=copy.deepcopy(MAN); m["tasks"][0]["git_blob_sha"]="bad"
        out=evaluate(CUT,m); self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("INVALID_BLOB_SHA") for x in out["errors"]))
    def test_resource_drift_fails(self):
        m=copy.deepcopy(MAN); m["tasks"][0]["cpus"]=4
        out=evaluate(CUT,m); self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("RESOURCE_MISMATCH") for x in out["errors"]))
    def test_instruction_exposure_fails(self):
        m=copy.deepcopy(MAN); m["source"]["instruction_files_read"]=1
        out=evaluate(CUT,m); self.assertFalse(out["pass"])
        self.assertIn("NONZERO_INSTRUCTION_FILES_READ",out["errors"])
if __name__=="__main__": unittest.main(verbosity=2)
