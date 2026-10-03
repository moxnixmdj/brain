from __future__ import annotations
import copy, unittest
from canonical.runtime.terminal_projection_consistency_v1 import PATHS,_git_blob_sha,_load,evaluate_documents,RECOVERY

class TerminalProjectionConsistencyTests(unittest.TestCase):
    def live(self):
        docs={k:_load(v) for k,v in PATHS.items()}
        shas={v:_git_blob_sha(v) for v in PATHS.values()}
        return docs,shas
    def evaluate(self,docs,shas):
        return evaluate_documents(
            docs["authority"],docs["closure"],docs["matrix"],docs["atomic_bindings"],
            docs["p1_restoration"],docs["delegation_acceptance"],docs["recovery_acceptance"],
            docs["recovery_integrator"],shas,
        )
    def test_live_projection_is_consistent(self):
        docs,shas=self.live(); out=self.evaluate(docs,shas)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["acceptance_closed_families"],4)
        self.assertEqual(out["acceptance_open_families"],15)
        self.assertEqual(out["atomic_predicates_proved"],11)
        self.assertEqual(out["atomic_predicates_unresolved"],27)
        self.assertTrue(out["p1_whole_scope_restored"])
        self.assertEqual(out["verified_owned_family_count"],2)
        self.assertIn("SUBAGENT_DELEGATION_AND_COORDINATION",out["accepted_families"])
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",out["accepted_families"])
    def test_stale_authority_acceptance_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["truth"]["opus55_acceptance"]="3/19_PASS__16/19_OPEN"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_MISMATCH",out["errors"])
    def test_recovery_cannot_disappear_from_projection(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["closure"]["opus55_acceptance_summary"]["calibrated_families"].remove("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH",out["errors"])
    def test_atomic_regression_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["atomic_bindings"]["saturation"]["proved_predicate_count"]=10
        docs["atomic_bindings"]["saturation"]["unresolved_predicate_count"]=28
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("ATOMIC_LEDGER_COUNTS_INVALID",out["errors"])
    def test_recovery_source_cannot_regress_to_old_receipt(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        row=next(x for x in docs["atomic_bindings"]["claims"] if x.get("predicate_id") in RECOVERY)
        row["source_path"]="canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_ACCEPTANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("RECOVERY_ATOMIC_SOURCE_PATH_MISMATCH") for x in out["errors"]))
    def test_ownership_not_implied_by_acceptance(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        row=next(x for x in docs["matrix"]["rows"] if x["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        row["postwave_ownership_credit"]="VERIFIED_OWNED_EQUAL_OR_BETTER"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("MATRIX_OWNERSHIP_OVERCLAIM:SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",out["errors"])
    def test_stale_blob_pointer_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"]="0"*40
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_SOURCE_BLOB_MISMATCH:terminal_closure_manifest",out["errors"])
    def test_p1_restoration_is_load_bearing(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["p1_restoration"]["verified"]["whole_p1_contract_restored"]=False
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("P1_WHOLE_SCOPE_NOT_RESTORED",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
