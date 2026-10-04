from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_oewn_lexical_acquisition_v1 import (
    OEWNLexicalError,
    resolve_lexical_role,
)

ROOT=Path(__file__).resolve().parents[1]
KNOW=ROOT/"governance"/"H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json"
PRE=ROOT/"governance"/"H100_OEWN_REAL_LEXICAL_PREEXPOSURE_V1.json"

class H100OEWNLexicalAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.knowledge=json.loads(KNOW.read_text())
        self.pre=json.loads(PRE.read_text())

    def test_all_preexposed_tasks_exact(self):
        self.assertEqual(len(self.pre["tasks"]),9)
        for task in self.pre["tasks"]:
            out=resolve_lexical_role(task["cue"],task["context"],self.knowledge)
            self.assertEqual(out["status"],task["expected_status"],task["task_id"])
            self.assertEqual(out["role"],task["expected_role"],task["task_id"])
            self.assertEqual(out["persistent_learned_bytes"],0)
            self.assertEqual(out["external_frontier_model_calls"],0)
            self.assertEqual(out["external_learned_capability_calls"],0)

    def test_comment_personal_opinion_selects_real_input_synset(self):
        out=resolve_lexical_role("comment","personal opinion belief adds information",self.knowledge)
        self.assertEqual(out["role"],"INPUT")
        self.assertEqual(out["selected_synsets"],["06777755-n"])

    def test_comment_book_sense_is_rejected_not_relabelled(self):
        out=resolve_lexical_role("comment","written explanation criticism illustration book textual material",self.knowledge)
        self.assertEqual(out["status"],"ABSTAIN_LEXICAL_SENSE_UNSUPPORTED")
        self.assertEqual(out["selected_synsets"],["06775422-n"])

    def test_nonqueried_member_does_not_inherit_completeness(self):
        out=resolve_lexical_role("issue","phenomenon follows caused previous",self.knowledge)
        self.assertEqual(out["status"],"ABSTAIN_LEXICAL_QUERY_NOT_PINNED")

    def test_query_incomplete_abstains(self):
        d=json.loads(json.dumps(self.knowledge))
        d["queries"]["input"]["noun_query_complete"]=False
        out=resolve_lexical_role("input","component production",d)
        self.assertEqual(out["status"],"ABSTAIN_LEXICAL_QUERY_INCOMPLETE")

    def test_broken_query_completeness_fails_closed(self):
        d=json.loads(json.dumps(self.knowledge))
        d["queries"]["input"]["records"][0]["members"]=["not-input"]
        with self.assertRaisesRegex(OEWNLexicalError,"QUERY_COMPLETENESS_BROKEN"):
            resolve_lexical_role("input","component production",d)

    def test_mixed_role_pack_without_context_abstains(self):
        d=json.loads(json.dumps(self.knowledge))
        d["queries"]["mixed"]={
          "noun_query_complete":True,
          "records":[
            {"id":"03578305-n","members":["mixed"],"definition":"goes into production","examples":[],"lexname":"noun.artifact"},
            {"id":"03292089-n","members":["mixed"],"definition":"final product","examples":[],"lexname":"noun.artifact"},
          ]
        }
        out=resolve_lexical_role("mixed","",d)
        self.assertEqual(out["status"],"ABSTAIN_LEXICAL_SENSE_AMBIGUOUS")

if __name__=="__main__":
    unittest.main(verbosity=2)
