import unittest

from canonical.runtime.bounded_semantic_graph_synthesizer import synthesize_graphs


class BoundedSemanticGraphSynthesizerTests(unittest.TestCase):
    def test_exhaustive_single_relation_instance(self):
        out=synthesize_graphs({
            "nodes":[
                {"id":"alice","type":"person"},
                {"id":"pump","type":"device"},
            ],
            "relation_schemas":[{
                "id":"OWNS",
                "roles":[
                    {"name":"owner","allowed_types":["person"]},
                    {"name":"item","allowed_types":["device"]},
                ],
            }],
            "max_edges":1,
            "max_candidates":10,
        })
        self.assertEqual(out["status"],"COMPLETE",out)
        self.assertTrue(out["complete_within_declared_bound"])
        self.assertEqual(out["relation_instance_count"],1)
        self.assertEqual(out["candidate_count"],2)
        self.assertEqual(out["candidates"][1]["relations"][0]["relation"],"OWNS")

    def test_all_ambiguous_structures_are_preserved(self):
        out=synthesize_graphs({
            "nodes":[
                {"id":"alice","type":"person"},
                {"id":"bob","type":"person"},
                {"id":"pump","type":"device"},
            ],
            "relation_schemas":[{
                "id":"OWNS",
                "roles":[
                    {"name":"owner","allowed_types":["person"]},
                    {"name":"item","allowed_types":["device"]},
                ],
            }],
            "max_edges":1,
            "max_candidates":10,
        })
        self.assertEqual(out["relation_instance_count"],2)
        self.assertEqual(out["candidate_count"],3)
        owners={
            c["relations"][0]["roles"]["owner"]
            for c in out["candidates"] if c["relations"]
        }
        self.assertEqual(owners,{"alice","bob"})
        self.assertFalse(out["truth_selection_authority"])

    def test_symmetric_relation_deduplicates_orientation(self):
        out=synthesize_graphs({
            "nodes":[{"id":"a","type":"x"},{"id":"b","type":"x"}],
            "relation_schemas":[{
                "id":"PEER",
                "symmetric":True,
                "roles":[
                    {"name":"left","allowed_types":["x"]},
                    {"name":"right","allowed_types":["x"]},
                ],
            }],
            "max_edges":1,
        })
        self.assertEqual(out["relation_instance_count"],1)

    def test_bound_exceeded_fails_without_false_completeness(self):
        out=synthesize_graphs({
            "nodes":[
                {"id":"a","type":"x"},{"id":"b","type":"x"},{"id":"c","type":"x"}
            ],
            "relation_schemas":[{
                "id":"R",
                "roles":[
                    {"name":"from","allowed_types":["x"]},
                    {"name":"to","allowed_types":["x"]},
                ],
            }],
            "max_edges":3,
            "max_candidates":2,
        })
        self.assertEqual(out["status"],"BOUND_EXCEEDED")
        self.assertFalse(out["complete_within_declared_bound"])
        self.assertNotIn("candidates",out)

    def test_unknown_semantic_label_is_not_invented(self):
        out=synthesize_graphs({
            "nodes":[{"id":"a","type":"x"},{"id":"b","type":"x"}],
            "relation_schemas":[],
            "max_edges":2,
        })
        self.assertEqual(out["status"],"COMPLETE")
        self.assertEqual(out["relation_instance_count"],0)
        self.assertEqual(out["candidate_count"],1)
        self.assertEqual(out["candidates"][0]["relations"],[])

    def test_deterministic_under_input_reordering(self):
        a=synthesize_graphs({
            "nodes":[{"id":"b","type":"x"},{"id":"a","type":"x"}],
            "relation_schemas":[{
                "id":"R",
                "roles":[
                    {"name":"u","allowed_types":["x"]},
                    {"name":"v","allowed_types":["x"]},
                ],
            }],
            "max_edges":1,
            "max_candidates":100,
        })
        b=synthesize_graphs({
            "nodes":[{"id":"a","type":"x"},{"id":"b","type":"x"}],
            "relation_schemas":[{
                "id":"R",
                "roles":[
                    {"name":"u","allowed_types":["x"]},
                    {"name":"v","allowed_types":["x"]},
                ],
            }],
            "max_edges":1,
            "max_candidates":100,
        })
        self.assertEqual(a,b)


if __name__=="__main__":
    unittest.main(verbosity=2)
