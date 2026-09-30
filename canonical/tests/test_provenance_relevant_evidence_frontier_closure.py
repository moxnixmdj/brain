#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
ASTRA=ROOT/"canonical/runtime/astra_runtime.py"
FRONT=ROOT/"canonical/runtime/bound_capabilities/open_research_source_frontend.py"
EXTRACT=ROOT/"canonical/runtime/bound_capabilities/provenance_relevant_evidence_extract.py"
INTENT=ROOT/"canonical/action_intents/2026-09-30_ACQUIRE_PROVENANCE_RELEVANT_EVIDENCE_EXTRACTION_V1.json"

class ProvenanceRelevantEvidenceFrontierClosure(unittest.TestCase):
    def test_extractor_has_no_authority_admission_argument(self):
        s=EXTRACT.read_text(encoding="utf-8")
        self.assertIn("def extract(objective,candidate,provenance,timeout=20,max_units=8,fetch=None):",s)
        self.assertNotIn("QUALIFIED_AUTHORITY_IDENTITY_REQUIRED",s)
        self.assertIn('"authority_identity_status":"OPTIONAL_NOT_REQUIRED"',s)

    def test_frontend_advances_extraction_only_to_relation_evaluation(self):
        s=FRONT.read_text(encoding="utf-8")
        self.assertIn("provenance_relevant_evidence_extract",s)
        self.assertIn("MODEL_INDEPENDENT_EVIDENCE_RELATION_EVALUATION",s)
        self.assertIn('"authority_identity_gate_required":False',s)
        self.assertIn('"evidence_relation_claims_made":False',s)
        self.assertIn('"factual_correctness_claims_made":False',s)
        self.assertIn('"evidence_sufficiency_claims_made":False',s)

    def test_astra_prefers_extracted_evidence_before_relevance_fallback(self):
        s=ASTRA.read_text(encoding="utf-8")
        count=s.index('source_frontend.get("evidence_extracted_candidate_count")')
        ready=s.index("OPEN_ENDED_RESEARCH_GROUNDED_EVIDENCE_READY__",count)
        relation=s.index("EVIDENCE_RELATION_EVALUATION_REQUIRED",ready)
        relevant=s.index("OPEN_ENDED_RESEARCH_RELEVANT_SOURCE_READY__",relation)
        self.assertLess(ready,relevant)
        self.assertNotIn("AUTHORITY_IDENTITY_OR_OBJECTIVE_RELEVANCE_VERIFICATION_REQUIRED",s[ready:])

    def test_exact_base_recursive_obs_is_present(self):
        d=json.loads(INTENT.read_text(encoding="utf-8"))
        obs=d["recursive_obs"]
        self.assertEqual(obs["canonical_base_commit"],"8c4d76e62cee474fc97844d59c12aa907b7ba44f")
        self.assertEqual(obs["route_frontier"]["unresolved_plausible_dominators"],[])
        self.assertTrue(obs["route_frontier"]["selected_route_preflight"]["execution_dependencies_complete"])

if __name__=="__main__":
    unittest.main(verbosity=2)
