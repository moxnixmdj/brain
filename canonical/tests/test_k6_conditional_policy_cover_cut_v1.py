from canonical.runtime.k6_conditional_policy_cover_cut_v1 import (
    conditional_policy_covers,
    construct_encoder_decoder,
    global_cardinality_false_sufficiency_counterexample,
    minimum_persistent_message_bits,
    minimum_persistent_message_states,
    verify_construction,
    zero_persistence_exact,
)


def test_zero_persistence_when_each_transcript_cell_has_common_policy():
    worlds=("w0","w1","w2","w3")
    policies=("p0","p1")
    adequate={
        "w0":("p0",),"w1":("p0",),
        "w2":("p1",),"w3":("p1",),
    }
    transcript={"w0":"t0","w1":"t0","w2":"t1","w3":"t1"}
    assert zero_persistence_exact(worlds,policies,adequate,transcript)
    assert minimum_persistent_message_bits(worlds,policies,adequate,transcript)==0
    assert verify_construction(worlds,policies,adequate,transcript)


def test_one_bit_needed_when_same_transcript_cell_contains_disjoint_policy_needs():
    worlds=("w0","w1")
    policies=("p0","p1")
    adequate={"w0":("p0",),"w1":("p1",)}
    transcript={"w0":"same","w1":"same"}
    assert minimum_persistent_message_states(worlds,policies,adequate,transcript)==2
    assert minimum_persistent_message_bits(worlds,policies,adequate,transcript)==1
    assert verify_construction(worlds,policies,adequate,transcript)


def test_global_cardinality_is_not_sufficient_for_zero_persistence():
    out=global_cardinality_false_sufficiency_counterexample()
    assert out["global_tau"]==2
    assert out["S"]==2
    assert out["global_cardinality_zero_lower_bound_trigger"] is True
    assert out["exact_conditional_states"]==2
    assert out["exact_conditional_bits"]==1
    assert out["construction_valid"] is True


def test_pairwise_common_policy_is_not_enough_for_zero_persistence():
    worlds=("w0","w1","w2")
    policies=("p1","p2","p3")
    adequate={
        "w0":("p1","p2"),
        "w1":("p2","p3"),
        "w2":("p1","p3"),
    }
    transcript={w:"same" for w in worlds}
    covers=conditional_policy_covers(worlds,policies,adequate,transcript)
    assert len(covers["same"])==2
    assert minimum_persistent_message_bits(worlds,policies,adequate,transcript)==1


def test_side_information_reduces_message_bits_exactly():
    worlds=("w0","w1","w2","w3")
    policies=("p0","p1","p2","p3")
    adequate={w:(f"p{i}",) for i,w in enumerate(worlds)}
    no_side={w:"same" for w in worlds}
    with_side={"w0":"a","w1":"a","w2":"b","w3":"b"}
    full_side={w:w for w in worlds}
    assert minimum_persistent_message_bits(worlds,policies,adequate,no_side)==2
    assert minimum_persistent_message_bits(worlds,policies,adequate,with_side)==1
    assert minimum_persistent_message_bits(worlds,policies,adequate,full_side)==0


def test_constructed_decoder_uses_same_message_labels_across_transcripts():
    worlds=("w0","w1","w2","w3")
    policies=("a","b","c","d")
    adequate={"w0":("a",),"w1":("b",),"w2":("c",),"w3":("d",)}
    transcript={"w0":"x","w1":"x","w2":"y","w3":"y"}
    built=construct_encoder_decoder(worlds,policies,adequate,transcript)
    assert built["persistent_states"]==2
    assert built["persistent_bits"]==1
    assert set(built["encoder"].values()) <= {0,1}
    assert verify_construction(worlds,policies,adequate,transcript)
