from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.action_hypergraph_open_predicate_guard_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def fixture(self):
        registry={"predicates":[{"id":"A"},{"id":"B"},{"id":"C"}]}
        evidence={"claims":[
            {"predicate_id":"A","state":"PROVED"},
            {"predicate_id":"B","state":"EXTERNAL_BLOCKED"},
        ]}
        actions={"actions":[{"id":"X","target_predicates":["B","C"]}]}
        return registry,evidence,actions

    def test_open_and_blocked_targets_allowed(self):
        r,e,a=self.fixture()
        out=evaluate(r,e,a)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["checked_target_count"],2)

    def test_proved_target_fails_closed(self):
        r,e,a=self.fixture()
        a["actions"][0]["target_predicates"].append("A")
        out=evaluate(r,e,a)
        self.assertFalse(out["pass"])
        self.assertIn("STALE_TERMINAL_TARGET:X:A:PROVED",out["errors"])

    def test_unknown_target_fails_closed(self):
        r,e,a=self.fixture()
        a["actions"][0]["target_predicates"].append("Z")
        out=evaluate(r,e,a)
        self.assertFalse(out["pass"])
        self.assertIn("UNKNOWN_TARGET_PREDICATE:X:Z",out["errors"])

    def test_live_frontier_excludes_closed_tool_learning(self):
        r=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        e=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        a=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
        out=evaluate(r,e,a)
        self.assertTrue(out["pass"],out)
        targets={
            p
            for action in a["actions"]
            for p in action.get("target_predicates",[])
        }
        self.assertNotIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",targets)
        claim=next(c for c in e["claims"] if c["predicate_id"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertEqual(claim["state"],"PROVED")

    def test_reinserting_closed_tool_learning_is_rejected(self):
        r=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        e=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        a=load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json")
        a=copy.deepcopy(a)
        x=next(z for z in a["actions"] if z["id"]=="SEARCH_SCOPE_COMPLETE_STRONGER_PROOFS_FOR_MATCHED_RESIDUAL")
        x["target_predicates"].append("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        out=evaluate(r,e,a)
        self.assertFalse(out["pass"])
        self.assertTrue(any("STALE_TERMINAL_TARGET" in x for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
