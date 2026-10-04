from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.h100_lexical_source_fallback_v1 import LexicalSourceFallbackError, resolve_source_relations

ROOT=Path(__file__).resolve().parents[1]
KNOW=ROOT/"governance"/"H100_LEXICAL_SOURCE_FALLBACK_KNOWLEDGE_V1.json"
PRE=ROOT/"governance"/"H100_LEXICAL_SOURCE_FALLBACK_PREEXPOSURE_V1.json"

class H100LexicalSourceFallbackTests(unittest.TestCase):
    def setUp(self):
        self.knowledge=json.loads(KNOW.read_text())
        self.pre=json.loads(PRE.read_text())

    def _records(self,term):
        return [r for r in self.knowledge["records"] if r["term"]==term]

    def test_observed_missing_terms_repaired(self):
        self.assertEqual(len(self.pre["tasks"]),2)
        for task in self.pre["tasks"]:
            out=resolve_source_relations(task["term"],self._records(task["term"]))
            self.assertEqual(out["status"],task["expected_status"])
            self.assertEqual(out["role"],task["expected_role"])
            self.assertEqual(out["persistent_learned_bytes"],0)
            self.assertEqual(out["external_frontier_model_calls"],0)
            self.assertEqual(out["external_learned_capability_calls"],0)

    def test_runtime_is_term_generic(self):
        out=resolve_source_relations("fresh_term",[{"term":"fresh_term","source_id":"s","relation_phrases":["predictor variable"]}])
        self.assertEqual((out["status"],out["role"]),("ROLE_IDENTIFIED","INPUT"))

    def test_target_relation_generic(self):
        out=resolve_source_relations("fresh_target",[{"term":"fresh_target","source_id":"s","relation_phrases":["response variable"]}])
        self.assertEqual(out["role"],"TARGET")

    def test_conflicting_relations_abstain(self):
        out=resolve_source_relations("x",[
          {"term":"x","source_id":"a","relation_phrases":["predictor variable"]},
          {"term":"x","source_id":"b","relation_phrases":["response variable"]}
        ])
        self.assertEqual(out["status"],"ABSTAIN_SOURCE_ROLE_CONFLICT")

    def test_unknown_relation_abstains(self):
        out=resolve_source_relations("x",[{"term":"x","source_id":"a","relation_phrases":["mysterious relation"]}])
        self.assertEqual(out["status"],"ABSTAIN_SOURCE_RELATION_UNSUPPORTED")

    def test_term_mismatch_fails_closed(self):
        with self.assertRaisesRegex(LexicalSourceFallbackError,"RECORD_TERM_MISMATCH"):
            resolve_source_relations("x",[{"term":"y","source_id":"s","relation_phrases":["predictor variable"]}])

if __name__=="__main__":
    unittest.main(verbosity=2)
