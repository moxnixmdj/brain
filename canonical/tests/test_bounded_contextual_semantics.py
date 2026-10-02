import unittest
from canonical.runtime.bounded_contextual_semantics import resolve_pronouns, explicit_discourse_relations, compile_context

class Tests(unittest.TestCase):
    def test_unique_masc_reference(self):
        text="Alice met Bob. He approved the plan."
        mentions=[
            {"id":"A","start":0,"end":5,"number":"singular","gender":"fem"},
            {"id":"B","start":10,"end":13,"number":"singular","gender":"masc"},
        ]
        r=resolve_pronouns(text,mentions)
        self.assertEqual(r["resolutions"][0]["status"],"RESOLVED")
        self.assertEqual(r["resolutions"][0]["antecedent_id"],"B")

    def test_gender_filter_blocks_wrong_nearest(self):
        text="Bob met Alice. He approved it."
        mentions=[
            {"id":"B","start":0,"end":3,"number":"singular","gender":"masc"},
            {"id":"A","start":8,"end":13,"number":"singular","gender":"fem"},
            {"id":"PLAN","start":27,"end":29,"number":"singular","gender":"neuter"},
        ]
        r=resolve_pronouns(text,mentions)
        self.assertEqual(r["resolutions"][0]["antecedent_id"],"B")

    def test_near_tie_fails_closed(self):
        text="Tom, Tim. He left."
        mentions=[
            {"id":"TOM","start":0,"end":3,"number":"singular","gender":"masc"},
            {"id":"TIM","start":5,"end":8,"number":"singular","gender":"masc"},
        ]
        r=resolve_pronouns(text,mentions)
        self.assertEqual(r["resolutions"][0]["status"],"AMBIGUOUS")

    def test_no_antecedent_fails_closed(self):
        r=resolve_pronouns("He left.",[])
        self.assertEqual(r["resolutions"][0]["status"],"UNRESOLVED")

    def test_plural_reference(self):
        text="The workers arrived. They started."
        mentions=[{"id":"W","start":0,"end":11,"number":"plural","gender":"unknown"}]
        r=resolve_pronouns(text,mentions)
        self.assertEqual(r["resolutions"][0]["antecedent_id"],"W")

    def test_explicit_discourse_relations(self):
        text="If A fails, retry because evidence changed; however stop before revocation."
        rels={x["relation"] for x in explicit_discourse_relations(text)}
        self.assertTrue({"CONDITION","CAUSE","CONTRAST","TEMPORAL_BEFORE"} <= rels)

    def test_compile_never_claims_terminal_authority(self):
        out=compile_context("Alice arrived. She left.",[
            {"id":"A","start":0,"end":5,"number":"singular","gender":"fem"}
        ])
        self.assertFalse(out["pronouns"]["terminal_authority"])
        self.assertIn("GENERAL_COREFERENCE",out["claims_excluded"])

if __name__=="__main__":
    unittest.main()
