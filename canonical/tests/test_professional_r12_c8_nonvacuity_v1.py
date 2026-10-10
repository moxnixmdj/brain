import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from copy import deepcopy
import unittest
from canonical.runtime import professional_r12_c8_nonvacuity_v1 as v

def docs():
    registry={
      "entries":[{
        "scope_id":v.SCOPE_ID,"root_id":v.ROOT_ID,
        "contributes_to_leaf_ids":[v.SEMANTIC_LEAF,v.EXECUTION_LEAF],
        "claim_kind":v.CLAIM_KIND,
        "source_receipt":{"path":v.CURRENTGEN_PATH,"git_blob_sha":v.CURRENTGEN_BLOB},
        "reusable_compiler":{"path":v.RUNTIME_PATH,"git_blob_sha":v.RUNTIME_BLOB},
        "compiler_verification":{"path":v.ORDER_PATH,"git_blob_sha":v.ORDER_BLOB},
        "scope_governance":{"path":v.SCOPE_PATH,"git_blob_sha":v.SCOPE_BLOB},
        "global_leaf_closure":False,"global_root_closure":False,"semantic_leaf_credit":False,
      }]
    }
    scope={
      "root_id":v.ROOT_ID,"claim_kind":v.CLAIM_KIND,
      "exact_components":{
        "runtime":{"path":v.RUNTIME_PATH,"git_blob_sha":v.RUNTIME_BLOB},
        "current_generation_replay":{"path":v.CURRENTGEN_PATH,"git_blob_sha":v.CURRENTGEN_BLOB},
        "order_soundness_verification":{"path":v.ORDER_PATH,"git_blob_sha":v.ORDER_BLOB},
      },
      "limitations":["NO_UNKNOWN_DEFEATER_COMPLETENESS","NO_DOMAIN_SEMANTIC_CLOSURE"],
      "global_leaf_closure":False,"global_root_closure":False,
    }
    execution={
      "status":"PASS__INDEPENDENT_SPRITE__EXACT",
      "subject":{"leaf_id":v.EXECUTION_LEAF,"root_id":v.ROOT_ID},
      "exact_blobs":{
        "uvck_runtime":v.RUNTIME_BLOB,
        "uvck_current_generation_verification":v.CURRENTGEN_BLOB,
        "uvck_defeater_order_verification":v.ORDER_BLOB,
      },
      "independent_replay":{"observed_case_counts":{"positive":2,"total":24}},
      "hard_nonclaims":["NO_R12_SEMANTIC_LEAF_CLOSURE","NO_UNKNOWN_DEFEATER_COMPLETENESS"],
      "r12_semantic_leaf_closed":False,"unknown_defeater_completeness_proved":False,
    }
    return registry,scope,execution

class Tests(unittest.TestCase):
    def test_same_scoped_runtime_plus_observed_positive_path_proves_only_c8(self):
        o=v.evaluate_documents(*docs())
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["c8_nonvacuity_proved"])
        self.assertEqual(o["positive_supported_route_count"],2)
        self.assertFalse(o["stronger_material_defeater_totality_proved"])
        self.assertFalse(o["semantic_property_truth_authority"])
    def test_semantic_leaf_must_be_in_same_scope(self):
        d=list(docs());d[0]=deepcopy(d[0]);d[0]["entries"][0]["contributes_to_leaf_ids"]=[v.EXECUTION_LEAF]
        o=v.evaluate_documents(*d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"R12_SCOPE_DOES_NOT_BIND_BOTH_LEAVES")
    def test_runtime_blob_mismatch_fails(self):
        d=list(docs());d[2]=deepcopy(d[2]);d[2]["exact_blobs"]["uvck_runtime"]="0"*40
        o=v.evaluate_documents(*d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"EXECUTION_RUNTIME_BINDING_DRIFT")
    def test_no_positive_case_does_not_prove_nonvacuity(self):
        d=list(docs());d[2]=deepcopy(d[2]);d[2]["independent_replay"]["observed_case_counts"]["positive"]=0
        o=v.evaluate_documents(*d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"NO_OBSERVED_POSITIVE_R12_ROUTE")
    def test_scope_credit_inflation_fails(self):
        d=list(docs());d[0]=deepcopy(d[0]);d[0]["entries"][0]["semantic_leaf_credit"]=True
        o=v.evaluate_documents(*d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"R12_SCOPE_AUTHORITY_INFLATION")
    def test_unknown_defeater_boundary_is_mandatory(self):
        d=list(docs());d[1]=deepcopy(d[1]);d[1]["limitations"]=["NO_DOMAIN_SEMANTIC_CLOSURE"]
        o=v.evaluate_documents(*d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"UNKNOWN_DEFEATER_BOUNDARY_MISSING")

if __name__=="__main__": unittest.main(verbosity=2)
