from canonical.runtime.verified_improvement_loop_v1 import verify_loop, PHASES
HEX='abcdef0123456789'
def h(ch): return (ch*64)[:64]
def episode():
    receipts={}; prev=None
    for i,p in enumerate(PHASES):
        sha=h(HEX[i])
        row={'sha256':sha,'pass':True}
        if prev is not None: row['previous_phase_sha256']=prev
        if p=='verify': row['independently_verified']=True
        receipts[p]=row; prev=sha
    return {'episode_id':'e1','phase_receipts':receipts,
            'learned_route':{'route_id':'r1','behavior_sha256':h('b'),'scope_relation_sha256':h('c'),'behavior_preservation_verified':True},
            'neighbor_replays':[{'route_id':'r1','pass':True,'independently_verified':True,'sha256':h('d')},{'route_id':'r1','pass':True,'independently_verified':True,'sha256':h('e')}],
            'compression':{'quality_preserved':True,'receipt_sha256':h('f'),'resource_before':10,'resource_after':5}}
def test_complete_loop_yields_promotion_candidate_not_authority():
    out=verify_loop(episode()); assert out['pass'] is True and out['promotion_candidate'] is True and out['promotion_authority'] is False
def test_broken_phase_chain_fails():
    e=episode(); e['phase_receipts']['compose']['previous_phase_sha256']=h('9'); assert verify_loop(e)['pass'] is False
