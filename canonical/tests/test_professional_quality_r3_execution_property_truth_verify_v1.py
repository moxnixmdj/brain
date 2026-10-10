from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r3_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text())

class R3ExecutionPropertyTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load(v.PINS["manifest"][0])
        cls.public=load(v.PINS["public_render_verify"][0])
        cls.rootv=load(v.PINS["root_binding_verify"][0])
        cls.stepv=load(v.PINS["step_verify"][0])
        cls.step=load(v.PINS["step_binding"][0])
        cls.subject=load(v.PINS["subject"][0])
        cls.preflight=load(v.PINS["preflight"][0])
        bout=v.batch.verify(repo_root=ROOT)
        cls.scope=next(r for r in bout["rows"] if r["leaf_id"]==v.LEAF_ID)
        cls.observed={
            rel:v._blob(ROOT/rel)
            for rel in cls.public["exact_brain_blobs"]
        }

    def eval(self, **kw):
        d=dict(
            manifest=deepcopy(self.manifest),
            public_verify=deepcopy(self.public),
            root_binding_verify=deepcopy(self.rootv),
            step_verify=deepcopy(self.stepv),
            step_binding=deepcopy(self.step),
            subject=deepcopy(self.subject),
            preflight=deepcopy(self.preflight),
            scope_row=deepcopy(self.scope),
            observed_native_blobs=deepcopy(self.observed),
        )
        d.update(kw)
        return v.evaluate_documents(**d)

    def test_current_exact_evidence_passes(self):
        out=v.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["leaf_property_truth_authority"])
        self.assertFalse(out["r3_semantic_leaf_closed"])
        self.assertFalse(out["r3_root_closed"])

    def test_manifest_acceptance_drift_fails(self):
        m=deepcopy(self.manifest)
        for row in m["roots"]:
            if row["root_id"]==v.ROOT_ID:
                row["execution_leaf"]["acceptance"]="WEAKER"
        self.assertEqual(self.eval(manifest=m)["reason"],"R3_EXECUTION_ACCEPTANCE_DRIFT")

    def test_scope_incomplete_fails(self):
        s=deepcopy(self.scope);s["whole_leaf_scope_complete"]=False
        self.assertEqual(self.eval(scope_row=s)["reason"],"R3_WHOLE_LEAF_SCOPE_NOT_CURRENT_AND_COMPLETE")

    def test_native_blob_drift_fails(self):
        o=deepcopy(self.observed)
        k=next(iter(o));o[k]="0"*40
        self.assertEqual(self.eval(observed_native_blobs=o)["reason"],"R3_NATIVE_BLOB_SET_NOT_EXACT_CURRENT")

    def test_missing_near_miss_coverage_fails(self):
        p=deepcopy(self.public)
        p["verified"]=[x for x in p["verified"] if x!="LARGE_DOCX_PAGE_GEOMETRY_MUTATION_IS_REJECTED"]
        self.assertEqual(self.eval(public_verify=p)["reason"],"R3_PUBLIC_CHALLENGE_COVERAGE_INCOMPLETE")

    def test_nonindependent_real_task_receipt_fails(self):
        s=deepcopy(self.stepv);s["producer_verifier_distinct"]=False
        self.assertEqual(self.eval(step_verify=s)["reason"],"R3_REAL_TASK_STEP_RECEIPT_INVALID")

    def test_subject_substitution_fails(self):
        s=deepcopy(self.stepv);s["subject_sha256"]="0"*64
        self.assertEqual(self.eval(step_verify=s)["reason"],"R3_REAL_TASK_STEP_RECEIPT_INVALID")

    def test_root_binding_without_real_task_receipt_fails(self):
        r=deepcopy(self.rootv);r["real_task_render_step_receipt_bound"]=False
        self.assertEqual(self.eval(root_binding_verify=r)["reason"],"R3_ROOT_BINDING_REAL_TASK_RECEIPT_NOT_BOUND")

if __name__=="__main__":
    unittest.main(verbosity=2)
