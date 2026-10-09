from __future__ import annotations
import json
import unittest

from canonical.runtime import cross_document_effect_dimension_lattice_v1 as l
from canonical.runtime import cross_document_effect_dimension_lattice_verify_v1 as lv
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations


def _j(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _dimension_line(eid,dim,value):
    if dim=="target":
        return f"Effect {eid} target: {value}."
    if dim=="effect_class":
        return f"Effect {eid} class: {value}."
    if dim=="value":
        return f"Effect {eid} value JSON: {_j(value)}."
    if dim=="conditions":
        return f"Effect {eid} conditions JSON: {_j(value)}."
    if dim=="valid_from":
        return f"Effect {eid} valid from: {value if value is not None else 'none'}."
    if dim=="valid_until":
        return f"Effect {eid} valid until: {value if value is not None else 'none'}."
    if dim=="supersedes":
        return f"Effect {eid} supersedes: {', '.join(value) if value else 'none'}."
    raise AssertionError(dim)


def _dimension_claim(did,eid,dim,value,n):
    return {
        "claim_id":f"{did}.d{n}",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
        "effect_id":eid,
        "dimension":dim,
        "value":value,
    }


def _effect_dims(*,cls="DEFINE",value="10",conditions=None,start=None,end=None,sup=None):
    return {
        "effect_class":cls,
        "value":value,
        "conditions":conditions or {},
        "valid_from":start,
        "valid_until":end,
        "supersedes":sup or [],
    }


def _doc(
    did,
    *,
    inventory=None,
    dimensions=None,
    scope=None,
    full_relation=None,
    extra_lines=None,
    extra_claims=None,
):
    lines=[]; claims=[]
    if scope is not None:
        lines.append("Effect targets only: "+", ".join(scope)+".")
        claims.append({
            "claim_id":did+".scope",
            "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
            "target_ids":list(scope),
        })
    if inventory is not None:
        lines.append("Effect IDs only for threshold: "+", ".join(inventory)+".")
        claims.append({
            "claim_id":did+".inv",
            "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
            "target_id":"threshold",
            "effect_ids":list(inventory),
        })
    n=0
    for eid,dimmap in (dimensions or {}).items():
        for dim,value in dimmap.items():
            lines.append(_dimension_line(eid,dim,value))
            claims.append(_dimension_claim(did,eid,dim,value,n)); n+=1
    if full_relation is not None:
        line="Effect relation: "+_j(full_relation)
        lines.append(line)
        parsed=parse_effect_relations(line,source=did)["relations"][0]["effect"]
        claims.append({
            "claim_id":did+".rel",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
            "effect":{k:v for k,v in parsed.items() if k!="source_locator"},
        })
    lines.extend(extra_lines or [])
    claims.extend(extra_claims or [])
    return {
        "document_id":did,
        "source_id":did,
        "source_text":"\n".join(lines) or "Unstructured prose.",
        "claims":claims,
    }


def _problem(*docs):
    return {
        "schema":l.SCHEMA,
        "case_id":"dimension-lattice",
        "source_documents":list(docs),
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


class CrossDocumentEffectDimensionLatticeV1Tests(unittest.TestCase):
    def test_inventory_only_leaves_six_relation_dimensions_top(self):
        out=l.evaluate(_problem(_doc("A",inventory=["A.t"])))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__QUERY_RELEVANT_EFFECT_DIMENSION_TOP_REMAINS",
        )
        dims={x["dimension"] for x in out["open_lattice_atoms"]}
        self.assertEqual(
            dims,
            {"effect_class","value","conditions","valid_from","valid_until","supersedes"},
        )

    def test_one_dimension_refines_only_itself(self):
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],
            dimensions={"A.t":{"effect_class":"DEFINE"}},
        )))
        self.assertFalse(out["pass"],out)
        state=out["lattice_documents"][0]["effect_states"]["A.t"]["dimensions"]
        self.assertEqual(state["effect_class"]["kind"],"EXACT")
        self.assertEqual(state["value"],{"kind":"TOP"})
        self.assertEqual(len(out["open_lattice_atoms"]),5)
        self.assertTrue(lv.verify(_problem(_doc(\n            "A",inventory=["A.t"],\n            dimensions={"A.t":{"effect_class":"DEFINE"}},\n        )),out)["verified"])

    def test_all_independent_dimensions_close_define(self):
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],
            dimensions={"A.t":_effect_dims()},
        )))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(out["open_lattice_atoms"],[])
        self.assertTrue(lv.verify(_problem(_doc(\n            "A",inventory=["A.t"],dimensions={"A.t":_effect_dims()},\n        )),out)["verified"])

    def test_v8_full_relation_still_closes(self):
        relation={
            "conditions":{},
            "effect_class":"DEFINE",
            "effect_id":"A.t",
            "supersedes":[],
            "target_id":"threshold",
            "valid_from":None,
            "valid_until":None,
            "value":"10",
        }
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],full_relation=relation,
        )))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")

    def test_v8_and_v9_equal_dimension_can_coexist(self):
        relation={
            "conditions":{},
            "effect_class":"DEFINE",
            "effect_id":"A.t",
            "supersedes":[],
            "target_id":"threshold",
            "valid_from":None,
            "valid_until":None,
            "value":"10",
        }
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],
            full_relation=relation,
            dimensions={"A.t":{"value":"10"}},
        )))
        self.assertTrue(out["pass"],out)

    def test_v8_v9_conflict_fails_closed(self):
        relation={
            "conditions":{},
            "effect_class":"DEFINE",
            "effect_id":"A.t",
            "supersedes":[],
            "target_id":"threshold",
            "valid_from":None,
            "valid_until":None,
            "value":"10",
        }
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],
            full_relation=relation,
            dimensions={"A.t":{"value":"11"}},
        )))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PROVED_EFFECT_DIMENSION_CONFLICT",out["reason"])

    def test_cross_field_invalid_closed_dimensions_fail_closed(self):
        dims=_effect_dims(cls="REPLACE",sup=[])
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],dimensions={"A.t":dims},
        )))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("NON_DEFINE_EFFECT_REQUIRES_SUPERSESSION_TARGET",out["reason"])

    def test_source_proved_nonquery_effect_dimensions_do_not_poison_query(self):
        dimensions={
            "A.t":_effect_dims(),
            "X.o":{
                "target":"other",
                **_effect_dims(value="alpha"),
            },
        }
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],dimensions=dimensions,
        )))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")

    def test_extra_effect_without_nonquery_target_proof_fails_closed(self):
        dimensions={
            "A.t":_effect_dims(),
            "X.o":{"effect_class":"DEFINE"},
        }
        out=l.evaluate(_problem(_doc(
            "A",inventory=["A.t"],dimensions=dimensions,
        )))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn(
            "QUERY_DIMENSION_OUTSIDE_PROVED_INVENTORY_WITHOUT_NONQUERY_TARGET_PROOF",
            out["reason"],
        )

    def test_define_then_replace_closes_from_independent_dimensions(self):
        a=_doc("A",inventory=["A.t"],dimensions={"A.t":_effect_dims(value="10")})
        b=_doc("B",inventory=["B.t"],dimensions={
            "B.t":_effect_dims(cls="REPLACE",value="12",sup=["A.t"])
        })
        out=l.evaluate(_problem(a,b))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"12")

    def test_finite_incomparable_effects_remain_open(self):
        a=_doc("A",inventory=["A.t"],dimensions={"A.t":_effect_dims(value="10")})
        b=_doc("B",inventory=["B.t"],dimensions={"B.t":_effect_dims(value="11")})
        out=l.evaluate(_problem(a,b))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__DIMENSION_LATTICE_FINITE__EFFECT_COMPOSITION_NOT_CLOSED",
        )
        self.assertEqual(set(out["possible_outcomes"]),{"10","11"})
        self.assertTrue(lv.verify(_problem(a,b),out)["verified"])


if __name__=="__main__":
    unittest.main()
