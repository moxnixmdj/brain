from canonical.runtime.precommit_isolation_guard_v2 import verify


H="0"*64
BASE={
 "committed_hashes":{"candidate":H,"harness":H,"scorer":H,"environment":H,"policy":H},
 "executed_hashes":{"candidate":H,"harness":H,"scorer":H,"environment":H,"policy":H},
 "commit_precedes_case_exposure":True,
 "independent_executor_controls_reveal":True,
 "no_evaluation_feedback_channel_to_candidate":True,
 "outputs_bound_to_precommitment":True,
 "benchmark_adapter":{"population":True,"scorer":True,"effort":True,"tools":True,"environment":True,"comparator":True},
}


def test_complete_antecedents_pass_but_do_not_authorize():
    out=verify(BASE)
    assert out["mechanical_antecedents_pass"] is True
    assert out["fresh_reality_authorized"] is False
    assert out["acceptance_credit_authorized"] is False


def test_hash_mismatch_fails():
    x=dict(BASE)
    x["executed_hashes"]=dict(BASE["executed_hashes"])
    x["executed_hashes"]["candidate"]="1"*64
    out=verify(x)
    assert out["mechanical_antecedents_pass"] is False
    assert "HASH_MISMATCH:candidate" in out["failures"]


def test_feedback_channel_fails():
    x=dict(BASE)
    x["no_evaluation_feedback_channel_to_candidate"]=False
    out=verify(x)
    assert out["mechanical_antecedents_pass"] is False


def test_thin_adapter_is_required():
    x=dict(BASE)
    x["benchmark_adapter"]=dict(BASE["benchmark_adapter"])
    x["benchmark_adapter"]["effort"]=False
    out=verify(x)
    assert out["mechanical_antecedents_pass"] is False
    assert "BENCHMARK_ADAPTER_INCOMPLETE" in out["failures"]
