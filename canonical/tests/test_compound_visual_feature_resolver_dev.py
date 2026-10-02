import unittest
from canonical.runtime.compound_visual_feature_resolver import resolve
from canonical.runtime.engineering_feature_notation import parse_feature_notation

class CompoundVisualFeatureResolverDev(unittest.TestCase):
    def test_2x_equal_holes(self):
        features=[
          {"kind":"circle","center":[180,160],"radius":28,"id":"H1"},
          {"kind":"circle","center":[330,160],"radius":28,"id":"H2"},
        ]
        ann=parse_feature_notation("2X DIA 10 THRU")
        r=resolve(features,ann,[180,132])
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["feature_ids"],["H1","H2"])
        self.assertEqual(r["quantity"],2)

    def test_3x_with_distractor(self):
        features=[
          {"kind":"circle","center":[140,190],"radius":25,"id":"H1"},
          {"kind":"circle","center":[285,190],"radius":25,"id":"H2"},
          {"kind":"circle","center":[430,190],"radius":25,"id":"H3"},
          {"kind":"circle","center":[515,80],"radius":12,"id":"H4"},
        ]
        ann=parse_feature_notation("3X DIA 8 THRU")
        r=resolve(features,ann,[140,165])
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["feature_ids"],["H1","H2","H3"])

    def test_slot_target_with_external_jit_parse_shape(self):
        features=[
          {"kind":"slot","center":[300,160],"length":150,"width":42,"id":"S1"},
          {"kind":"circle","center":[100,160],"radius":24,"id":"H1"},
        ]
        # This object is the normalized output a JIT notation rule supplies.
        ann={"status":"PARSED","kind":"slot_feature","feature_kind":"slot","quantity":1,"width":42}
        r=resolve(features,ann,[225,160])
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["feature_id"],"S1")
        self.assertEqual(r["feature_kind"],"slot")

    def test_ambiguous_quantity_fails_to_choose(self):
        features=[
          {"kind":"circle","center":[150,180],"radius":24,"id":"H1"},
          {"kind":"circle","center":[300,180],"radius":24,"id":"H2"},
          {"kind":"circle","center":[450,180],"radius":24,"id":"H3"},
        ]
        ann=parse_feature_notation("2X DIA 8 THRU")
        r=resolve(features,ann,[300,156])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertEqual(r["reason"],"QUANTITY_SUBSET_NONUNIQUE")
        self.assertEqual(r["alternative_count"],2)

    def test_equal_leader_distance_is_ambiguous(self):
        features=[
          {"kind":"circle","center":[210,170],"radius":25,"id":"H1"},
          {"kind":"circle","center":[290,170],"radius":25,"id":"H2"},
        ]
        ann=parse_feature_notation("DIA 10 THRU")
        r=resolve(features,ann,[250,145])
        self.assertEqual(r["status"],"AMBIGUOUS")
        self.assertEqual(r["reason"],"LEADER_TARGET_NONUNIQUE")

if __name__=="__main__":
    unittest.main()
