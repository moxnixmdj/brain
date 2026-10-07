import unittest
from canonical.runtime.explicit_obligation_index_v1 import build_index as build_v1
from canonical.runtime.explicit_requirement_index_v2 import build_index as build_v2

class T(unittest.TestCase):
    def test_v1_modal_obligation_identity_preserved(self):
        s="The report must include revenue."
        a=build_v1(s,source_id="s")
        b=build_v2(s,source_id="s")
        self.assertEqual(a["obligation_count"],1)
        self.assertEqual(b["modal_obligation_count"],1)
        self.assertEqual(a["obligations"][0]["obligation_id"],b["modal_obligations"][0]["obligation_id"])
        for k in ("source_id","source_sha256","segment_index","segment_span","segment_sha256","semantic_graph","condition"):
            self.assertEqual(a["obligations"][0][k],b["modal_obligations"][0][k])

    def test_imperative_added_without_semantic_split(self):
        s="Include metrics A1 and C1, which carry higher risk weightings."
        x=build_v2(s,source_id="s")
        self.assertEqual(x["modal_obligation_count"],0)
        self.assertEqual(x["imperative_directive_count"],1)
        d=x["imperative_directives"][0]["directive"]
        self.assertEqual(d["predicate"],"include")
        self.assertFalse(d["coordination_split"])
        self.assertFalse(d["argument_semantics_resolved"])
        a,b=d["action_span"]; self.assertEqual(s[a:b],s[:-1])

    def test_context_bound(self):
        s="For each invoice, list the original amount and monthly expense."
        x=build_v2(s,source_id="s")
        self.assertEqual(x["imperative_directive_count"],1)
        c=x["imperative_directives"][0]["context"]
        self.assertEqual(c["relation"],"CONTEXT_FOR")
        a,b=c["span"]; self.assertEqual(s[a:b],"each invoice")

    def test_declarative_stays_unresolved_or_ignored(self):
        s="The report includes revenue and expense details."
        x=build_v2(s,source_id="s")
        self.assertEqual(x["positive_requirement_count"],0)
        self.assertEqual(len(x["unresolved_segments"])+len(x["ignored_segments"]),1)

    def test_mixed_document(self):
        s="The analyst must review the ledger. Create a summary workbook. Background information is attached."
        x=build_v2(s,source_id="s")
        self.assertEqual(x["modal_obligation_count"],1)
        self.assertEqual(x["imperative_directive_count"],1)
        self.assertEqual(x["positive_requirement_count"],2)
        self.assertFalse(x["semantic_completeness_claim"])

if __name__=="__main__":
    unittest.main(verbosity=2)
