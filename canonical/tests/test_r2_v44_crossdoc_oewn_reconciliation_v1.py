from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCHED=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V44.json"
R2=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ACT=ROOT/"canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V24.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def blob(path):
    raw=path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()

class Tests(unittest.TestCase):
    def test_all_current_authority_views_bind_v44(self):
        s,r,t=load(SCHED),load(R2),load(TERM)
        sha=blob(SCHED)
        self.assertEqual(r["scheduler_cut"]["git_blob_sha"],sha)
        self.assertEqual(t["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],sha)
        self.assertEqual(t["live_truth"]["current_r2_scheduler_cut"],"ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V44")
        self.assertEqual(t["authoritative_sources"]["current_r2_decision_intelligence"]["scheduler_cut"]["git_blob_sha"],sha)
        self.assertIn("__V44__",r["status"])
        self.assertIn("__V44__",t["authoritative_sources"]["current_r2_decision_intelligence"]["status"])

    def test_direct_route_delta_is_exactly_30_27(self):
        a,r,t=load(ACT),load(R2),load(TERM)
        self.assertEqual(len(a["current_routes"]),30)
        self.assertEqual(a["runtime"],"canonical/runtime/r2_direct_end_to_end_adequacy_v10.py")
        ids={x["route_id"] for x in a["current_routes"]}
        self.assertIn("DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_COMPOSITION_V1",ids)
        self.assertIn("DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1",ids)
        self.assertEqual(r["direct_adequacy"]["current_route_count"],30)
        self.assertEqual(r["direct_adequacy"]["bounded_family_count"],27)
        self.assertEqual(t["live_truth"]["r2_direct_adequacy_route_count"],30)
        self.assertEqual(t["live_truth"]["r2_direct_adequacy_bounded_family_count"],27)

    def test_cross_document_and_oewn_controls_are_bound_without_overclaim(self):
        s,r,t=load(SCHED),load(R2),load(TERM)
        self.assertTrue(s["live_mechanism"]["cross_document_effect_worldset"]["raw_language_hypothesis_completeness_authority"] is False)
        self.assertTrue(s["live_mechanism"]["oewn_decision_sense_control"]["intended_sense_selection_closed_within_authenticated_manifest_scope"])
        self.assertFalse(s["live_mechanism"]["oewn_decision_sense_control"]["open_world_word_sense_closed"])
        self.assertTrue(r["cross_document_effect_worldset_frontier"]["minimum_discriminator_slots_when_outcomes_diverge"])
        self.assertFalse(r["cross_document_effect_worldset_frontier"]["raw_language_hypothesis_completeness_closed"])
        self.assertTrue(r["oewn_decision_sense_frontier"]["exact_minimum_declared_discriminator_when_action_changes"])
        self.assertFalse(r["oewn_decision_sense_frontier"]["open_world_word_sense_closed"])
        rec=t["r2_v44_crossdoc_oewn_reconciliation"]
        self.assertTrue(rec["cross_document_worldsets_bound"])
        self.assertTrue(rec["oewn_decision_sense_control_bound"])
        self.assertFalse(rec["raw_language_hypothesis_completeness_closed"])
        self.assertFalse(rec["open_world_word_sense_closed"])

    def test_finance_residual_is_narrowed_not_erased(self):
        r=load(R2)
        cell=r["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertTrue(cell["state"].startswith("INTERNAL_UNSOLVED"))
        boundary=cell["remaining_boundary"]
        self.assertIn("OEWN_SENSE_CASES_LACKING_AUTHENTICATED_COMPLETE_DECISION_MANIFEST",boundary)
        self.assertIn("RAW_LANGUAGE_CROSS_DOCUMENT_EFFECT_HYPOTHESIS_COMPLETENESS",boundary)
        self.assertIn("OPEN_WORLD_ONTOLOGY_MAPPING",boundary)
        self.assertIn("STRONGER_EXTERNAL_FACT_AUTHENTICATION",boundary)

    def test_zero_credit_and_terminal_false(self):
        t=load(TERM)
        rec=t["r2_v44_crossdoc_oewn_reconciliation"]
        self.assertTrue(rec["terminal_remains_false"])
        self.assertEqual(rec["terminal_credit_delta"],0)
        self.assertFalse(t["live_truth"]["terminal"])

if __name__=="__main__":
    unittest.main(verbosity=2)
