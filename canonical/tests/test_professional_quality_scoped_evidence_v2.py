import unittest
from canonical.runtime import professional_quality_scoped_evidence_v2 as v

RUNTIME='58eca51f479d16a0b217f0b3f4129d0ef054a19f'
STATUS='PASS__MINIMAL_R10_KERNEL_EXACT_LEGACY_FUNCTION_EQUIVALENCE__5_OF_5__ZERO_GLOBAL_LEAF_CREDIT'

def entry():
    return {'root_id':v.R10_ROOT,'contributes_to_leaf_ids':sorted(v.R10_LEAVES),'global_leaf_closure':False,'global_root_closure':False,'semantic_leaf_credit':False,'execution_leaf_credit':False,'terminal_credit_delta':0}

def receipt():
    return {'schema':v.R10_SOURCE_SCHEMA,'status':STATUS,'exact_blobs':{'runtime':RUNTIME,'legacy_runtime':'b8347a3993f96aa5e6fa2f1fe68d7c8afccb8bec'},'replay':{'tests_run':5,'tests_passed':5,'tests_failed':0,'decision_contract_exact_legacy_output':True,'minimum_information_contract_exact_legacy_output':True},'claim_scope':{'kind':v.R10_KIND,'guarantees':['DECISION_SUFFICIENT_BASELINE_IS_LOSSLESS_IDENTITY_AND_CONTENT_ADDRESSED','NO_EVIDENCE_IS_OMITTED_WITHOUT_A_FUTURE_OMISSION_CERTIFICATE','MINIMUM_INFORMATION_REQUESTS_DEDUPLICATE_EVIDENCE_BLOCKERS','BROAD_ACQUISITION_IS_FORBIDDEN_WITHOUT_MINIMALITY_PROOF','FULL_EMPIRICAL_EVALUATION_REMAINS_LAST','PROVIDERS_CANNOT_MUTATE_VERIFICATION_AUTHORITY','FALSE_PROGRESS_WITH_UNCHANGED_FRONTIER_FAILS_CLOSED'],'limitations':['NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE','NO_NORMATIVE_AGGREGATION_CLOSURE','NO_MODEL_MULTIPLICITY_DECISION_CLOSURE','NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE']},'current_state':{'global_leaf_credit':False,'global_r10_root_closed':False,'domain_semantic_closure':False,'domain_execution_closure':False}}

class ScopedEvidenceV2R10Tests(unittest.TestCase):
    def test_valid(self):
        errors,scope=v._validate_r10(entry(),receipt(),receipt(),RUNTIME)
        self.assertEqual(errors,[])
        self.assertEqual(scope['kind'],v.R10_KIND)
    def test_equivalence_required(self):
        r=receipt(); r['replay']['decision_contract_exact_legacy_output']=False
        errors,_=v._validate_r10(entry(),r,r,RUNTIME)
        self.assertIn('SOURCE_DECISION_EQUIVALENCE_NOT_PROVED',errors)
    def test_runtime_required(self):
        r=receipt(); r['exact_blobs']['runtime']='0'*40
        errors,_=v._validate_r10(entry(),r,r,RUNTIME)
        self.assertIn('SOURCE_RUNTIME_MISMATCH',errors)
    def test_nonclosure_required(self):
        r=receipt(); r['claim_scope']['limitations'].remove('NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE')
        errors,_=v._validate_r10(entry(),r,r,RUNTIME)
        self.assertIn('SOURCE_SCOPE_LIMITATIONS_MISSING',errors)

if __name__=='__main__': unittest.main(verbosity=2)
