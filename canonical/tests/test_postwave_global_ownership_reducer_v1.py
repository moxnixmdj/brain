import copy,unittest
from pathlib import Path
from canonical.runtime.postwave_global_ownership_reducer_v1 import evaluate,evaluate_documents,WAVE,REDUCTION,MUTATION,COMPOSITION,DEPENDENCY,DONOR,BUNDLE,SOURCES,_load,_blob

class Tests(unittest.TestCase):
    def test_live_branch_evidence_closes(self):
        out=evaluate(Path("."))
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["achieved"],out)
        self.assertFalse(out["terminal_replay_authorized"])
        self.assertEqual(out["derived_counters"]["donor_dependent_required_behaviors"],0)
        self.assertTrue(out["derived_predicates"]["final_donor_deletion_cleanroom_pass"])

    def test_donor_audit_failure_fails_closed(self):
        root=Path(".")
        docs={p:_load(root,p) for p in (*SOURCES,BUNDLE)}
        blobs={p:_blob(root/p) for p in SOURCES}
        donor=copy.deepcopy(docs[DONOR])
        donor["adjudication"]["target_capability_donor_present_in_terminal_execution_closure"]=True
        out=evaluate_documents(docs[WAVE],docs[REDUCTION],docs[MUTATION],docs[COMPOSITION],docs[DEPENDENCY],donor,docs[BUNDLE],current_blobs=blobs)
        self.assertFalse(out["pass"])
        self.assertIn("CHECK_FAILED:terminal_wave_donor_absent",out["errors"])

    def test_bundle_hash_drift_fails_closed(self):
        root=Path(".")
        docs={p:_load(root,p) for p in (*SOURCES,BUNDLE)}
        blobs={p:_blob(root/p) for p in SOURCES}
        bundle=copy.deepcopy(docs[BUNDLE])
        bundle["sources"][WAVE]="0"*40
        out=evaluate_documents(docs[WAVE],docs[REDUCTION],docs[MUTATION],docs[COMPOSITION],docs[DEPENDENCY],docs[DONOR],bundle,current_blobs=blobs)
        self.assertFalse(out["pass"])
        self.assertIn("CHECK_FAILED:proof_bundle_frozen",out["errors"])

    def test_terminal_replay_guard_failure_fails_closed(self):
        root=Path(".")
        docs={p:_load(root,p) for p in (*SOURCES,BUNDLE)}
        blobs={p:_blob(root/p) for p in SOURCES}
        wave=copy.deepcopy(docs[WAVE])
        wave["result_guards"]["tuning_replay"]=True
        out=evaluate_documents(wave,docs[REDUCTION],docs[MUTATION],docs[COMPOSITION],docs[DEPENDENCY],docs[DONOR],docs[BUNDLE],current_blobs=blobs)
        self.assertFalse(out["pass"])
        self.assertIn("CHECK_FAILED:terminal_wave_immutable_pass",out["errors"])

if __name__=="__main__": unittest.main()
