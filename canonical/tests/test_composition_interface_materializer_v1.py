from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.composition_interface_materializer_v1 import materialize
ROOT=Path(__file__).resolve().parents[2]
PROTO="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
SHA="eb4bca0fe6a015d49d2854998fbe046c979c7ea9"
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class Tests(unittest.TestCase):
    def test_live_protocol_materializes_exact_literal_roles(self):
        out=materialize(load(PROTO),source_protocol_blob_sha=SHA)
        self.assertEqual(out["status"],"MATERIALIZED_LITERAL_COMPONENT_INTERFACES__ZERO_CREDIT")
        roles={x["role_literal"] for x in out["interfaces"]}
        self.assertEqual(roles,{
          "research","tool use","artifact creation",
          "browser/computer action","memory","recovery",
          "coding","debugging","tool discovery",
          "delegation","evidence synthesis","artifact production",
        })
        self.assertEqual(out["interaction_requirements"],["cross-capability state handoff and rollback"])
        self.assertIn("artifact creation",roles); self.assertIn("artifact production",roles)
        self.assertEqual(len(roles),12)
        self.assertFalse(out["promotion_authority"])
    def test_checked_in_materialization_matches_runtime_exactly(self):
        got=materialize(load(PROTO),source_protocol_blob_sha=SHA)
        want=load("canonical/governance/COMPOSITION_COMPONENT_INTERFACES_V1.json")
        self.assertEqual(got,want)
    def test_protocol_change_invalidates_checked_in_output(self):
        d=copy.deepcopy(load(PROTO))
        row=next(x for x in d["protocols"] if x["family"]=="MULTI_CAPABILITY_COMPOSITION")
        row["task_dimensions"][0]="research+tool use+artifact creation+new role"
        got=materialize(d,source_protocol_blob_sha=SHA)
        self.assertNotEqual(got,load("canonical/governance/COMPOSITION_COMPONENT_INTERFACES_V1.json"))
    def test_malformed_clause_fails_closed(self):
        d=copy.deepcopy(load(PROTO))
        row=next(x for x in d["protocols"] if x["family"]=="MULTI_CAPABILITY_COMPOSITION")
        row["task_dimensions"][0]="research++artifact creation"
        self.assertEqual(materialize(d,source_protocol_blob_sha=SHA)["status"],"FAIL_CLOSED")
if __name__=="__main__": unittest.main(verbosity=2)
