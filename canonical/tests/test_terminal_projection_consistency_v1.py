from __future__ import annotations
import copy, unittest
from canonical.runtime.terminal_projection_consistency_v1 import PATHS,_git_blob_sha,_load,evaluate_documents

class TerminalProjectionConsistencyTests(unittest.TestCase):
    def live(self):
        docs={k:_load(v) for k,v in PATHS.items()}
        shas={v:_git_blob_sha(v) for v in PATHS.values()}
        return docs,shas
    def evaluate(self,docs,shas):
        return evaluate_documents(docs["authority"],docs["closure"],docs["matrix"],docs["atomic_bindings"],
                                  docs["p1_propagation"],docs["delegation_acceptance"],shas)
    def test_live_projection_is_consistent(self):
        docs,shas=self.live(); out=self.evaluate(docs,shas)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["acceptance_closed_families"],3)
        self.assertEqual(out["acceptance_open_families"],16)
        self.assertEqual(out["atomic_predicates_proved"],8)
        self.assertEqual(out["atomic_predicates_unresolved"],30)
        self.assertIn("SUBAGENT_DELEGATION_AND_COORDINATION",out["accepted_families"])
    def test_stale_authority_acceptance_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["truth"]["opus55_acceptance"]="2/19_PASS__17/19_OPEN"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_MISMATCH",out["errors"])
    def test_delegation_cannot_disappear_from_projection(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["closure"]["opus55_acceptance_summary"]["calibrated_families"].remove("SUBAGENT_DELEGATION_AND_COORDINATION")
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH",out["errors"])
    def test_atomic_regression_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["atomic_bindings"]["saturation"]["proved_predicate_count"]=7
        docs["atomic_bindings"]["saturation"]["unresolved_predicate_count"]=31
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("ATOMIC_LEDGER_COUNTS_INVALID",out["errors"])
    def test_stale_planning_artifact_cannot_be_live(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["sources"]["residual_plan"]["status"]="ACTIVE"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("STALE_PLANNING_SOURCE_NOT_DEMOTED:residual_plan",out["errors"])
    def test_ownership_not_implied_by_acceptance(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        row=next(x for x in docs["matrix"]["rows"] if x["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        row["postwave_ownership_credit"]="VERIFIED_OWNED_EQUAL_OR_BETTER"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("MATRIX_DELEGATION_OWNERSHIP_OVERCLAIM",out["errors"])
    def test_stale_blob_pointer_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"]="0"*40
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_SOURCE_BLOB_MISMATCH:terminal_closure_manifest",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
