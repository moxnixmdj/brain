#!/usr/bin/env python3
"""Producer-run synthetic transfer-driver comparison, not a whole-system control.

Fresh processes share only an explicitly copied episode store. The same fixed
baseline plan and environment are used for all arms. The parent independently
replays the reported plan against the simple lock rules. No generated command,
filesystem task, untrusted code or real computer capability is exercised.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

WORKER = r'''
import json, os, sys
from canonical.runtime import transfer_learning_v1 as tl
class Lock:
    def __init__(self): self.d = [0, 0, 0]
    def reset(self): self.d = [0, 0, 0]
    def state(self): return tuple(self.d)
    def act(self, action):
        i = int(str(action)[1]); self.d[i] = (self.d[i] + 1) % 10
    def snapshot(self): return list(self.d)
    def restore(self, value): self.d = list(value)
target = tuple(int(x) for x in sys.argv[2].split(','))
env = Lock()
r = tl.drive(env, ['+0', '+1', '+2'], is_goal=lambda s: s == target,
             budget=40, max_depth=24, heuristic=lambda s: sum(abs(a-b) for a,b in zip(s,target)),
             seed=11, experience_mode=sys.argv[1], fixed_plan=['+0'])
print(json.dumps({'pid': os.getpid(), 'target': target, 'result': r,
                  'worker_final_state': env.state()}))
'''


def replay(plan):
    if not isinstance(plan, list) or not plan:
        return None
    d = [0, 0, 0]
    for action in plan:
        if action not in ('+0', '+1', '+2'):
            return None
        i = int(action[1])
        d[i] = (d[i] + 1) % 10
    return d


def run():
    with tempfile.TemporaryDirectory(prefix='brain-transfer-control-') as tmp:
        root = Path(tmp)
        env_base = {k: v for k, v in os.environ.items() if not k.startswith('BRAIN_')}
        env_base['PYTHONDONTWRITEBYTECODE'] = '1'
        def worker(role, mode, target):
            state = root / role / 'episodes.json'
            state.parent.mkdir(parents=True, exist_ok=True)
            if role in ('off', 'warm'):
                shutil.copyfile(root / 'teach' / 'episodes.json', state)
            before = state.read_bytes() if state.exists() else None
            env = dict(env_base, BRAIN_TRANSFER_LEARNING_STATE=str(state),
                       BRAIN_TRANSFER_LEARNING_FINGERPRINTS=str(state) + '.fingerprints')
            proc = subprocess.run([sys.executable, '-c', WORKER, mode, target],
                                  env=env, text=True, capture_output=True, check=True, timeout=30)
            row = json.loads(proc.stdout)
            row['role'] = role
            row['host_replay'] = replay(row['result'].get('plan'))
            row['host_plan_reaches_target'] = row['host_replay'] == row['target']
            row['episode_store_unchanged'] = before == (state.read_bytes() if state.exists() else None)
            return row
        rows = [worker('teach', 'learn_and_recall', '7,2,9'),
                worker('off', 'off', '1,1,1'),
                worker('cold', 'learn_and_recall', '1,1,1'),
                worker('warm', 'learn_and_recall', '1,1,1')]
        return {'scope': 'synthetic three-dial lock; transfer drive only',
                'fixed_plan_in_all_arms': ['+0'],
                'off_scope': 'driver does not use retained episodes, fingerprint probes or model learning',
                'shared_fixed_source_and_goal_rules': True,
                'independent_personnel_verification': False,
                'rows': rows}


def main():
    print(json.dumps(run(), indent=2))


if __name__ == '__main__':
    main()
