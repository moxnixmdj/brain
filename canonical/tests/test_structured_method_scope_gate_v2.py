from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/STRUCTURED_METHOD_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json"

class Tests(unittest.TestCase):
    def payload(self):
        return json.loads(INPUT.read_text(encoding="utf-8"))

    def test_current_input_is_admissible(self):
        out=evaluate(self.payload())
        self.assertTrue(out["admissible"],out)
        self.assertEqual(out["errors"],[])
        self.assertEqual(out["covered_interaction_count"],8)

    def test_load_bearing_graph_oracle_leak_fails_closed(self):
        p=self.payload()
        p["candidate_visible_derived_or_oracle_ids"]=["GRAPH_TOPOLOGY"]
        out=evaluate(p)
        self.assertFalse(out["admissible"])
        self.assertTrue(any(x.startswith("LOAD_BEARING_INFERENCE_LEAKED_TO_CANDIDATE") for x in out["errors"]))

    def test_missing_edge_interaction_fails_closed(self):
        p=self.payload()
        p["candidate_interaction_ids"].remove("MATERIAL_EDGE_INDEPENDENT_STRUCTURAL_ACCEPTANCE")
        out=evaluate(p)
        self.assertFalse(out["admissible"])
        self.assertTrue(any(x.startswith("MISSING_REQUIRED_INTERACTIONS") for x in out["errors"]))

    def test_unresolved_rule_grammar_dimension_fails_closed(self):
        p=self.payload()
        p["unresolved_required_dimensions"]=["NORMALIZED_RULE_EXPRESSION_GRAMMAR"]
        out=evaluate(p)
        self.assertFalse(out["admissible"])
        self.assertTrue(any(x.startswith("UNRESOLVED_REQUIRED_DIMENSIONS") for x in out["errors"]))

    def test_target_weakening_fails_closed(self):
        p=self.payload(); p["target_weakened"]=True
        self.assertFalse(evaluate(p)["admissible"])

if __name__=="__main__":
    unittest.main(verbosity=2)
