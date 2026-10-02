import unittest

from canonical.runtime.feature_constraint_composer import compose_feature_constraints

class FeatureConstraintComposerTests(unittest.TestCase):
    def test_compound_hole_and_position_frame(self):
        rows=[
            {"target_id":"hole1","source_id":"c1","annotation":{
                "status":"PARSED","kind":"hole_or_cylindrical_feature",
                "diameter":10.0,"units":"mm","through":True,"depth":None,
                "depth_units":None,"counterbore":None,"countersink":None,"quantity":1,
            }},
            {"target_id":"hole1","source_id":"c2","annotation":{
                "status":"PARSED","kind":"gdt","characteristic":"position",
                "tolerance":0.1,"diametrical_zone":True,"units":"mm","datums":["A","B","C"],
            }},
        ]
        o=compose_feature_constraints(rows)
        self.assertEqual(o["status"],"COMPOSED")
        self.assertEqual(o["features"]["hole1"]["diameter"]["value"],10.0)
        self.assertTrue(o["features"]["hole1"]["extent"]["through"])
        self.assertEqual(o["features"]["hole1"]["gdt:position"]["datums"],["A","B","C"])

    def test_conflicting_diameter_fails_closed(self):
        rows=[
            {"target_id":"h","source_id":"a","annotation":{"status":"PARSED","kind":"diameter","value":10.0,"units":"mm"}},
            {"target_id":"h","source_id":"b","annotation":{"status":"PARSED","kind":"diameter","value":12.0,"units":"mm"}},
        ]
        o=compose_feature_constraints(rows)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertIn("CONFLICT:h:diameter",o["errors"])

    def test_duplicate_same_claim_is_idempotent(self):
        ann={"status":"PARSED","kind":"radius","value":4.0,"units":"mm"}
        o=compose_feature_constraints([
            {"target_id":"f","source_id":"a","annotation":ann},
            {"target_id":"f","source_id":"b","annotation":ann},
        ])
        self.assertEqual(o["status"],"COMPOSED")
        self.assertEqual(o["features"]["f"]["radius"]["value"],4.0)
        self.assertEqual(o["provenance"]["f"]["radius"],["a","b"])

    def test_unparsed_annotation_fails(self):
        o=compose_feature_constraints([
            {"target_id":"x","annotation":{"status":"FAIL_CLOSED","kind":"diameter"}}
        ])
        self.assertEqual(o["status"],"FAIL_CLOSED")

    def test_declarative_jit_claim_composes(self):
        o=compose_feature_constraints([
            {"target_id":"surface1","source_id":"jit","annotation":{
                "status":"PARSED","kind":"declarative_claim",
                "property":"surface_finish.ra",
                "value":{"roughness":3.2,"units":"UM"}
            }}
        ])
        self.assertEqual(o["status"],"COMPOSED")
        self.assertEqual(o["features"]["surface1"]["surface_finish.ra"]["roughness"],3.2)

if __name__=="__main__":
    unittest.main()
