from __future__ import annotations
import json
import unittest

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as v8
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v8 as v8v
from canonical.runtime import cross_document_effect_semantic_lattice_v9 as v9
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v9 as v9v
from canonical.runtime.partial_effect_query_irrelevance_v1 import prove_inapplicable

def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )

def source(*,partial_fields):
    lines=[
        "Effect IDs only for threshold: A.active, A.partial.",
        field_line("A.active","effect_class","DEFINE"),
        field_line("A.active","value","10"),
        field_line("A.active","conditions",{}),
        field_line("A.active","valid_from",None),
        field_line("A.active","valid_until",None),
        field_line("A.active","supersedes",[]),
    ]
    for field,value in partial_fields.items():
        lines.append(field_line("A.partial",field,value))
    return "\n".join(lines)

def problem(*,partial_fields,context=None,as_of="2026-10-09"):
    return {
        "schema":v8.SCHEMA,
        "case_id":"partial-prune",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":source(partial_fields=partial_fields),
            "claims":[],
        }],
        "query":{
            "target_id":"threshold",
            "as_of":as_of,
            "context":context or {},
        },
    }

class PartialEffectQueryIrrelevanceV1Tests(unittest.TestCase):
    def test_future_valid_from_proves_inapplicable(self):
        state={"components":{"valid_from":{"kind":"EXACT","value":"2027-01-01"}}}
        out=prove_inapplicable(
            state,
            {"target_id":"threshold","as_of":"2026-10-09","context":{}},
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["reason"]["kind"],"VALID_FROM_AFTER_QUERY")

    def test_condition_mismatch_proves_inapplicable(self):
        state={"components":{"conditions":{"kind":"EXACT","value":{"small":True}}}}
        out=prove_inapplicable(
            state,
            {"target_id":"threshold","as_of":"2026-10-09","context":{"small":False}},
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["reason"]["kind"],"CONDITION_MISMATCH")

    def test_unknown_applicability_stays_open(self):
        state={"components":{"value":{"kind":"TOP"},"effect_class":{"kind":"TOP"}}}
        out=prove_inapplicable(
            state,
            {"target_id":"threshold","as_of":"2026-10-09","context":{}},
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__PARTIAL_EFFECT_MAY_APPLY")

class CrossDocumentEffectSemanticLatticeV9Tests(unittest.TestCase):
    def test_future_partial_effect_is_pruned_and_active_value_closes(self):
        p=problem(partial_fields={"valid_from":"2027-01-01"})
        before=v8.evaluate(p)
        self.assertFalse(before["pass"],before)
        self.assertTrue(v8v.verify(p,before)["verified"])
        out=v9.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(out["pruned_partial_effects"][0]["effect_id"],"A.partial")
        self.assertEqual(
            out["pruned_partial_effects"][0]["reason"]["kind"],
            "VALID_FROM_AFTER_QUERY",
        )

    def test_expired_partial_effect_is_pruned(self):
        p=problem(partial_fields={"valid_until":"2026-01-01"})
        out=v9.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(
            out["pruned_partial_effects"][0]["reason"]["kind"],
            "VALID_UNTIL_NOT_AFTER_QUERY",
        )

    def test_condition_mismatched_partial_effect_is_pruned(self):
        p=problem(
            partial_fields={"conditions":{"small":True}},
            context={"small":False},
        )
        out=v9.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(
            out["pruned_partial_effects"][0]["reason"]["kind"],
            "CONDITION_MISMATCH",
        )

    def test_partial_effect_that_may_apply_remains_top(self):
        p=problem(partial_fields={"valid_from":"2020-01-01"})
        out=v9.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS_AFTER_PARTIAL_PRUNING",
        )
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("effect_id")=="A.partial"
        ]
        self.assertGreater(len(atoms),0)
        self.assertEqual(out["pruned_partial_effects"],[])

    def test_empty_conditions_do_not_prune(self):
        p=problem(partial_fields={"conditions":{}})
        out=v9.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["pruned_partial_effects"],[])

if __name__=="__main__":
    unittest.main()
