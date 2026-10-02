import unittest
from canonical.runtime.m0a_semantic_graph_consensus import compile_consensus

SRC="The parser failed. It was unavailable."

class M0ASemanticGraphConsensusTests(unittest.TestCase):
    def test_two_independent_groups_admit_binding(self):
        p=[
            {"route_id":"a","independence_group":"deterministic","bindings":[{"mention_span":[19,21],"target_span":[4,10],"kind":"coreference"}]},
            {"route_id":"b","independence_group":"whitebox_coref","bindings":[{"mention_span":[19,21],"target_span":[4,10],"kind":"coreference"}]},
        ]
        o=compile_consensus(SRC,p)
        self.assertEqual(o["status"],"CONSENSUS")
        self.assertEqual(len(o["accepted"]["bindings"]),1)

    def test_duplicate_routes_same_group_do_not_fake_independence(self):
        p=[
            {"route_id":"a","independence_group":"same_model","bindings":[{"mention_span":[19,21],"target_span":[4,10]}]},
            {"route_id":"b","independence_group":"same_model","bindings":[{"mention_span":[19,21],"target_span":[4,10]}]},
        ]
        o=compile_consensus(SRC,p)
        self.assertEqual(o["status"],"PARTIAL")
        self.assertEqual(o["unresolved"][0]["independent_support"],1)

    def test_material_alternative_binding_is_ambiguity(self):
        p=[
            {"route_id":"a","independence_group":"g1","bindings":[{"mention_span":[19,21],"target_span":[4,10]}]},
            {"route_id":"b","independence_group":"g2","bindings":[{"mention_span":[19,21],"target_span":[11,17]}]},
        ]
        o=compile_consensus(SRC,p)
        self.assertEqual(o["status"],"AMBIGUOUS")
        self.assertEqual(len(o["ambiguity_witness"]),1)

    def test_relations_need_independent_support(self):
        rel={"kind":"causal","left_span":[4,10],"right_span":[11,17]}
        p=[
            {"route_id":"a","independence_group":"g1","relations":[rel]},
            {"route_id":"b","independence_group":"g2","relations":[rel]},
        ]
        o=compile_consensus(SRC,p)
        self.assertEqual(o["status"],"CONSENSUS")
        self.assertEqual(len(o["accepted"]["relations"]),1)

    def test_out_of_bounds_span_fails_closed(self):
        p=[{"route_id":"a","independence_group":"g1","bindings":[{"mention_span":[0,999],"target_span":[4,10]}]}]
        o=compile_consensus(SRC,p)
        self.assertEqual(o["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main()
