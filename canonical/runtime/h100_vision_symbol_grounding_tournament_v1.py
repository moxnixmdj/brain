from __future__ import annotations

class VisionGroundingError(ValueError): pass

def factorial(n):
 if not isinstance(n,int) or isinstance(n,bool) or n<1: raise VisionGroundingError("N_INVALID")
 out=1
 for x in range(2,n+1): out*=x
 return out

def ceil_log2(n):
 if n<1: raise VisionGroundingError("N_INVALID")
 return 0 if n==1 else (n-1).bit_length()

def hidden_mapping_class_size(glyph_count):
 return factorial(glyph_count)

def persistent_bits_lower_bound_without_legend(glyph_count):
 return ceil_log2(hidden_mapping_class_size(glyph_count))

def universal_zero_bit_success_upper_bound_without_legend(glyph_count):
 return 1.0/hidden_mapping_class_size(glyph_count)

def resolve_with_runtime_legend(glyph_sequence,legend):
 if not isinstance(legend,dict): raise VisionGroundingError("LEGEND_INVALID")
 if len(set(legend.values()))!=len(legend): raise VisionGroundingError("LEGEND_NOT_BIJECTIVE")
 out=[]
 for g in glyph_sequence:
  if g not in legend: raise VisionGroundingError("GLYPH_UNGROUNDED")
  out.append(legend[g])
 return out

def certificate(glyph_count=4):
 return {
  "glyph_count":glyph_count,
  "mapping_class_size":hidden_mapping_class_size(glyph_count),
  "persistent_bits_lower_bound_without_legend":persistent_bits_lower_bound_without_legend(glyph_count),
  "zero_bit_success_upper_bound_without_legend":universal_zero_bit_success_upper_bound_without_legend(glyph_count),
  "persistent_target_bits_required_with_complete_runtime_legend":0
 }
