from canonical.runtime.bytes_sequence_characteristic_set_v1 import (
 evaluate,scalar_equal,sequence_components,signature,CHARACTERISTIC
)

def test_exact_counts_and_characteristic_set():
 o=evaluate()
 assert o["pass"] is True
 assert o["program_count"]==2955
 assert o["pointwise_exact_classes"]==200
 assert o["sequence_global_equivalence_components"]==809
 assert o["characteristic_set_size"]==7
 assert o["distinct_characteristic_signatures"]==809

def test_symbolic_pointwise_equivalences():
 assert scalar_equal("A","NA")
 assert scalar_equal("P","NMA")
 assert scalar_equal("2O","AM")
 assert not scalar_equal("P","M")

def test_characteristic_signatures_unique_on_component_representatives():
 cc=sequence_components()
 sig=[signature(c[0]) for c in cc]
 assert len(sig)==len(set(sig))==809

def test_no_component_member_disagrees_on_characteristic_set():
 for c in sequence_components():
  s=signature(c[0])
  assert all(signature(p)==s for p in c)
