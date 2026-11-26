"""A plan is not an observation, a COW snapshot is not a universe of programs.

Set BRAIN_TEST_CHROME to an experimental WebMCP-capable browser executable
inside a loopback-only user+net namespace for the live refusal/reload check.
"""
import os
from pathlib import Path
import socket
import time

import pytest
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.creature_runtime_v1 import Creature
from canonical.runtime import witnessed_browser_v1 as browser
from canonical.swe_kernel.reset_probe_v1 import predict
from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore


def test_crash_timeout_and_outside_space_are_not_identifications():
    model=open_model();alarms=[]
    def writes(x):alarms.append(x);return len(alarms)
    assert predict(writes,'a')==predict(writes,'b')==1 and alarms==[]
    with pytest.raises(ValueError,match='timed out'):predict(lambda _:time.sleep(.5),0,timeout=.025)
    kw={'candidate_probes':[{'id':'safe','input':'a'}, {'id':'skip','input':'b','irreversible':True}]}
    dead=model.minimax_interrogate_version_space(hypotheses={'A':lambda _:os._exit(2),'B':str},**kw)
    assert dead['pass'] is False and dead['status']=='UNMEASURED_PREDICTION'
    probes=[]
    def third(x):probes.append(x);return None
    out=model.minimax_interrogate_version_space(hypotheses={'a':lambda _:0,'b':lambda _:False},true_oracle=third,**kw)
    assert out['status']=='OUTSIDE_DECLARED_SPACE' and out['resolved_policy_ids']==[]
    assert out['cow_predictions']==2 and probes==['a'] and out['gated_irreversible_probes']==['skip']


def test_readonly_tool_and_no_passive_slot_promotion():
    t={'name':'paint','description':'paint a label', 'schema':{'type':'object','properties':{'color':{'type':'string'}},'required':['color']},'annotations':{}}
    row={'slot':'color','tool':'paint','schema':browser.digest(t['schema']),'args':{'color':'oak'},'goal':'Go oak','literal_context':['Go ','']}
    assert browser.propose('Go fir',[t],lesson=row,arm='lifted') is None
    assert browser.propose('What paint is this?', [t]) is None
    assert browser.admit_slot(row,{'status':'PLAN_ONLY','surviving_worlds':['slot']})==row
    with pytest.raises(ValueError):browser.step(None,'paint',origin='https://external.invalid')


@pytest.mark.skipif(not os.environ.get('BRAIN_TEST_CHROME'),reason='live local Chromium not configured')
def test_registered_handle_read_refusal_and_actual_reloaded_slot(tmp_path):
    from canonical.tools.live_interface_trial_v1 import CALIBRATION, serving, fresh_room
    assert {n for _,n in socket.if_nameindex()}=={'lo'}
    exe=os.environ['BRAIN_TEST_CHROME'];page=tmp_path/'page';page.mkdir();(page/'index.html').write_text(CALIBRATION)
    m=open_model();c=Creature('probe',tmp_path/'memory',100);path=c.root/'revisions.sqlite'
    with serving(page) as origin:
        g='Stamp "cedar"'
        with fresh_room(exe,origin) as room:
            no=m.live_browser_step('What stamp is visible?',room=room,origin=origin)
            assert no['status']=='NO_GROUNDING' and no['executed'] is False
            obs=m.live_browser_step(g,room=room,origin=origin,expected_text='cedar')
            assert obs['goal_verified'] and obs['tool_count']==1
            assert m.live_browser_step(g,room=room,origin=origin,expected_text='cedar')['status']=='ALREADY_VISIBLE_NO_ACTION'
        teacher=browser.induce(g,obs)
        def read_on_fresh(arg):
            with fresh_room(exe,origin) as room:
                result=c.live_browser_step(f'Stamp "{arg}"',room=room,origin=origin)
                assert result['executed'] and not result['goal_verified']
                return room.evaluate('document.querySelector("output").innerText')
        contrast=m.minimax_interrogate_version_space(hypotheses={'literal':lambda _:'cedar','slot':lambda x:x},
            candidate_probes=[{'input':'lilac'}],true_oracle=read_on_fresh)
        skill=browser.admit_slot(teacher,contrast); assert skill['slot_evidence'][0]['observed_output']=='lilac'
        c.revision_memory('set',key='skill',valid_from=1,source='page',witness=obs['after'],value=skill)
        for version,route in [(1,'lifted'),(2,'schema')]:
            if version==2:c.revision_memory('delete',key='skill',valid_from=2,source='control',witness='retraction')
            row=RevisionStore(path).query('skill')
            with fresh_room(exe,origin) as room:
                r=m.live_browser_step('Stamp "fir"',room=room,origin=origin,lesson=row['value'],arm='lifted',expected_text='fir')
                assert r['goal_verified'] and r['action']['route']==route


def test_single_patch_zygote_is_bounded_and_reports_only_actual_assertions(tmp_path):
    from canonical.runtime.cow_zygote_speculative_verifier_v1 import verify_candidate_patch_cow as check
    original='def f(x): return x';patch='def f(x): return x + 1';test='def test_f(): assert f(2)==3'
    assert check(original,original,test)['failed_test']=='test_f'
    ok=check(original,patch,test);assert ok['verdict']=='PASS' and ok['tested']==['test_f']
    assert check(original,patch,'def helper():pass')['verdict']=='UNMEASURED'
    assert check(original,patch,'from app import f\n'+test)['verdict']=='UNMEASURED'
    assert check(original,'def f(x):\n while True: pass',test,timeout_s=.05)['verdict']=='UNMEASURED'
    assert check(original,'import os\ndef f(x): os._exit(3)',test)['verdict']=='UNMEASURED'


def test_federation_does_not_promote_no_test_and_default_hard_rung_abstains():
    from canonical.runtime.unified_hidden_capability_federation_v1 import run_federated_engine
    r=run_federated_engine('COW_ZYGOTE_SPECULATIVE_VERIFIER',{'original_module_source':'x=1','candidate_patch_source':'x=2','test_suite_source':'pass'})
    assert not r['pass'] and r['reason']=='COW_CANDIDATE_UNMEASURED'
    r=open_model().partial_route_with_jitrl('PARTIAL_ROUTE', {'subtasks':[{'kind':'unhandled','difficulty':1.0}]})
    assert not r['pass'] and r['pluggable_proposer_calls']==r['model_calls']==0
    assert r['rung_counts']['ABSTAINED']==1 and r['routed_subtasks'][0]['output'] is None
