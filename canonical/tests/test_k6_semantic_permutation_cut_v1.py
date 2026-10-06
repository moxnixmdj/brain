from canonical.runtime.k6_semantic_permutation_cut_v1 import best_symmetric_worst_case,mapping_aware_success,success_pair,verify

def test_identical_observation_forces_tradeoff():
    assert success_pair(1.0)==(1.0,0.0)
    assert success_pair(0.0)==(0.0,1.0)
    assert success_pair(0.5)==(0.5,0.5)

def test_best_worst_case_is_half():
    assert best_symmetric_worst_case()==0.5

def test_mapping_breaks_symmetry():
    assert mapping_aware_success()==(1.0,1.0)

def test_verifier():
    assert verify()["mapping_breaks_symmetry"] is True
