import unittest
from canonical.runtime import h100_portfolio_capability_accounting_v1 as a

S1="1"*64; S2="2"*64; S3="3"*64; S4="4"*64

class T(unittest.TestCase):
 def setUp(self):
  self.arts=[
   a.artifact("shared",S1,100,"SHARED_CAPABILITY"),
   a.artifact("capA",S2,20,"DETERMINISTIC_TARGET"),
   a.artifact("capB",S3,30,"LEARNED_TARGET"),
   a.artifact("aliasShared",S1,100,"SHARED_CAPABILITY"),
  ]
 def test_shared_counts_once_portfolio(self):
  m={"A":["shared","capA"],"B":["aliasShared","capB"]}
  r=a.report(m,self.arts,reference_machine_id="H100_U1_STACK_VM")
  self.assertEqual(r["portfolio_unique_bytes"],150)
  self.assertEqual(r["summed_standalone_bytes"],250)
  self.assertEqual(r["reuse_savings_bytes"],100)
  self.assertFalse(r["shared_capability_bytes_are_free"])
 def test_standalone_counts_shared(self):
  self.assertEqual(a.standalone_bytes(["shared","capA"],self.arts),120)
 def test_marginal_reuse_zero_for_existing_shared(self):
  self.assertEqual(a.marginal_bytes(["shared","capA"],["aliasShared","capB"],self.arts),30)
 def test_category_total_invariant(self):
  m={"A":["shared","capA"],"B":["capB"]}
  c=a.category_bytes(m,self.arts)
  self.assertEqual(c["TARGET_ADAPTED_TOTAL"],150)
 def test_duplicate_content_size_conflict_rejected(self):
  bad=self.arts+[a.artifact("bad",S1,101,"SHARED_CAPABILITY")]
  with self.assertRaises(a.PortfolioAccountingError): a.report({"A":["shared"]},bad,reference_machine_id="U")
 def test_unknown_ref_rejected(self):
  with self.assertRaises(a.PortfolioAccountingError): a.report({"A":["missing"]},self.arts,reference_machine_id="U")
if __name__=="__main__": unittest.main(verbosity=2)
