import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import capability_parallel_frontier_post_composition_v1 as m

IDS=["PQ::R1_TARGET_SPECIFICATION::EXECUTION","PQ::R2_CANDIDATE_SEARCH::EXECUTION","PQ::R3_REALIZATION_OBSERVATION::EXECUTION","PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION","PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION","PQ::R10_ANALYSIS_DECISION::EXECUTION","PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION"]

def row(closed=7,oe=5,os=12,ids=None):
 return {"work_id":"NEW_LABEL","source":m.PROF_SOURCE,"mutation_keys":[m.PROF_MUTATION_KEY],"authority_keys":[m.PROF_AUTHORITY_KEY],"evidence_acquisition_mode":"READ_ONLY","read_only_evidence":{"whole_leaf_scope_complete_count":24,"property_truth_closed_count":closed,"verified_property_truth_leaf_ids":IDS if ids is None else ids,"open_execution_leaf_count":oe,"open_semantic_leaf_count":os,"semantic_shared_blocker_independently_verified":True,"semantic_catalog_alone_can_close":False}}

def write(root,closed=7,oe=5,os=12,ids=None):
 p=root/m.PROF_SOURCE;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps({"property_truth_frontier":{"verified_leaf_count":closed,"open_execution_leaf_count":oe,"open_semantic_leaf_count":os,"verified_leaf_ids":IDS if ids is None else ids}}))

class T(unittest.TestCase):
 def test_currentness_and_guards(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);write(root)
   with patch.object(m.core,"ROOT",root):
    out=m._assert_post_composition({"candidates":[row()]})
    self.assertEqual((out["property_truth_closed_count"],out["open_execution_leaf_count"],out["open_semantic_leaf_count"]),(7,5,12))
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"EVIDENCE_DRIFT"):
     m._assert_post_composition({"candidates":[row(5,7,12,IDS[:5])]})
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"CARDINALITY"):
     m._assert_post_composition({"candidates":[row(),row()]})
    bad=row();bad["evidence_acquisition_mode"]="WRITE"
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"NOT_READ_ONLY"):
     m._assert_post_composition({"candidates":[bad]})
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"ACCOUNTING"):
     m._assert_post_composition({"candidates":[row(7,6,12)]})
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"COUNT_MISMATCH"):
     m._assert_post_composition({"candidates":[row(7,5,12,IDS[:6])]})
