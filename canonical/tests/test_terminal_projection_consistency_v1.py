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
                                  docs["predicate_registry"],docs["target_envelope"],shas)

    def test_live_projection_is_count_generic_and_consistent(self):
        docs,shas=self.live(); out=self.evaluate(docs,shas)
        self.assertTrue(out["pass"],out)
        root=docs["authority"]["current_root_partition_override"]
        self.assertEqual(out["acceptance_closed_families"],root["accepted_families"])
        self.assertEqual(out["acceptance_open_families"],root["open_families"])
        self.assertEqual(out["atomic_predicates_proved"],root["proved_atomic"])
        self.assertEqual(out["atomic_predicates_unresolved"],root["unresolved_atomic"])
        self.assertEqual(set(out["baseline_families"]),{"EXACT_SYMBOLIC_COMPUTATION","LONG_HORIZON_MEMORY_AND_CONTINUITY"})
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",out["accepted_families"])
        self.assertIn("SUBAGENT_DELEGATION_AND_COORDINATION",out["accepted_families"])

    def test_canonical_pointer_tracks_current_terminal_authority(self):
        docs,shas=self.live()
        pointer=_load("canonical/CANONICAL_POINTER.json")
        root=docs["authority"]["current_root_partition_override"]
        expected_blocker=(
            f"TERMINAL_FALSE__{root['open_families']}_OF_19_FAMILIES_OPEN__"
            f"{root['unresolved_atomic']}_OF_38_ATOMIC_PREDICATES_UNRESOLVED__"
            "SEE_CURRENT_TERMINAL_AUTHORITY_NEXT_FOR_EXACT_ACTIVE_ROUTE"
        )
        current=pointer["current_frontier"]
        self.assertEqual(current["critical_blocker"],expected_blocker)
        self.assertEqual(current["highest_leverage_capability_gap"],expected_blocker)
        self.assertEqual(current["next_step"],docs["authority"]["next_terminal_action"])

    def test_next_residual_family_closure_is_derived_without_code_change(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        reg=docs["predicate_registry"]; atom=docs["atomic_bindings"]
        target="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        ids=[p["id"] for p in reg["predicates"] if p["family"]==target]
        cmap={x["predicate_id"]:x for x in atom["claims"]}
        for pid in ids:
            if pid not in cmap:
                atom["claims"].append({"predicate_id":pid,"state":"PROVED","scope_complete":True})
            else:
                cmap[pid]["state"]="PROVED"; cmap[pid]["scope_complete"]=True
        atom["saturation"]["proved_predicate_count"]+=sum(1 for pid in ids if pid not in {x["predicate_id"] for x in docs["atomic_bindings"]["claims"]})
        # recompute exact counts after mutation
        proved=sum(1 for p in reg["predicates"] if next((x for x in atom["claims"] if x["predicate_id"]==p["id"] and x.get("state")=="PROVED" and x.get("scope_complete") is True),None))
        atom["saturation"]["proved_predicate_count"]=proved
        atom["saturation"]["unresolved_predicate_count"]=38-proved
        # leave projections stale: generic reducer must detect mismatch, proving the new closure was derived
        out=self.evaluate(docs,shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_MISMATCH",out["errors"])

    def test_stale_authority_acceptance_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["truth"]["opus55_acceptance"]="3/19_PASS__16/19_OPEN"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_MISMATCH",out["errors"])

    def test_scope_incomplete_proved_claim_does_not_count(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        row=next(x for x in docs["atomic_bindings"]["claims"] if x["predicate_id"]=="RECOVERY_TERMINAL_NONINFERIOR")
        row["scope_complete"]=False
        docs["atomic_bindings"]["saturation"]["proved_predicate_count"]=10
        docs["atomic_bindings"]["saturation"]["unresolved_predicate_count"]=28
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ACCEPTANCE_MISMATCH",out["errors"])
        self.assertIn("CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH",out["errors"])

    def test_family_disappearance_from_closure_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["closure"]["opus55_acceptance_summary"]["calibrated_families"].remove("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH",out["errors"])

    def test_ownership_cannot_precede_acceptance(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        row=next(x for x in docs["matrix"]["rows"] if x["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        row["postwave_ownership_credit"]="VERIFIED_OWNED_EQUAL_OR_BETTER"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("MATRIX_OWNERSHIP_WITHOUT_ACCEPTANCE:TOOL_DISCOVERY_SELECTION_AND_LEARNING",out["errors"])

    def test_stale_blob_pointer_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"]="0"*40
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_SOURCE_BLOB_MISMATCH:terminal_closure_manifest",out["errors"])

    def test_registry_predicate_outside_residual_family_fails_closed(self):
        docs,shas=self.live(); docs=copy.deepcopy(docs)
        docs["predicate_registry"]["predicates"][0]["family"]="EXACT_SYMBOLIC_COMPUTATION"
        out=self.evaluate(docs,shas); self.assertFalse(out["pass"])
        self.assertTrue(any(e.startswith("REGISTRY_PREDICATE_FAMILY_NOT_RESIDUAL") for e in out["errors"]))

if __name__=="__main__": unittest.main(verbosity=2)
