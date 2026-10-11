from __future__ import annotations
from hashlib import sha256
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime import professional_task_fulfillment_bridge_v1 as f

def w(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,sort_keys=True))
    return f.git_blob_sha(p)

class Tests(unittest.TestCase):
    def test_one_obligation_requires_independent_scope_and_semantic_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);tid="t";ts="a"*64;art="b"*64
            obs=[{"obligation_id":"O","semantics":"deliver requested conclusion","required":True}]
            dig=f.obligation_universe_digest(obs)
            sid=f.task_scope_id(task_id=tid,task_sha256=ts,obligation_digest=dig)

            scope={"id":"s","target_scope_id":sid,"basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
                   "verified":True,"independent":True,"scope_relation":"EXACT",
                   "complete_target_case_set":True,"universe_identity_bound":True,
                   "case_universe_digest":dig,"obligation_universe_digest":dig,"producer_id":"scope-p"}
            sp=root/"canonical/evidence/scope.json";sb=w(sp,scope)
            scope_verify={"schema":f.SCOPE_VERIFY_SCHEMA,"subject_git_blob_sha":sb,"task_id":tid,
                          "task_sha256":ts,"obligation_universe_digest":dig,"target_scope_id":sid,
                          "scope_complete":True,"pass":True,"independent_verified":True,
                          "scope_complete_verified":True,"independent_verifier_id":"scope-v"}
            svp=root/"canonical/verification/scope.json";svb=w(svp,scope_verify)
            scope_binding={"certificate":{"path":"canonical/evidence/scope.json","git_blob_sha":sb},
                           "verification":{"path":"canonical/verification/scope.json","git_blob_sha":svb}}

            sem=sha256(obs[0]["semantics"].encode()).hexdigest();ev="1"*64
            rec={"schema":f.RECEIPT_SCHEMA,"task_id":tid,"task_sha256":ts,"artifact_sha256":art,
                 "obligation_id":"O","obligation_semantics_sha256":sem,
                 "obligation_universe_digest":dig,"target_scope_id":sid,"verdict":"PASS",
                 "semantic_satisfaction_proved":True,"producer_id":"p","evidence_sha256":ev}
            rp=root/"canonical/evidence/o.json";rb=w(rp,rec)
            ver={"schema":f.VERIFY_SCHEMA,"subject_git_blob_sha":rb,"task_id":tid,"task_sha256":ts,
                 "artifact_sha256":art,"obligation_id":"O","obligation_semantics_sha256":sem,
                 "obligation_universe_digest":dig,"target_scope_id":sid,"evidence_sha256":ev,
                 "pass":True,"independent_verified":True,"semantic_satisfaction_verified":True,
                 "independent_verifier_id":"v"}
            vp=root/"canonical/verification/o.json";vb=w(vp,ver)
            bundle={"task":{"task_id":tid,"task_sha256":ts,"obligations":obs,
                            "obligation_scope_binding":scope_binding},
                    "artifact_sha256":art,
                    "obligation_bindings":[{"obligation_id":"O",
                      "receipt":{"path":"canonical/evidence/o.json","git_blob_sha":rb},
                      "verification":{"path":"canonical/verification/o.json","git_blob_sha":vb}}]}
            out=f.verify(bundle,repo_root=root)
            self.assertTrue(out["pass"],out)

            scope_verify["scope_complete_verified"]=False
            scope_binding["verification"]["git_blob_sha"]=w(svp,scope_verify)
            out=f.verify(bundle,repo_root=root)
            self.assertFalse(out["pass"])

            scope_verify["scope_complete_verified"]=True
            scope_verify["independent_verifier_id"]="scope-p"
            scope_binding["verification"]["git_blob_sha"]=w(svp,scope_verify)
            out=f.verify(bundle,repo_root=root)
            self.assertFalse(out["pass"])

if __name__=="__main__":
    unittest.main()
