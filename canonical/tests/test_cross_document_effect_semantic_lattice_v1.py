from __future__ import annotations
import json
import unittest

from canonical.runtime import cross_document_effect_semantic_lattice_v1 as l
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v1 as lv
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations


def _relation(effect):
    payload=json.dumps(effect,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return "Effect relation: "+payload


def _semantics_from_line(line,source_id):
    parsed=parse_effect_relations(line,source=source_id)["relations"][0]["effect"]
    return {k:v for k,v in parsed.items() if k!="source_locator"}


def _doc(did,*,target="threshold",effect_ids=None,effects=None,scope=None,extra_claims=None):
    effect_ids=effect_ids or []
    effects=effects or []
    lines=[]
    claims=[]
    if scope is not None:
        lines.append("Effect targets only: "+", ".join(scope)+".")
        claims.append({
            "claim_id":did+".scope",
            "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
            "target_ids":list(scope),
        })
    if effect_ids is not None:
        if effect_ids:
            lines.append(
                "Effect IDs only for "+target+": "+", ".join(effect_ids)+"."
            )
            claims.append({
                "claim_id":did+".inventory",
                "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                "target_id":target,
                "effect_ids":list(effect_ids),
            })
    for i,effect in enumerate(effects):
        line=_relation(effect)
        lines.append(line)
    text="\n".join(lines)
    for i,effect in enumerate(effects):
        line=_relation(effect)
        claims.append({
            "claim_id":did+f".relation.{i}",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
            "effect":_semantics_from_line(line,did),
        })
    claims.extend(extra_claims or [])
    return {
        "document_id":did,
        "source_id":did,
        "source_text":text or "Unstructured prose.",
        "claims":claims,
    }


def _define(eid,value,target="threshold"):
    return {
        "conditions":{},"effect_class":"DEFINE","effect_id":eid,
        "supersedes":[],"target_id":target,"valid_from":None,
        "valid_until":None,"value":value,
    }


def _replace(eid,value,sup,target="threshold"):
    return {
        "conditions":{},"effect_class":"REPLACE","effect_id":eid,
        "supersedes":[sup],"target_id":target,"valid_from":None,
        "valid_until":None,"value":value,
    }


def _problem(*docs):
    return {
        "schema":l.SCHEMA,
        "case_id":"lattice",
        "source_documents":list(docs),
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


class CrossDocumentEffectSemanticLatticeV1Tests(unittest.TestCase):
    def test_no_proof_starts_at_inventory_top(self):
        out=l.evaluate(_problem({
            "document_id":"A","source_id":"A",
            "source_text":"The threshold might change.",
            "claims":[],
        }))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__QUERY_RELEVANT_EFFECT_SEMANTIC_TOP_REMAINS",
        )
        atom=out["open_lattice_atoms"][0]
        self.assertEqual(atom["dimension"],"EFFECT_ID_INVENTORY")
        self.assertEqual(atom["state"],"TOP")
        self.assertTrue(lv.verify(_problem({
            "document_id":"A","source_id":"A",
            "source_text":"The threshold might change.","claims":[]}),out)["verified"])

    def test_scope_exclusion_discharge_is_query_relative(self):
        doc=_doc("X",target="other",effect_ids=["X.o"],
                 effects=[_define("X.o","alpha","other")],
                 scope=["other"])
        out=l.evaluate(_problem(doc))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__NO_QUERY_EFFECT_RELATION_PROVED")
        self.assertEqual(
            out["lattice_documents"][0]["query_status"],
            "PROVED_QUERY_IRRELEVANT",
        )
        self.assertEqual(out["open_lattice_atoms"],[])

    def test_inventory_refines_ids_but_relations_remain_top(self):
        doc=_doc("A",effect_ids=["A.t"],effects=[])
        out=l.evaluate(_problem(doc))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["lattice_documents"][0]["query_effect_id_inventory"],
            {"kind":"FINITE","values":["A.t"]},
        )
        atom=out["open_lattice_atoms"][0]
        self.assertEqual(atom["dimension"],"DOCUMENT_EFFECT_RELATION")
        self.assertEqual(atom["effect_id"],"A.t")

    def test_relation_without_inventory_cannot_claim_completeness(self):
        doc=_doc("A",effect_ids=[],effects=[_define("A.t","10")])
        out=l.evaluate(_problem(doc))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["open_lattice_atoms"][0]["dimension"],
            "EFFECT_ID_INVENTORY",
        )

    def test_exact_inventory_and_relation_close_value(self):
        doc=_doc("A",effect_ids=["A.t"],effects=[_define("A.t","10")])
        out=l.evaluate(_problem(doc))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertTrue(out["query_relative_effect_semantics_finite"])
        self.assertTrue(lv.verify(_problem(doc),out)["verified"])
        self.assertEqual(out["open_lattice_atoms"],[])

    def test_define_then_replace_composes(self):
        a=_doc("A",effect_ids=["A.t"],effects=[_define("A.t","10")])
        b=_doc("B",effect_ids=["B.t"],effects=[_replace("B.t","12","A.t")])
        out=l.evaluate(_problem(a,b))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"12")

    def test_rejected_relation_claim_never_narrows_top(self):
        effect=_define("A.t","10")
        doc=_doc("A",effect_ids=["A.t"],effects=[])
        wrong=dict(effect); wrong["value"]="99"
        doc["source_text"]+="\n"+_relation(effect)
        doc["claims"].append({
            "claim_id":"A.bad",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
            "effect":wrong,
        })
        out=l.evaluate(_problem(doc))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["lattice_documents"][0]["relation_states"]["A.t"],
            {"kind":"TOP"},
        )
        self.assertGreater(
            out["lattice_documents"][0]["rejected_claim_count"],0
        )

    def test_relation_outside_inventory_fails_closed(self):
        doc=_doc(
            "A",
            effect_ids=["A.t"],
            effects=[_define("A.t","10"),_define("A.extra","11")],
        )
        out=l.evaluate(_problem(doc))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("RELATION_ID_OUTSIDE_PROVED_INVENTORY",out["reason"])

    def test_relation_outside_proved_scope_fails_closed(self):
        doc=_doc(
            "A",
            effect_ids=["A.t"],
            effects=[_define("A.t","10")],
            scope=["other"],
        )
        out=l.evaluate(_problem(doc))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("RELATION_TARGET_OUTSIDE_PROVED_SCOPE",out["reason"])

    def test_finite_incomparable_effects_remain_open(self):
        a=_doc("A",effect_ids=["A.t"],effects=[_define("A.t","10")])
        b=_doc("B",effect_ids=["B.t"],effects=[_define("B.t","11")])
        out=l.evaluate(_problem(a,b))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__SEMANTIC_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
        )
        self.assertEqual(set(out["possible_outcomes"]),{"10","11"})
        self.assertTrue(out["query_relative_effect_semantics_finite"])
        self.assertTrue(lv.verify(_problem(a,b),out)["verified"])


if __name__=="__main__":
    unittest.main()
