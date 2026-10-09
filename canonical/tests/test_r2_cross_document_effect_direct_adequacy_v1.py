from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_calculus_v1 as c
from canonical.runtime import r2_cross_document_effect_direct_adequacy_v1 as d

def _canon_sha(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def _effect(eid,cls,value,*,cond=None,start=None,sup=None):
    return {"effect_id":eid,"target_id":"threshold","effect_class":cls,"value":value,
            "conditions":cond or {},"valid_from":start,"valid_until":None,
            "supersedes":sup or [],"source_locator":"section:"+eid}

def _doc(did,effects):
    return {"schema":c.DOC_SCHEMA,"document_id":did,"effects":effects}

def _goal():
    return ("Using the cross-document effect case at canonical/tmp/case.json, "
            "compute and independently verify the effective value and save it to "
            "canonical/tmp/out.json.")

def _write(root:Path,*,conflict=False):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    a=_doc("A",[_effect("A.t","DEFINE","10")])
    if conflict:
        b=_doc("B",[_effect("B.t","DEFINE","11")])
    else:
        b=_doc("B",[_effect("B.t","REPLACE","12",start="2026-07-01",sup=["A.t"])])
    cc=_doc("C",[_effect("C.t","EXCEPTION","8",cond={"small":True},start="2026-07-01",
                           sup=[] if conflict else ["B.t"])])
    if conflict:
        cc=_doc("C",[_effect("C.t","DEFINE","13")])
    docs={"canonical/tmp/A.json":a,"canonical/tmp/B.json":b,"canonical/tmp/C.json":cc}
    for rel,obj in docs.items():
        (root/rel).write_text(json.dumps(obj),encoding="utf-8")
    case={"schema":c.CASE_SCHEMA,"case_id":"abc",
          "documents":[{"path":rel,"sha256":_canon_sha(obj)} for rel,obj in docs.items()],
          "query":{"target_id":"threshold","as_of":"2026-08-01","context":{"small":True}}}
    (p/"case.json").write_text(json.dumps(case),encoding="utf-8")
    return docs

class R2CrossDocumentEffectDirectAdequacyV1Tests(unittest.TestCase):
    def test_closed_case_matches_and_runs(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root=Path(td); _write(root)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"8")
            self.assertEqual(out["surviving_effect_ids"],["C.t"])
            self.assertTrue(out["source_immutability_verified"])

    def test_unresolved_incomparable_effects_fall_through(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root=Path(td); _write(root,conflict=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertEqual(pf["status"],"NOT_APPLICABLE__COMMON_EFFECTIVE_VALUE_NOT_PROVED")
            self.assertTrue(pf["direct_route_semantic_open"])

    def test_case_hash_or_document_drift_fails_closed(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root=Path(td); _write(root)
            p=root/"canonical/tmp/A.json"
            row=json.loads(p.read_text()); row["effects"][0]["value"]="99"; p.write_text(json.dumps(row))
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"])
            self.assertEqual(pf["status"],"FAIL_CLOSED")
            self.assertIn("DOCUMENT_CONTENT_ADDRESS_MISMATCH",pf["reason"])

    def test_postwrite_verifier_failure_rolls_back(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root=Path(td); _write(root)
            outp=root/"canonical/tmp/out.json"; outp.write_text('{"old":true}\n')
            old=outp.read_bytes()
            original=d.verifier.verify
            calls={"n":0}
            def injected(case,docs,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(case,docs,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(outp.read_bytes(),old)

if __name__=="__main__":
    unittest.main()
