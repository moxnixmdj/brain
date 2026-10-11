import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/'canonical/runtime/capability_proof_compression_optimizer_v1.py'
S=importlib.util.spec_from_file_location('opt',P); opt=importlib.util.module_from_spec(S); S.loader.exec_module(opt)
class T(unittest.TestCase):
 def test_one_shared_certificate_beats_three_separate_receipts(self):
  req=[{'id':'A'},{'id':'B'},{'id':'C'}]
  ev=[
   {'id':'a','covers':['A'],'wall_clock_cost':5},
   {'id':'b','covers':['B'],'wall_clock_cost':5},
   {'id':'c','covers':['C'],'wall_clock_cost':5},
   {'id':'shared','covers':['A','B','C'],'wall_clock_cost':7,'reusable_coverage_bonus':9},
  ]
  r=opt.optimize(req,ev); self.assertTrue(r['complete_cover']); self.assertEqual(r['selected_evidence_ids'],['shared'])
 def test_wall_clock_dominates_reuse_bonus(self):
  req=[{'id':'A'}]
  ev=[{'id':'fast','covers':['A'],'wall_clock_cost':2,'reusable_coverage_bonus':0},{'id':'slow','covers':['A'],'wall_clock_cost':3,'reusable_coverage_bonus':999}]
  self.assertEqual(opt.optimize(req,ev)['selected_evidence_ids'],['fast'])
 def test_reuse_breaks_equal_wall_clock_tie(self):
  req=[{'id':'A'}]
  ev=[{'id':'x','covers':['A'],'wall_clock_cost':2,'reusable_coverage_bonus':1},{'id':'y','covers':['A'],'wall_clock_cost':2,'reusable_coverage_bonus':4}]
  self.assertEqual(opt.optimize(req,ev)['selected_evidence_ids'],['y'])
 def test_external_wait_paid_and_outsourced_rejected(self):
  req=[{'id':'A'}]
  ev=[
   {'id':'wait','covers':['A'],'wall_clock_cost':0,'waits_for_external_event':True},
   {'id':'paid','covers':['A'],'wall_clock_cost':0,'incremental_spend_usd':1},
   {'id':'model','covers':['A'],'wall_clock_cost':0,'external_runtime_cognition':1},
  ]
  r=opt.optimize(req,ev); self.assertFalse(r['complete_cover']); self.assertEqual(r['uncovered_required_propositions'],['A']); self.assertEqual(len(r['rejected']),3)
 def test_partial_cover_returns_exact_uncovered_set(self):
  req=[{'id':'A','weight':3},{'id':'B','weight':1},{'id':'C','weight':5}]
  ev=[{'id':'ab','covers':['A','B'],'wall_clock_cost':1},{'id':'b','covers':['B'],'wall_clock_cost':0}]
  r=opt.optimize(req,ev); self.assertFalse(r['complete_cover']); self.assertEqual(set(r['covered_required_propositions']),{'A','B'}); self.assertEqual(r['uncovered_required_propositions'],['C'])
 def test_no_credit_authority(self):
  r=opt.optimize([{'id':'A'}],[{'id':'x','covers':['A'],'wall_clock_cost':1}]); self.assertFalse(r['credit_authority'])
if __name__=='__main__': unittest.main(verbosity=2)
