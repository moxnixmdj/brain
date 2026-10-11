import unittest
from canonical.runtime.hle_native_total_solver_v2 import solve
def none(**k):return {'status':'NO_CANDIDATE','candidate_answer':None,'candidate_answer_authority':False,'external_model_calls':0,'external_reasoning_model_calls':0,'model_dependency_count':0}
def mcq(**k):return {'status':'CANDIDATE_GENERATED','candidate_answer':'C','candidate_answer_authority':False,'confidence_band':'HIGH','external_model_calls':0,'model_dependency_count':0}
def lark(**k):return {'status':'CANDIDATE_GENERATED','candidate_answer':'55','candidate_answer_authority':False,'external_model_calls':0,'external_reasoning_model_calls':0,'model_dependency_count':0}
def surface(**k):return {'status':'CANDIDATE_GENERATED','candidate_answer':'7','candidate_answer_authority':False,'external_model_calls':0,'model_dependency_count':0}
def retr(**k):return {'status':'CANDIDATE_GENERATED','candidate_answer':'Alpha','candidate_answer_authority':False,'confidence_band':'MEDIUM','external_model_calls':0,'model_dependency_count':0}
def obs(**k):return {'status':'OBSERVED','image_sha256':'a'*64,'ocr_text':'x=2','ocr_text_sha256':'b'*64,'ocr_chars':3,'local_ocr_tool_used':True}
class T(unittest.TestCase):
 def test_lark_precedes_old_surface(self):
  o=solve(task_id='a',question='Compute math.',mcq_proposer=mcq,symbolic_lark_proposer=lark,symbolic_surface_proposer=surface,retrieval_proposer=retr,image_observer=obs)
  self.assertEqual(o['final_answer'],'55');self.assertEqual(o['selected_lane'],'SYMBOLIC_LARK_V2')
 def test_surface_fallback(self):
  o=solve(task_id='b',question='Compute math.',mcq_proposer=mcq,symbolic_lark_proposer=none,symbolic_surface_proposer=surface,retrieval_proposer=retr,image_observer=obs)
  self.assertEqual(o['final_answer'],'7')
 def test_retrieval_fallback(self):
  o=solve(task_id='c',question='What thing?',mcq_proposer=mcq,symbolic_lark_proposer=none,symbolic_surface_proposer=none,retrieval_proposer=retr,image_observer=obs)
  self.assertEqual(o['final_answer'],'Alpha')
 def test_mcq(self):
  o=solve(task_id='d',question='Q\nAnswer Choices:\nA. a\nB. b\nC. c',mcq_proposer=mcq,symbolic_lark_proposer=lark,symbolic_surface_proposer=surface,retrieval_proposer=retr,image_observer=obs)
  self.assertEqual(o['final_answer'],'C');self.assertEqual(o['selected_lane'],'MCQ_RETRIEVAL_VOTE')
 def test_abstention(self):
  o=solve(task_id='e',question='Unknown.',mcq_proposer=mcq,symbolic_lark_proposer=none,symbolic_surface_proposer=none,retrieval_proposer=none,image_observer=obs)
  self.assertEqual(o['final_answer'],'UNKNOWN');self.assertTrue(o['precommittable'])
 def test_no_hidden_answer_type(self):
  o=solve(task_id='f',question='Unknown.',mcq_proposer=mcq,symbolic_lark_proposer=none,symbolic_surface_proposer=none,retrieval_proposer=none,image_observer=obs)
  self.assertFalse(o['answer_type_metadata_used']);self.assertTrue(o['answer_type_inferred_from_visible_question_only'])
 def test_no_external_solver_model(self):
  o=solve(task_id='g',question='Unknown.',mcq_proposer=mcq,symbolic_lark_proposer=none,symbolic_surface_proposer=none,retrieval_proposer=none,image_observer=obs)
  self.assertEqual(o['external_reasoning_model_calls'],0);self.assertFalse(o['external_model_solver_output_used']);self.assertFalse(o['brain_capability_claim_from_external_model'])
if __name__=='__main__':unittest.main(verbosity=2)
