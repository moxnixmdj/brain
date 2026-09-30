#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
EXTRACT=ROOT/"canonical/runtime/bound_capabilities/relevant_source_evidence_extract.py"
RELATION=ROOT/"canonical/runtime/bound_capabilities/extracted_evidence_claim_relation.py"
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"
INTENT=ROOT/"canonical/action_intents/2026-09-30_REPAIR_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_REMOVE_ROR_GATE_V1.json"

class ExtractionAuthorityGateRepairClosure(unittest.TestCase):
    def test_existing_extraction_contract_is_preserved(self):
        s=EXTRACT.read_text(encoding="utf-8")
        self.assertIn('SCHEMA="PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"',s)
        self.assertIn('"status":"OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED"',s)
        self.assertIn('"record_type":"OBJECTIVE_ANCHORED_TEXT_CLAIM_CANDIDATE"',s)
        self.assertIn('"numeric_literals":nums',s)
        self.assertIn('"authority_identity_status":"OPTIONAL_NOT_REQUIRED"',s)
        self.assertNotIn("_load_relevance",s)

    def test_relation_consumer_accepts_preserved_schema(self):
        s=RELATION.read_text(encoding="utf-8")
        self.assertIn('EXTRACTION_SCHEMA="PROJECT_BRAIN_RELEVANT_SOURCE_EVIDENCE_EXTRACTION_V1"',s)
        self.assertIn('data.get("status")!="OBJECTIVE_ANCHORED_EVIDENCE_EXTRACTED"',s)

    def test_frontend_and_astra_do_not_gate_on_authority_identity(self):
        front=FRONT.read_text(encoding="utf-8")
        astra=ASTRA.read_text(encoding="utf-8")
        self.assertIn('"authority_identity_gate_required":False',front)
        self.assertIn("Generic extraction runs from retrieval provenance",front)
        self.assertNotIn("BLOCKED_ON_AUTHORITY_IDENTITY_AND_OBJECTIVE_RELEVANCE_VERIFICATION",front)
        self.assertNotIn("AUTHORITY_IDENTITY_OR_OBJECTIVE_RELEVANCE_VERIFICATION_REQUIRED",astra)
        self.assertIn("OBJECTIVE_RELEVANCE_OR_RELEVANT_SOURCE_COVERAGE_REQUIRED",astra)

    def test_exact_base_recursive_obs_has_no_unresolved_dominator(self):
        d=json.loads(INTENT.read_text(encoding="utf-8"))
        obs=d["recursive_obs"]
        self.assertEqual(obs["canonical_base_commit"],"adb12d9fc81ab9e2c9653266a7b7d08afe642cf7")
        frontier=obs["route_frontier"]
        self.assertEqual(frontier["unresolved_plausible_dominators"],[])
        self.assertTrue(frontier["selected_route_preflight"]["execution_dependencies_complete"])

if __name__=="__main__":
    unittest.main(verbosity=2)
