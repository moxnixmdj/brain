from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_behavioral_abstraction_v1 as b
from canonical.runtime import r2_cross_document_effect_behavioral_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v20 as v20


def field_line(eid, field, value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False
    )


def doc(did,eid,fields):
    lines=[f"The only effects on threshold are {eid}."]
    for field,value in fields.items():
        lines.append(field_line(eid,field,value))
    return {
        "document_id":did,
        "source_id":did,
        "source_text":"\n".join(lines),
        "claims":[],
    }


def case(*docs):
    return {
        "schema":b.SCHEMA,
        "case_id":"direct-behavior",
        "source_documents":list(docs),
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


def goal():
    return (
        "Using the cross-document behavioral effect case at "
        "canonical/tmp/behavior.json, compute and independently verify the "
        "effective value and save it to canonical/tmp/out.json."
    )


def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"behavior.json").write_text(json.dumps(obj),encoding="utf-8")


class R2CrossDocumentEffectBehavioralDirectAdequacyV1Tests(unittest.TestCase):
    def test_behavioral_class_top_case_matches_and_runs(self):
        obj=case(doc("A","A.t",{
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        }))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,obj)
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["source_immutability_verified"])

    def test_behavioral_value_top_is_unmatched_with_reduced_obligation(self):
        obj=case(doc("A","A.t",{
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        }))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,obj)
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            kinds=[x["kind"] for x in pf["next_behavioral_obligations"]]
            self.assertIn("PROVE_EFFECT_VALUE",kinds)
            ignored={(x["effect_id"],x["field"]) for x in pf["ignored_top_fields"]}
            self.assertIn(("A.t","effect_class"),ignored)

    def test_postwrite_verifier_failure_rolls_back(self):
        obj=case(doc("A","A.t",{
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        }))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,obj)
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=d.verifier.verify; calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)


class R2DirectEndToEndAdequacyV20Tests(unittest.TestCase):
    def test_v20_selects_behavioral_route_before_v19(self):
        obj=case(doc("A","A.t",{
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        }))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,obj)
            with patch.object(v20.v19,"preflight") as prior:
                pf=v20.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v20_preserves_behavioral_open_without_v19_fallback(self):
        obj=case(doc("A","A.t",{
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        }))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,obj)
            with patch.object(v20.v19,"preflight") as prior:
                pf=v20.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            prior.assert_not_called()

    def test_v20_delegates_unrelated_request_to_v19(self):
        expected={"matched":False,"pass":False,"status":"V19_FALLBACK"}
        with patch.object(v20.v19,"preflight",return_value=expected) as prior:
            out=v20.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected)
        prior.assert_called_once()


if __name__=="__main__":
    unittest.main()
