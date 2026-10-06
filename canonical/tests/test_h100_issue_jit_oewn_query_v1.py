import json, unittest
from pathlib import Path
from canonical.runtime import h100_oewn_lexical_acquisition_v1 as r

ROOT=Path(__file__).resolve().parents[2]
PRE=json.loads((ROOT/"canonical/governance/H100_ISSUE_JIT_OEWN_QUERY_PRECOMMIT_V1.json").read_text())
BASE=json.loads((ROOT/"canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json").read_text())

class T(unittest.TestCase):
    def test_issue_direct_query_resolves_target(self):
        knowledge={
            "schema":"PROJECT_BRAIN_H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1",
            "queries":{
                "issue":{
                    "noun_query_complete":True,
                    "records":PRE["records"],
                }
            },
            "anchors":BASE["anchors"],
        }
        out=r.resolve_lexical_role(PRE["cue"],PRE["context"],knowledge)
        self.assertEqual(out["status"],"ROLE_IDENTIFIED")
        self.assertEqual(out["role"],"TARGET")
        self.assertEqual(out["selected_synsets"],["11430739-n"])
        self.assertEqual(out["persistent_learned_bytes"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
