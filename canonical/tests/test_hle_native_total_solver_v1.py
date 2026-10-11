import unittest
from canonical.runtime.hle_native_total_solver_v1 import solve

def no_search(q,limit=10): return {'status':'NO_RESULTS','results':[]}
def no_fetch(u,max_bytes=1): return {'status':'FAILED'}
def mcq(**k): return {'status':'CANDIDATE_GENERATED','candidate_answer':'B','candidate_answer_authority':False,'confidence_band':'HIGH','external_model_calls':0,'model_dependency_count':0}
def sym(**k): return {'status':'CANDIDATE_GENERATED','candidate_answer':'5','candidate_answer_authority':False,'external_model_calls':0,'model_dependency_count':0}
def no_sym(**k): return {'status':'FAIL_CLOSED','candidate_answer':None,'candidate_answer_authority':False,'external_model_calls':0,'model_dependency_count':0}
def retr(**k): return {'status':'CANDIDATE_GENERATED','candidate_answer':'Quartz Lattice','candidate_answer_authority':False,'confidence_band':'MEDIUM','external_model_calls':0,'model_dependency_count':0}
def no_retr(**k): return {'status':'NO_CANDIDATE','candidate_answer':None,'candidate_answer_authority':False,'external_model_calls':0,'model_dependency_count':0}
def obs(**k): return {'status':'OBSERVED','image_sha256':'a'*64,'ocr_text':'diagram says 7','ocr_text_sha256':'b'*64,'ocr_chars':14,'local_ocr_tool_used':True,'intrinsic_brain_vision_claimed':False}

class T(unittest.TestCase):
    def test_mcq(self):
        q='Choose.\nAnswer Choices:\nA. x\nB. y'
        o=solve(task_id='m',question=q,mcq_proposer=mcq,symbolic_proposer=sym,retrieval_proposer=retr,image_observer=obs,search_fn=no_search,fetch_fn=no_fetch)
        self.assertEqual(o['final_answer'],'B');self.assertEqual(o['selected_lane'],'MCQ_RETRIEVAL_VOTE')
    def test_symbolic(self):
        o=solve(task_id='s',question='Compute 2+3.',mcq_proposer=mcq,symbolic_proposer=sym,retrieval_proposer=retr,image_observer=obs)
        self.assertEqual(o['final_answer'],'5');self.assertFalse(o['abstained'])
    def test_retrieval_fallback(self):
        o=solve(task_id='r',question='What is it?',mcq_proposer=mcq,symbolic_proposer=no_sym,retrieval_proposer=retr,image_observer=obs,search_fn=no_search,fetch_fn=no_fetch)
        self.assertEqual(o['final_answer'],'Quartz Lattice');self.assertEqual(o['selected_lane'],'EXACT_RETRIEVAL_V2')
    def test_abstain_totality(self):
        o=solve(task_id='u',question='Hard unknown.',mcq_proposer=mcq,symbolic_proposer=no_sym,retrieval_proposer=no_retr,image_observer=obs,search_fn=no_search,fetch_fn=no_fetch)
        self.assertEqual(o['final_answer'],'UNKNOWN');self.assertTrue(o['precommittable']);self.assertTrue(o['abstained'])
    def test_image_observation_not_intrinsic_vision(self):
        o=solve(task_id='i',question='What value is shown?',image='data:image/png;base64,abc',mcq_proposer=mcq,symbolic_proposer=sym,retrieval_proposer=retr,image_observer=obs)
        self.assertEqual(o['final_answer'],'5');self.assertFalse(o['image_observation']['intrinsic_brain_vision_claimed'])
    def test_no_external_model_substitution(self):
        o=solve(task_id='x',question='Hard unknown.',mcq_proposer=mcq,symbolic_proposer=no_sym,retrieval_proposer=no_retr,image_observer=obs,search_fn=no_search,fetch_fn=no_fetch)
        self.assertEqual(o['external_reasoning_model_calls'],0)
        self.assertFalse(o['external_model_solver_output_used'])
        self.assertFalse(o['brain_capability_claim_from_external_model'])
        self.assertFalse(o['target_score_claimed'])
if __name__=='__main__':unittest.main(verbosity=2)
