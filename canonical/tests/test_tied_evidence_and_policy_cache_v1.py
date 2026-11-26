from canonical.runtime.wave39_leapfrog_unification_v1 import CLMRRFMemoryEngine
from canonical.swe_kernel.meta_circular_organ_graph_v1 import compile_policy_organ


def test_copy_policy_data_not_a_shared_live_namespace():
    a=compile_policy_organ(); b=compile_policy_organ()
    a.ensure_compiled(); b.ensure_compiled()
    assert a._ns is not b._ns and a._fn is not b._fn
    a.metadata['empirical_burns']['change']=1
    assert 'change' not in b.metadata['empirical_burns']
    assert a.source_code==b.source_code


def test_unrecognized_or_missing_origin_is_never_verifier_evidence():
    e=CLMRRFMemoryEngine();args=dict(record_id='rec',key='greeting',verbatim_text='hi',valid_from=1)
    assert not e.write_surprise_gated(**args,origin_token='typo')['admitted']
    assert e.write_surprise_gated(**args)['admitted']
    assert e.retrieve_4way_rrf_budgeted('hi')['results'][0]['origin_token']=='UNTRUSTED_EXTERNAL'
    for token,expected in [('USER_DIRECT','TRUSTED_USER'),('UNTRUSTED_RETRIEVAL','UNTRUSTED_EXTERNAL'),('RUNTIME_OBSERVATION','DERIVED_INTERNAL')]:
        r=e.write_surprise_gated(**{**args,'record_id':token},min_surprise=0,origin_token=token)
        assert r['admitted'] and e.memory_bus.verify_origin_binding(token)['origin_class']==expected


def test_constant_channels_do_not_vote_for_lexical_order_of_ids():
    for ids in [('z','a','b'),('a','z','b')]:
        e=CLMRRFMemoryEngine()
        for ident,text in zip(ids,['needed word','other content','unrelated text']):
            e.write_surprise_gated(record_id=ident,key=ident,verbatim_text=text,valid_from=1,min_surprise=0,origin_token='USER_DIRECT')
        r=e.retrieve_4way_rrf_budgeted('needed',top_k=3)['results']
        assert r[0]['record_id']==ids[0]
        assert [v['channel_ranks']['temporal_entity'] for v in r]==[2]*3
        assert [v['channel_ranks']['lexical'] for v in r]==[1,2.5,2.5]
