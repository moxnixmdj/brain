from __future__ import annotations
import copy, json
from pathlib import Path
import unittest

from canonical.runtime.current_terminal_information_dominance_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def inputs():
    return (
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
    )

class CurrentTerminalInformationDominanceV2Tests(unittest.TestCase):
    def test_live_27_world_and_exact_dominance(self):
        out=evaluate(*inputs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["live_world_summary"],{
            "frozen_predicates":38,
            "proved_predicates":11,
            "unresolved_predicates":27,
            "live_certificate_count":16,
            "live_action_coverage_count":27,
        })
        d=out["dominance"]
        self.assertEqual(d["status"],"EXACT_INFORMATION_DOMINANCE_COMPUTED")
        self.assertEqual(d["unresolved_predicate_count"],27)
        self.assertEqual(d["certificate_count"],16)
        self.assertEqual(d["dominated_certificate_ids"],[])
        self.assertEqual(len(d["nondominated_certificate_ids"]),16)
        self.assertEqual(d["highest_direct_coverage_count"],8)
        self.assertEqual(d["highest_direct_coverage_certificate_ids"],["MATCHED_SCOPE_BINDING_CERTIFICATE"])
        self.assertEqual(d["best_full_frontier_bundle"]["covered_predicate_count"],27)
        self.assertEqual(d["best_full_frontier_bundle"]["unique_requirement_count"],19)
        self.assertEqual(d["best_full_frontier_bundle"]["new_reality_units"],0.0)
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["new_reality_units_consumed"],0)

    def test_recovery_predicates_are_removed_from_live_matched_certificate(self):
        out=evaluate(*inputs())
        front={x["certificate_id"]:x for x in out["dominance"]["single_certificate_structural_front"]}
        matched=front["MATCHED_SCOPE_BINDING_CERTIFICATE"]
        self.assertEqual(matched["covered_predicate_count"],8)
        for pid in (
            "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "RECOVERY_TERMINAL_NONINFERIOR",
            "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        ):
            self.assertNotIn(pid,matched["covered_predicates"])

    def test_authority_count_drift_fails_closed(self):
        args=list(inputs())
        authority=copy.deepcopy(args[5])
        authority["atomic_acceptance_frontier"]["unresolved"]=30
        args[5]=authority
        out=evaluate(*args)
        self.assertFalse(out.get("pass",False),out)
        self.assertEqual(out["status"],"FAIL_CLOSED__LIVE_WORLD_INVALID")
        self.assertIn("UNRESOLVED_COUNT_NE_AUTHORITY:27:30",out["live_world"]["errors"])

    def test_evidence_drift_fails_closed_against_authority(self):
        args=list(inputs())
        evidence=copy.deepcopy(args[1])
        row=next(x for x in evidence["claims"] if x["predicate_id"]=="RECOVERY_TERMINAL_NONINFERIOR")
        row["state"]="OPEN"
        args[1]=evidence
        out=evaluate(*args)
        self.assertFalse(out.get("pass",False),out)
        self.assertIn("PROVED_COUNT_NE_AUTHORITY:10:11",out["live_world"]["errors"])
        self.assertIn("UNRESOLVED_COUNT_NE_AUTHORITY:28:27",out["live_world"]["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
