from __future__ import annotations
import json, tempfile, unittest
from hashlib import sha1
from pathlib import Path
from canonical.runtime.r1_live_architecture_closure_gate_refinement_checker_v1 import verify

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"canonical/governance/R1_LIVE_ARCHITECTURE_CLOSURE_GATE_ABSTRACT_SPEC_20261010_V1.json"
SUB=Path("canonical/runtime/r1_live_architecture_closure_gate_v1.py")

def spec(): return json.loads(SPEC.read_text())
def blob(p):
    b=p.read_bytes(); return sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
def temp_subject(src):
    td=tempfile.TemporaryDirectory(); r=Path(td.name)
    p=r/SUB; p.parent.mkdir(parents=True); p.write_text(src)
    for name in ("unified_cognitive_fabric_v1.py","live_capability_invoker_v1.py","live_brain_runtime_v1.py"):
        q=r/"canonical/runtime"/name; q.write_text("# fixture\n")
    return td,r

class R1RefinementTests(unittest.TestCase):
    def test_current(self):
        o=verify(spec(),repo_root=ROOT)
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["refinement_verified"])
        self.assertEqual(o["branch_witness_count"],53)
        self.assertEqual(o["exception_witness_count"],3)
        self.assertEqual(o["witness_count"],56)
        self.assertFalse(o["repository_wide_refinement"])
        self.assertFalse(o["downstream_capability_semantics_proved"])
        self.assertEqual(o["terminal_credit_delta"],0)
    def test_missing_fixed_error_spec_rejected(self):
        s=spec(); s["fixed_error_classes"].remove("PUBLIC_ENTRYPOINT_DRIFT")
        o=verify(s,repo_root=ROOT)
        self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"FIXED_ERROR_CENSUS_MISMATCH")
    def test_blob_drift_rejected(self):
        td,r=temp_subject((ROOT/SUB).read_text()+"\n")
        try:
            o=verify(spec(),repo_root=r)
            self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"SUBJECT_BLOB_DRIFT")
        finally: td.cleanup()
    def test_lifecycle_condition_mutation_rejected(self):
        src=(ROOT/SUB).read_text().replace('ownership.get("pass") is not True','ownership.get("pass") is True',1)
        td,r=temp_subject(src)
        try:
            s=spec(); s["subject"]["git_blob_sha"]=blob(r/SUB)
            o=verify(s,repo_root=r)
            self.assertFalse(o["pass"])
        finally: td.cleanup()
    def test_success_status_mutation_rejected(self):
        src=(ROOT/SUB).read_text().replace('"PASS__R1_LIVE_ARCHITECTURE_CLOSED_AND_DRIFT_LOCKED"','"PASS__BROKEN"',1)
        td,r=temp_subject(src)
        try:
            s=spec(); s["subject"]["git_blob_sha"]=blob(r/SUB)
            o=verify(s,repo_root=r)
            self.assertFalse(o["pass"]); self.assertEqual(o["reason"],"SUCCESS_PROJECTION_MISMATCH")
        finally: td.cleanup()

if __name__=="__main__": unittest.main(verbosity=2)
