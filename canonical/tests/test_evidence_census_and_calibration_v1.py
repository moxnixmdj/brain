from canonical.tools.producer_source_census_v1 import census
from canonical.tools.replay_source_verifier_v1 import calibrated_controls


def test_calibration_zero_ptp_is_not_an_absent_negative_or_positive_control():
    required={'fail_to_pass':{'a','b'},'pass_to_pass':set()}
    nop={'exit':1,'reward_file':0,'required':{'fail_to_pass':{'FAILED':2},'pass_to_pass':{}}}
    ref={'exit':0,'reward_file':1,'required':{'fail_to_pass':{'PASSED':2},'pass_to_pass':{}}}
    assert calibrated_controls(required,nop,ref)
    nop['required']['fail_to_pass']={'MISSING':1,'FAILED':1}
    assert not calibrated_controls(required,nop,ref)
    nop['required']['fail_to_pass']={'FAILED':2};required['pass_to_pass'].add('c')
    assert not calibrated_controls(required,nop,ref)
    ref['required']['pass_to_pass']={'PASSED':1};nop['required']['pass_to_pass']={'PASSED':1}
    assert calibrated_controls(required,nop,ref)
    assert not calibrated_controls(required,nop,{**ref,'error':'TIMEOUT'})


def test_census_is_a_source_graph_not_a_runtime_measurement(tmp_path):
    r=tmp_path/'canonical/runtime';r.mkdir(parents=True)
    for f,s in {'brain_unified_model_v1':'if False:\n    from . import conditional\n',
                'conditional':"name='canonical.runtime.literal'\n",'literal':'x=1\n',
                'unrouted':'x=2\n','syntax':'if\n'}.items():
        (r/(f+'.py')).write_text(s)
    out=census(tmp_path)
    assert out['all']=={'modules':5,'physical_lines':6}
    assert out['reachable_imports']=={'modules':2,'physical_lines':3}
    assert out['reachable_with_literal_addresses']=={'modules':3,'physical_lines':4}
    assert out['parse_errors']==[['canonical/runtime/syntax.py','SyntaxError']]
