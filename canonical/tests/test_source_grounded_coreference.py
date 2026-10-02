import unittest
from canonical.runtime.source_grounded_coreference import Mention,compile_coreference_candidates,extract_surface_mentions

class SourceGroundedCoreferenceTests(unittest.TestCase):
    def test_ambiguity_preserved(self):
        ms=[
          Mention("a","Alice",0,5,0,"PERSON","SINGULAR",False),
          Mention("b","Beth",10,14,0,"PERSON","SINGULAR",False),
          Mention("r","she",20,23,1,"UNKNOWN","SINGULAR",True),
        ]
        o=compile_coreference_candidates(ms)
        self.assertEqual(o["status"],"COMPILED")
        self.assertEqual({x["antecedent_id"] for x in o["candidate_edges"]},{"a","b"})
        self.assertTrue(o["ambiguity_preserved"])

    def test_number_filter(self):
        ms=[
          Mention("team","Robots",0,6,0,"NONPERSON","PLURAL",False),
          Mention("one","Device",10,16,0,"NONPERSON","SINGULAR",False),
          Mention("r","they",20,24,1,"UNKNOWN","PLURAL",True),
        ]
        o=compile_coreference_candidates(ms)
        self.assertEqual([x["antecedent_id"] for x in o["candidate_edges"]],["team"])

    def test_nonperson_filter_for_it(self):
        ms=[
          Mention("p","Alice",0,5,0,"PERSON","SINGULAR",False),
          Mention("x","Server",10,16,0,"NONPERSON","SINGULAR",False),
          Mention("r","it",20,22,1,"UNKNOWN","SINGULAR",True),
        ]
        o=compile_coreference_candidates(ms)
        self.assertEqual([x["antecedent_id"] for x in o["candidate_edges"]],["x"])

    def test_missing_antecedent_stays_unresolved(self):
        o=compile_coreference_candidates([Mention("r","it",0,2,0,is_reference=True)])
        self.assertEqual(o["candidate_edges"],[])
        self.assertEqual(o["unresolved_references"][0]["reason"],"NO_COMPATIBLE_PRIOR_MENTION")

    def test_surface_extractor_does_not_promote_lowercase_words(self):
        o=extract_surface_mentions("the server met Alice and she left.")
        texts=[m["text"] for m in o["mentions"]]
        self.assertEqual(texts,["Alice","she"])
        self.assertTrue(o["mentions"][1]["is_reference"])

    def test_surface_extractor_keeps_multiword_capitalized_np(self):
        o=extract_surface_mentions("New York met Alice. It changed.")
        texts=[m["text"] for m in o["mentions"]]
        self.assertEqual(texts,["New York","Alice","It"])

    def test_overlap_fails_closed(self):
        ms=[Mention("a","A",0,2,0),Mention("b","B",1,3,0)]
        self.assertEqual(compile_coreference_candidates(ms)["status"],"FAIL_CLOSED")

if __name__=="__main__": unittest.main()
