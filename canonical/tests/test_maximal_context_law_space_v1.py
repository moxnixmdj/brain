import unittest
from canonical.runtime.maximal_context_law_space_v1 import certificate,residual,top_element

class T(unittest.TestCase):
    def test_maximal_k_contains_target(self):
        L={"a","b","c"}
        dom=lambda x,y: x==y
        x=certificate(L,"b","a",dom)
        self.assertTrue(x["maximal_k_complete_for_target"])
        self.assertFalse(x["target_information_required_for_completeness"])

    def test_top_deletes_residual(self):
        L={"a","b","c"}
        dom=lambda x,y: x=="top" or x==y
        L.add("top")
        self.assertTrue(top_element(L,"top",dom))
        self.assertEqual(residual(L,"top",dom),set())

    def test_non_top_leaves_only_undominated(self):
        L={"a","b","c"}
        dom=lambda x,y: (x,y) in {("a","a"),("a","b")} or x==y
        self.assertEqual(residual(L,"a",dom),{"c"})

    def test_sound_restriction_can_empty_residual(self):
        L={"a","b","c"}
        dom=lambda x,y: (x,y) in {("a","a"),("a","b")} or x==y
        x=certificate(L,"b","a",dom,target_subset={"a","b"})
        self.assertTrue(x["pass"])
        self.assertEqual(x["restricted_residual"],[])

    def test_unsound_restriction_fails(self):
        L={"a","b","c"}
        dom=lambda x,y: x==y
        x=certificate(L,"c","a",dom,target_subset={"a","b"})
        self.assertFalse(x["pass"])
        self.assertEqual(x["reason"],"UNSOUND_TARGET_RESTRICTION")

if __name__=="__main__":
    unittest.main(verbosity=2)
