import hashlib,json
from canonical.runtime.authenticated_pareto_scheduler_v1 import compile_schedule, ALL_KEYS
R='a'*64
def cand(cid,vals):
    m={k:float(vals.get(k,1)) for k in ALL_KEYS}; m['cost_usd_ucb']=float(vals.get('cost_usd_ucb',0))
    subject=hashlib.sha256(json.dumps({'candidate_id':cid,'metrics':m},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'candidate_id':cid,'metrics':m,'measurement_receipt':{'independently_verified':True,'sha256':R,'subject_sha256':subject}}
def test_authenticated_pareto_removes_dominated():
    a=cand('a',{'capability_gain_lcb':2,'generalization_lcb':2,'reliability_lcb':2,'reuse_breadth_lcb':2,'success_probability_lcb':2,'latency_ms_ucb':1,'compute_units_ucb':1,'memory_mb_ucb':1})
    b=cand('b',{'capability_gain_lcb':1,'generalization_lcb':1,'reliability_lcb':1,'reuse_breadth_lcb':1,'success_probability_lcb':1,'latency_ms_ucb':2,'compute_units_ucb':2,'memory_mb_ucb':2})
    out=compile_schedule([a,b]); assert out['pass'] is True and out['nondominated_candidate_ids']==['a']
def test_unbound_metrics_fail():
    c=cand('x',{}); c['metrics']['latency_ms_ucb']=999
    assert compile_schedule([c])['pass'] is False
def test_nonzero_spend_fails():
    assert compile_schedule([cand('x',{'cost_usd_ucb':0.01})])['pass'] is False
