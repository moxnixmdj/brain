from __future__ import annotations
import copy, unittest
from pathlib import Path
from canonical.runtime.ownership_escrow_guard_v1 import evaluate, load

ROOT=Path(__file__).resolve().parents[2]
CLOSURE=ROOT/"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
MATRIX=ROOT/"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"

class OwnershipEscrowGuardV1Tests(unittest.TestCase):
    def live(self):
        return load(CLOSURE),load(MATRIX)

    def test_live_state_has_zero_accepted_unowned_backlog(self):
        out=evaluate(*self.live())
        self.assertTrue(out["pass"])
        self.assertEqual(out["counts"]["families"],19)
        self.assertEqual(out["counts"]["strictly_accepted"],5)
        self.assertEqual(out["counts"]["verified_owned"],5)
        self.assertEqual(out["counts"]["accepted_owned"],5)
        self.assertEqual(out["counts"]["accepted_blocked_exact"],0)
        self.assertEqual(out["counts"]["accepted_unclassified"],0)

    def test_acceptance_without_ownership_or_exact_blocker_fails(self):
        c,m=map(copy.deepcopy,self.live())
        fam="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        next(x for x in m["rows"] if x["family"]==fam)["status"]="OWNED_COMPONENT_NOT_FULL_FAMILY"
        next(x for x in c["families"] if x["id"]==fam)["ownership_status"]="OWNERSHIP_PROMOTION_SEPARATE"
        out=evaluate(c,m)
        self.assertFalse(out["pass"])
        row=next(x for x in out["families"] if x["family"]==fam)
        self.assertEqual(row["ownership_outcome"],"UNCLASSIFIED_ACCEPTED_UNOWNED")
        self.assertIn("OWNERSHIP_ESCROW_MISSING",row["errors"])

    def test_exact_blocker_is_valid_classified_escrow(self):
        c,m=map(copy.deepcopy,self.live())
        fam="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        next(x for x in m["rows"] if x["family"]==fam)["status"]="OWNED_COMPONENT_NOT_FULL_FAMILY"
        row=next(x for x in c["families"] if x["id"]==fam)
        row["ownership_status"]="OWNERSHIP_BLOCKED_EXACT"
        row["ownership_escrow"]={
            "state":"OWNERSHIP_BLOCKED_EXACT",
            "blocker_class":"EXACT_RUNTIME_PROVIDER_BOUNDARY_UNPROVED",
            "missing_proof_obligations":["PROVE_EXACT_RUNTIME_PROVIDER_BOUNDARY"],
            "next_action":"RUN_MINIMUM_PROVIDER_BOUNDARY_PROOF",
            "ownership_credit_delta":0,
        }
        out=evaluate(c,m)
        self.assertTrue(out["pass"])
        self.assertEqual(out["counts"]["accepted_blocked_exact"],1)
        self.assertEqual(out["counts"]["accepted_unclassified"],0)

    def test_ownership_without_acceptance_fails(self):
        c,m=map(copy.deepcopy,self.live())
        fam="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        row=next(x for x in c["families"] if x["id"]==fam)
        row["opus55_acceptance_state"]="OPEN"
        row["opus55_acceptance_calibrated"]=False
        row["unresolved"]=["SYNTHETIC_REOPEN"]
        out=evaluate(c,m)
        self.assertFalse(out["pass"])
        got=next(x for x in out["families"] if x["family"]==fam)
        self.assertIn("OWNERSHIP_WITHOUT_STRICT_ACCEPTANCE",got["errors"])

if __name__=="__main__":
    unittest.main()
