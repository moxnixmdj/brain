from __future__ import annotations
import json
import unittest

from canonical.runtime import cross_document_effect_semantic_lattice_v2 as l
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v2 as lv


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )


def relation_line(effect):
    return "Effect relation: "+json.dumps(
        effect,sort_keys=True,separators=(",",":"),ensure_ascii=False
    )


def define(eid,value,target="threshold"):
    return {
        "conditions":{},
        "effect_class":"DEFINE",
        "effect_id":eid,
        "supersedes":[],
        "target_id":target,
        "valid_from":None,
        "valid_until":None,
        "value":value,
    }


def replace(eid,value,sup,target="threshold"):
    return {
        "conditions":{},
        "effect_class":"REPLACE",
        "effect_id":eid,
        "supersedes":[sup],
        "target_id":target,
        "valid_from":None,
        "valid_until":None,
        "value":value,
    }


def field_source(effect,*,omit=(),extra=()):
    eid=effect["effect_id"]
    target=effect["target_id"]
    lines=[
        "Effect IDs only for "+target+": "+eid+".",
    ]
    for field in (
        "effect_class","value","conditions",
        "valid_from","valid_until","supersedes",
    ):
        if field not in set(omit):
            lines.append(field_line(eid,field,effect[field]))
    lines.extend(extra)
    return "\n".join(lines)


def doc(did,source,claims=None):
    return {
        "document_id":did,
        "source_id":did,
        "source_text":source,
        "claims":list(claims or []),
    }


def problem(*docs):
    return {
        "schema":l.SCHEMA,
        "case_id":"fields",
        "source_documents":list(docs),
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


class CrossDocumentEffectSemanticLatticeV2Tests(unittest.TestCase):
    def test_unstructured_source_starts_at_inventory_top(self):
        p=problem(doc("A","Threshold might change."))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["open_lattice_atoms"][0]["dimension"],
            "EFFECT_ID_INVENTORY",
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_inventory_only_opens_six_independent_fields(self):
        p=problem(doc("A","Effect IDs only for threshold: A.t."))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("dimension")=="DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(len(atoms),6)
        self.assertEqual(
            {x["field"] for x in atoms},
            {
                "effect_class","value","conditions",
                "valid_from","valid_until","supersedes",
            },
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_five_of_six_fields_leave_exact_single_top(self):
        effect=define("A.t","10")
        p=problem(doc("A",field_source(effect,omit={"supersedes"})))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(len(out["open_lattice_atoms"]),1)
        atom=out["open_lattice_atoms"][0]
        self.assertEqual(atom["effect_id"],"A.t")
        self.assertEqual(atom["field"],"supersedes")
        self.assertEqual(
            atom["proof_obligation"]["kind"],
            "PROVE_DOCUMENT_EFFECT_FIELD",
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_six_fields_assemble_and_close_value(self):
        effect=define("A.t","10")
        p=problem(doc("A",field_source(effect)))
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        state=out["lattice_documents"][0]["effect_states"]["A.t"]
        self.assertEqual(state["kind"],"EXACT_FIELDS")
        self.assertTrue(
            state["effect"]["source_locator"].startswith("A:fieldproof:")
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_field_assembled_replace_composes_with_define(self):
        a=define("A.t","10")
        b=replace("B.t","12","A.t")
        p=problem(
            doc("A",field_source(a)),
            doc("B",field_source(b)),
        )
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"12")
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_complete_but_cross_field_invalid_effect_fails_closed(self):
        bad=replace("B.t","12","A.t")
        bad["supersedes"]=[]
        p=problem(doc("B",field_source(bad)))
        out=l.evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("ASSEMBLED_EFFECT_INVALID",out["reason"])

    def test_target_field_conflicting_with_inventory_fails_closed(self):
        effect=define("A.t","10")
        source=field_source(
            effect,
            extra=[field_line("A.t","target_id","other")],
        )
        p=problem(doc("A",source))
        out=l.evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn(
            "INVENTORIED_EFFECT_TARGET_FIELD_MISMATCH",
            out["reason"],
        )

    def test_full_relation_remains_stronger_shortcut(self):
        effect=define("A.t","10")
        source="\n".join([
            "Effect IDs only for threshold: A.t.",
            relation_line(effect),
        ])
        p=problem(doc("A",source))
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["lattice_documents"][0]["effect_states"]["A.t"]["kind"],
            "EXACT_RELATION",
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_full_relation_conflicting_field_fails_closed(self):
        effect=define("A.t","10")
        source="\n".join([
            "Effect IDs only for threshold: A.t.",
            relation_line(effect),
            field_line("A.t","value","99"),
        ])
        p=problem(doc("A",source))
        out=l.evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("FULL_RELATION_FIELD_PROOF_CONFLICT",out["reason"])

    def test_wrong_existing_field_blocks_autofill_and_leaves_top(self):
        effect=define("A.t","10")
        source=field_source(effect)
        wrong=[{
            "claim_id":"wrong",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":"A.t",
            "field":"value",
            "value":"99",
        }]
        p=problem(doc("A",source,wrong))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        atoms=out["open_lattice_atoms"]
        self.assertEqual(len(atoms),1)
        self.assertEqual(atoms[0]["field"],"value")
        self.assertGreater(
            out["lattice_documents"][0]["rejected_claim_count"],0
        )
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_finite_incomparable_field_effects_remain_open(self):
        p=problem(
            doc("A",field_source(define("A.t","10"))),
            doc("B",field_source(define("B.t","11"))),
        )
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__FIELD_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
        )
        self.assertEqual(set(out["possible_outcomes"]),{"10","11"})
        self.assertTrue(out["query_relative_effect_semantics_finite"])
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_verifier_rejects_tampered_closed_value(self):
        p=problem(doc("A",field_source(define("A.t","10"))))
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        tampered=dict(out)
        tampered["effective_value"]="999"
        check=lv.verify(p,tampered)
        self.assertFalse(check["verified"])
        self.assertIn("MISMATCH:effective_value",check["errors"])


if __name__=="__main__":
    unittest.main()
