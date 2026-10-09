from __future__ import annotations
import json
import unittest

from canonical.runtime import cross_document_effect_behavioral_abstraction_v1 as b


def field_line(eid, field, value):
    payload={"effect_id":eid,"field":field,"value":value}
    return "Effect field: "+json.dumps(
        payload,sort_keys=True,separators=(",",":"),ensure_ascii=False
    )


def doc(did, eid, *, fields):
    lines=[f"The only effects on threshold are {eid}."]
    for field,value in fields.items():
        lines.append(field_line(eid,field,value))
    return {
        "document_id":did,
        "source_id":did,
        "source_text":"\n".join(lines),
        "claims":[],
    }


def problem(*docs):
    return {
        "schema":b.SCHEMA,
        "case_id":"behavior",
        "source_documents":list(docs),
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{"small":True}},
    }


class CrossDocumentEffectBehavioralAbstractionV1Tests(unittest.TestCase):
    def test_effect_class_top_is_behaviorally_irrelevant(self):
        a=doc("A","A.t",fields={
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        })
        out=b.evaluate(problem(a))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        ignored={(x["effect_id"],x["field"]) for x in out["ignored_top_fields"]}
        self.assertIn(("A.t","effect_class"),ignored)

    def test_unknown_weaker_effect_is_irrelevant_under_exact_applicable_global_dominator(self):
        a=doc("A","A.t",fields={
            "effect_class":"REPLACE",
            "value":"12",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":["B.t"],
        })
        bdoc=doc("B","B.t",fields={})
        out=b.evaluate(problem(a,bdoc))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"12")
        ignored={(x["effect_id"],x["field"]) for x in out["ignored_top_fields"]}
        self.assertIn(("B.t","value"),ignored)
        self.assertIn(("B.t","conditions"),ignored)
        self.assertIn(("B.t","supersedes"),ignored)

    def test_unknown_surviving_value_remains_open(self):
        a=doc("A","A.t",fields={
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        })
        out=b.evaluate(problem(a))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__BEHAVIORAL_COMPLETIONS_HAVE_DISTINCT_OUTCOMES",
        )
        kinds=[x["kind"] for x in out["next_behavioral_obligations"]]
        self.assertIn("PROVE_EFFECT_VALUE",kinds)

    def test_unknown_applicability_remains_open_when_it_can_remove_only_effect(self):
        a=doc("A","A.t",fields={
            "value":"10",
            "supersedes":[],
        })
        out=b.evaluate(problem(a))
        self.assertFalse(out["pass"],out)
        kinds=[x["kind"] for x in out["next_behavioral_obligations"]]
        self.assertIn("RESOLVE_EFFECT_APPLICABILITY_AT_QUERY",kinds)

    def test_unknown_supersession_remains_open_when_it_changes_winner(self):
        a=doc("A","A.t",fields={
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
        })
        c=doc("C","C.t",fields={
            "value":"11",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
        })
        out=b.evaluate(problem(a,c))
        self.assertFalse(out["pass"],out)
        kinds=[x["kind"] for x in out["next_behavioral_obligations"]]
        self.assertIn("PROVE_SUPERSESSION_SET_FOR_EFFECT",kinds)

    def test_same_exact_values_close_despite_other_behavioral_top(self):
        a=doc("A","A.t",fields={
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        })
        c=doc("C","C.t",fields={
            "value":"10",
        })
        out=b.evaluate(problem(a,c))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertGreater(out["behavioral_world_count"],1)

    def test_exact_non_define_empty_supersedes_fails_closed(self):
        a=doc("A","A.t",fields={
            "effect_class":"REPLACE",
            "value":"10",
            "conditions":{},
            "valid_from":None,
            "valid_until":None,
            "supersedes":[],
        })
        out=b.evaluate(problem(a))
        self.assertFalse(out["pass"],out)
        self.assertTrue(str(out["status"]).startswith("FAIL_CLOSED"),out)

    def test_behavioral_world_bound_fails_open_not_false_pass(self):
        docs=[]
        for i in range(5):
            docs.append(doc(chr(65+i),f"E{i}",fields={
                "value":"10",
                "conditions":{},
                "valid_from":None,
                "valid_until":None,
            }))
        out=b.evaluate(problem(*docs))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__BEHAVIORAL_WORLD_BOUND_EXCEEDED")


if __name__=="__main__":
    unittest.main()
