from __future__ import annotations
import copy,unittest
from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as o
E={"scope_id":"PQ::R2::SEARCH_SEMANTICS::FINITE_SCOPE","root_id":"R2_CANDIDATE_SEARCH","contributes_to_leaf_ids":["PQ::R2_CANDIDATE_SEARCH::SEMANTIC"],"claim_kind":"FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS","source_receipt":{"path":"canonical/verification/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_20261010_V1.json","git_blob_sha":"06da6b94712ec844a56c0f663cce67f059b7ba8d"},"reusable_compiler":{"path":"canonical/runtime/professional_candidate_search_semantic_certificate_v1.py","git_blob_sha":"84c6dbd8e36c98dde74cf16252fe83ff0aad4baf"},"compiler_verification":{"path":"canonical/verification/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_20261010_V1.json","git_blob_sha":"06da6b94712ec844a56c0f663cce67f059b7ba8d"},"scope_governance":{"path":"canonical/governance/PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_SCOPE_20261010_V1.json","git_blob_sha":"c12893656c0546aafa79135dec221f2e5f7e9774"},"global_leaf_closure":False,"global_root_closure":False,"semantic_leaf_credit":False,"execution_leaf_credit":False,"terminal_credit_delta":0}
class T(unittest.TestCase):
 def test_ok(self):
  x=o.validate_entry(copy.deepcopy(E));self.assertTrue(x["admitted"],x);self.assertEqual(x["claim_scope"]["kind"],o.K)
 def test_stale(self):
  e=copy.deepcopy(E);e["source_receipt"]["git_blob_sha"]="0"*40;x=o.validate_entry(e);self.assertFalse(x["admitted"])
 def test_no_global(self):
  e=copy.deepcopy(E);e["global_leaf_closure"]=True;x=o.validate_entry(e);self.assertFalse(x["admitted"])
if __name__=="__main__":unittest.main(verbosity=2)
