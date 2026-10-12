from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
import tempfile, unittest
from unittest.mock import patch
from canonical.runtime import current_escape_o11_proof_instantiation_search_v1 as search

O1="CODING_TB4_GE_66_4"; O2="AUTOMATIONBENCH_GE_40"
Q1="PROWORK_GDPVAL_GE_1846"; Q2="PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT"

def blob(p):
    raw=p.read_bytes(); return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2)+"\n")

def frontier(root):
    ids=[O1,O2,Q1,Q2]+[f"O{i}" for i in range(9)]
    assert len(ids)==13
    m=root/"canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
    write(m,{"schema":search.gate.MANIFEST_SCHEMA,"rows":[{"obligation_id":x} for x in ids]})
    write(root/"canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json",{
        "schema":search.gate.OQ_SCHEMA,"status":"TEST",
        "source_manifest":{"path":m.relative_to(root).as_posix(),"git_blob_sha":blob(m)},
        "reduction":{"O_OBJECTIVE_ACCEPTANCE":11,"Q_QUALITATIVE_RELATIVE_ORDER":2,"Q_rows":[Q1,Q2]},
    })

def claim(pid):
    return {"policy":{"predicate_id":pid},"evidence":{"x":1},"current_identity":{"x":1}}

class SearchTests(unittest.TestCase):
    def test_discovers_gates_and_excludes_q(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); frontier(root)
            e=root/"canonical/evidence/c.json"; write(e,{"x":[{"claim_spec":claim(O1)},{"claim_spec":claim(O2)},{"claim_spec":claim(Q1)}]})
            def verdict(payload,**_):
                ok=payload["obligation_id"]==O1
                return {"pass":ok,"status":"PROVEN" if ok else "OPEN","reason":None if ok else "MISSING","proof_mode":"THRESHOLD_LOWER_BOUND"}
            with patch.object(search.gate,"evaluate",side_effect=verdict):
                out=search.scan(repo_root=root)
            expected_blob=blob(e)
        self.assertEqual(out["candidate_count"],2); self.assertEqual(out["proved_obligation_ids"],[O1])
        self.assertIn(O2,out["missing_obligation_ids"]); self.assertEqual(out["near_misses"][O2][0]["gate_reason"],"MISSING")
        row=next(r for r in out["candidates"] if r["obligation_id"]==O1)
        self.assertEqual(row["source_git_blob_sha"],expected_blob); self.assertFalse(out["acceptance_authority"])

    def test_groups_multirow_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); frontier(root)
            write(root/"canonical/verification/shared.json",{"claims":[claim(O1),claim(O2)]})
            with patch.object(search.gate,"evaluate",return_value={"pass":True,"status":"PROVEN","proof_mode":"SCOPE_SUPERSET"}):
                out=search.scan(repo_root=root)
        self.assertEqual(out["proved_obligation_count"],2); self.assertEqual(len(out["multi_row_proof_sources"]),1)

    def test_malformed_json_is_non_authoritative(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); frontier(root)
            p=root/"canonical/evidence/bad.json"; p.parent.mkdir(parents=True); p.write_text("{bad")
            out=search.scan(repo_root=root)
        self.assertTrue(out["pass"]); self.assertEqual(out["parse_failure_count"],1); self.assertEqual(out["candidate_count"],0)
        self.assertEqual(out["missing_obligation_count"],11)

if __name__=="__main__": unittest.main(verbosity=2)
