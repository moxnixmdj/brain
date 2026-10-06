import json,unittest
from canonical.runtime import h100_stateless_external_registry_v1 as r

M=[
 {"capability_id":"A","sequence":["square","log1p_abs","sqrt_abs","sat"]},
 {"capability_id":"B","sequence":["sat","square","log1p_abs","sqrt_abs"]},
 {"capability_id":"C","sequence":["log1p_abs","sat","sqrt_abs","log1p_abs"]}
]
XS=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-.6,-.2,0,.4,.8,1,1.5,2,2.5,3,3.5,4]
def rows(seq,a,b,c):
 return [{"x":x,"y":a+b*x+c*r._apply(x,seq)} for x in XS]

class T(unittest.TestCase):
 def test_three_external_recipes_hit(self):
  specs=[
   ("A",M[0]["sequence"],-.7,.31,-.85),
   ("B",M[1]["sequence"],.9,-.22,1.4),
   ("C",M[2]["sequence"],-.35,-.08,.72)
  ]
  for cid,seq,a,b,c in specs:
   out=r.resolve(rows(seq,a,b,c),M)
   self.assertEqual(out["status"],"HIT")
   self.assertEqual(out["capability_id"],cid)
   self.assertEqual(out["internal_persistent_causal_learned_bits"],0)
   x=1.37
   self.assertAlmostEqual(r.predict(out,{"x":x}),a+b*x+c*r._apply(x,seq),places=8)
 def test_manifest_information_is_not_zero(self):
  n=len(json.dumps(M,sort_keys=True,separators=(",",":")).encode())
  self.assertGreater(n,0)
 def test_unknown_structure_misses(self):
  seq=["square","sat","log1p_abs","sqrt_abs"]
  self.assertEqual(r.resolve(rows(seq,.2,.13,.88),M)["status"],"MISS")
if __name__=="__main__": unittest.main(verbosity=2)
