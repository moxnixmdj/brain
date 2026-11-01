"""Retained-plan reuse is measured across processes and rechecked after change."""
import json
from pathlib import Path
import subprocess
import sys

from canonical.runtime import transfer_learning_v1 as transfer
from canonical.runtime import universal_learning_contract_v1 as contract

ROOT = Path(__file__).resolve().parents[2]

WORKER = r'''
import json, sys
from pathlib import Path
from canonical.runtime import transfer_learning_v1 as transfer
transfer.STATE_PATH = sys.argv[1]
class Environment:
    def __init__(self): self.x=0; self.calls=0; self.resets=0
    def reset(self): self.x=0; self.resets+=1
    def state(self): return self.x
    def act(self, action):
        self.calls+=1
        self.x=0 if sys.argv[2]=='changed' else 1-self.x
env=Environment()
result=transfer.drive(env,['toggle'],is_goal=lambda x:x==1,goal_key='reach-one',budget=8,max_depth=1,use_transfer=sys.argv[3]!='disabled')
print(json.dumps({'result':result,'actual_calls':env.calls,'actual_resets':env.resets}))
'''


def execute(state, mode, *, use_transfer=True):
    child = subprocess.run([sys.executable, '-B', '-c', WORKER, str(state), mode, 'enabled' if use_transfer else 'disabled'], cwd=ROOT,
                           text=True, capture_output=True, check=True, timeout=10)
    return json.loads(child.stdout)


def test_reuse_survives_restart_and_counts_probe_work(tmp_path):
    state = tmp_path/'episodes.json'
    first = execute(state, 'initial')
    second = execute(state, 'repeat')
    assert first['result']['pass'] is True
    assert first['result']['transferred'] is False
    assert first['result']['episode_persisted'] is True
    assert second['result']['pass'] is True
    assert second['result']['transferred'] is True
    assert second['result']['trials_spent'] < first['result']['trials_spent']
    for run in (first, second):
        assert run['result']['interactions']['act_calls'] == run['actual_calls']
        assert run['result']['interactions']['reset_calls'] == run['actual_resets']
        assert run['result']['retention_policy']['all_experiences_retained_forever'] is False
    assert second['actual_calls'] > second['result']['trials_spent']
    baseline = execute(state, 'repeat', use_transfer=False)
    assert baseline['result']['pass'] is True
    assert baseline['result']['transferred'] is False
    assert second['actual_calls'] < baseline['actual_calls']


def test_changed_environment_does_not_inherit_success_authority(tmp_path):
    state = tmp_path/'episodes.json'
    assert execute(state, 'initial')['result']['pass'] is True
    changed = execute(state, 'changed')
    assert changed['result']['pass'] is False
    assert changed['result']['reached'] is False
    assert changed['result']['interactions']['act_calls'] == changed['actual_calls']
    assert contract.transition('VERIFIED', 'ENVIRONMENT_CHANGED') == 'UNKNOWN'


def test_unwritable_store_does_not_claim_a_persisted_lesson(tmp_path):
    # A real file occupying the parent path fails on all users, including root.
    blocking = tmp_path/'not-a-directory'
    blocking.write_text('occupied')
    run = execute(blocking/'episodes.json', 'initial')
    assert run['result']['pass'] is True
    assert run['result']['episode_persisted'] is False
    assert blocking.read_text() == 'occupied'
