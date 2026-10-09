from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v2 as l
from canonical.runtime import r2_cross_document_effect_field_lattice_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v14 as v14


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),
    )


def case(*,closed):
    lines=["Effect IDs only for threshold: A.t."]
    values={
        "effect_class":"DEFINE",
        "value":"10",
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
    }
    fields=list(values)
    if not closed:
        fields.remove("supersedes")
    for field in fields:
        lines.append(field_line("A.t",field,values[field]))
    return {
        "schema":l.SCHEMA,
        "case_id":"router",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":"\n".join(lines),"claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


def goal():
    return (
        "Using the cross-document effect field lattice case at "
        "canonical/tmp/fields.json, compute and independently verify the "
        "effective value and save it to canonical/tmp/out.json."
    )


def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"fields.json").write_text(json.dumps(obj),encoding="utf-8")


class R2DirectEndToEndAdequacyV14Tests(unittest.TestCase):
    def test_v14_selects_field_lattice_before_v13(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(closed=True))
            with patch.object(v14.v13,"preflight") as prior:
                out=v14.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v14_preserves_open_field_top_without_v13_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(closed=False))
            with patch.object(v14.v13,"preflight") as prior:
                out=v14.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"],out)
            self.assertTrue(out["direct_route_semantic_open"])
            self.assertEqual(out["open_lattice_atoms"][0]["field"],"supersedes")
            prior.assert_not_called()

    def test_v14_delegates_unrelated_request_to_v13(self):
        expected={"matched":False,"pass":False,"status":"V13_FALLBACK"}
        with patch.object(v14.v13,"preflight",return_value=expected) as prior:
            out=v14.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected)
        prior.assert_called_once()


if __name__=="__main__":
    unittest.main()
