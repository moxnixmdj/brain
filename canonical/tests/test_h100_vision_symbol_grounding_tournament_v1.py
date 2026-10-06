import itertools,unittest
from canonical.runtime import h100_vision_symbol_grounding_tournament_v1 as g

class T(unittest.TestCase):
 def test_four_glyph_class_has_24_worlds(self):
  self.assertEqual(g.hidden_mapping_class_size(4),24)
 def test_perfect_universal_grounding_needs_five_bits_without_legend(self):
  self.assertEqual(g.persistent_bits_lower_bound_without_legend(4),5)
 def test_zero_bit_universal_success_without_legend_is_one_over_24(self):
  self.assertEqual(g.universal_zero_bit_success_upper_bound_without_legend(4),1/24)
 def test_complete_runtime_legend_collapses_mapping_ambiguity(self):
  glyphs=["G_A","G_D","G_B","G_C"]
  for perm in itertools.permutations([0,1,2,3]):
   legend=dict(zip(["G_A","G_B","G_C","G_D"],perm))
   self.assertEqual(g.resolve_with_runtime_legend(glyphs,legend),[legend[x] for x in glyphs])
 def test_incomplete_legend_fails_closed(self):
  with self.assertRaises(g.VisionGroundingError):
   g.resolve_with_runtime_legend(["G_A","G_B"],{"G_A":0})
if __name__=="__main__": unittest.main(verbosity=2)
