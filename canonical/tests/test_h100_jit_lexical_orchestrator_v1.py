import json, unittest
from pathlib import Path
from canonical.runtime import h100_jit_lexical_orchestrator_v1 as r

ROOT=Path(__file__).resolve().parents[2]
OEWN=json.loads((ROOT/"canonical/governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json").read_text())
FALL=json.loads((ROOT/"canonical/governance/H100_LEXICAL_SOURCE_FALLBACK_KNOWLEDGE_V1.json").read_text())

class H100JITLexicalOrchestratorTests(unittest.TestCase):
    def test_oewn_hit(self):
        out=r.resolve(term="input",oewn_knowledge=OEWN)
        self.assertEqual((out["status"],out["role"]),("ROLE_IDENTIFIED","INPUT"))

    def test_oewn_miss_fallback_hit(self):
        records=[x for x in FALL["records"] if x["term"]=="covariate"]
        out=r.resolve(term="covariate",oewn_knowledge=OEWN,source_records=records)
        self.assertEqual((out["status"],out["role"]),("ROLE_IDENTIFIED","INPUT"))
        self.assertIn("LEXICAL_SOURCE_FALLBACK",out["successful_routes"])

    def test_cross_source_conflict_abstains(self):
        records=[{"term":"input","source":"synthetic-conflict-control","relation_phrases":["dependent variable"]}]
        out=r.resolve(term="input",oewn_knowledge=OEWN,source_records=records)
        self.assertEqual(out["status"],"ABSTAIN_SOURCE_ROLE_CONFLICT")
        self.assertIsNone(out["role"])

    def test_no_evidence_abstains(self):
        out=r.resolve(term="novel_unbound_token")
        self.assertEqual(out["status"],"ABSTAIN_NO_VERIFIED_LEXICAL_ROLE")
        self.assertEqual(out["persistent_learned_bytes"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
