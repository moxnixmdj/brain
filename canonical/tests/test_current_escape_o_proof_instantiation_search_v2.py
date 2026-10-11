from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import current_escape_o_proof_instantiation_search_v2 as search

GDP="PROWORK_GDPVAL_GE_1846"
AA="PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT"
TB="TB_SCIENCE_GE_58_7"
CURSOR="CODING_CURSORBENCH_GE_57_8"
O=[
"CODING_TB4_GE_66_4","CODING_FRONTIERCODE_GE_54_4",CURSOR,GDP,
"AUTOMATIONBENCH_GE_40","HLE_TOOLS_GE_67_7","CHARTOGRAPHY_TOOLS_GE_89",
"OSWORLD_2_1_PARTIAL_GE_81_8","FINANCE_ACCOUNTING_INDEX_GE_61",
"FINANCE_AGENT_V2_GE_58_59","MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER",
]


def blob(p:Path)->str:
    raw=p.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def write(p:Path,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2)+"\n")


def frontier(root:Path):
    ids=O+[AA,TB]
    m=root/"canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
    write(m,{"schema":search.gate.MANIFEST_SCHEMA,"rows":[{"obligation_id":x} for x in ids]})
    write(root/search.gate.CUT_PATH,{
      "schema":search.gate.CUT_SCHEMA,
      "status":"TEST_O11_Q1_PARKED1",
      "source_bindings":{"manifest":[m.relative_to(root).as_posix(),blob(m)]},
      "current_partition":{
        "total_escape_rows":13,"active_rows":12,"parked_rows":1,
        "active_o_rows":11,"active_q_rows":1,
        "active_o_obligation_ids":O,"active_q_obligation_ids":[AA],"parked_obligation_ids":[TB],
      },
    })


def claim(pid:str):
    return {"policy":{"predicate_id":pid},"evidence":{},"current_identity":{}}


class SearchV2Tests(unittest.TestCase):
    def test_gdpval_is_scanned_as_current_o_and_aa_tb_are_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); frontier(root)
            write(root/"canonical/evidence/claims.json",{
                "claims":[{"claim_spec":claim(GDP)},{"claim_spec":claim(AA)},{"claim_spec":claim(TB)}]
            })
            def verdict(payload,**_):
                return {"pass":payload["obligation_id"]==GDP,"status":"PROVEN" if payload["obligation_id"]==GDP else "OPEN"}
            with patch.object(search.gate,"evaluate",side_effect=verdict):
                out=search.scan(repo_root=root)
        self.assertEqual(out["current_o_count"],11)
        self.assertEqual(out["current_q_count"],1)
        self.assertEqual(out["current_parked_count"],1)
        self.assertEqual(out["candidate_count"],1)
        self.assertEqual(out["proved_obligation_ids"],[GDP])
        self.assertNotIn(AA,[r["obligation_id"] for r in out["candidates"]])
        self.assertNotIn(TB,[r["obligation_id"] for r in out["candidates"]])

    def test_near_miss_preserves_current_o_membership(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); frontier(root)
            write(root/"canonical/governance/candidate.json",{"claim_spec":claim(CURSOR)})
            with patch.object(search.gate,"evaluate",return_value={
                "pass":False,"status":"OPEN__CURRENT_O_OBJECTIVE_ACCEPTANCE","reason":"SCOPE_RECEIPT_MISSING","proof_mode":"THRESHOLD_LOWER_BOUND"
            }):
                out=search.scan(repo_root=root)
        self.assertEqual(out["candidate_count"],1)
        self.assertIn(CURSOR,out["missing_obligation_ids"])
        self.assertEqual(out["near_misses"][CURSOR][0]["gate_reason"],"SCOPE_RECEIPT_MISSING")

    def test_malformed_json_is_non_authoritative(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); frontier(root)
            p=root/"canonical/evidence/bad.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text("{bad")
            out=search.scan(repo_root=root)
        self.assertTrue(out["pass"])
        self.assertEqual(out["parse_failure_count"],1)
        self.assertEqual(out["candidate_count"],0)
        self.assertEqual(out["missing_obligation_count"],11)


if __name__=="__main__":
    unittest.main(verbosity=2)
