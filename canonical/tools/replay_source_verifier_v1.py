"""Grade frozen source-room captures using an unchanged upstream V2 verifier.

NOT the release container image. Both negative and positive controls must run.
Input hidden assets are evaluator-only. Never import from a candidate repo.
"""
from __future__ import annotations

import argparse
import ast
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

PIN = '66f92766bba642462d4bbe5479e83f91f9211862'
NAMES = ('test.sh','config.json','test_patch.patch','parser.py','run_script.sh')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def names(raw):
    if isinstance(raw,str):
        raw = ast.literal_eval(raw)
    if not isinstance(raw,list) or not all(isinstance(x,str) for x in raw):
        raise ValueError('invalid case list')
    return set(raw)


def calibrated_controls(required, nop, reference):
    """No reward without the named cases: both controls must actually run."""
    if not required['fail_to_pass'] or any(r.get('error') for r in (nop, reference)):
        return False
    if (nop['exit'], nop['reward_file'], reference['exit'], reference['reward_file']) != (1, 0, 0, 1):
        return False
    def count(row, group, outcome):
        return row['required'][group].get(outcome, 0)
    ftp = 'fail_to_pass'; ptp = 'pass_to_pass'
    return (count(nop, ftp, 'FAILED') > 0
            and count(nop, ftp, 'PASSED') + count(nop, ftp, 'FAILED') == len(required[ftp])
            and count(nop, ptp, 'PASSED') == len(required[ptp])
            and all(count(reference, group, 'PASSED') == len(cases) for group, cases in required.items()))


def replay(base, task, venv, captured, *, verifier_timeout=220):
    if not 1 <= verifier_timeout <= 3000:
        raise ValueError('verifier timeout outside upstream task limit')
    tests = task/'tests'; cfg = json.loads((tests/'config.json').read_bytes())
    required = {k:names(cfg[k]) for k in ('fail_to_pass','pass_to_pass')}
    # Some released tasks declare no pass-to-pass cases. Never manufacture one;
    # insist on a nonempty repair obligation and expose exactly what ran.
    if not required['fail_to_pass']:raise ValueError('expected at least one fail-to-pass case')
    commit = subprocess.check_output(['git','-C',base,'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',base,'status','--porcelain','-uall']):raise ValueError('dirty base')
    pred = json.loads(captured.read_bytes());arms=[]
    for run in pred['rows']:
        m = run['measurement']
        if m is None or run['launcher']['returncode'] or m.get('base') != commit or m['capture_exit']:
            raise ValueError('no valid measured capture')
        data = base64.b64decode(m.get('patch_base64',''),validate=True)
        if sha(data)!=m['patch_sha256'] or len(data)!=m['patch_bytes']:raise ValueError('patch digest or size mismatch')
        arms.append((run['producer_revision'],data))
    arms += [('nop',b''),('reference',(task/'solution/gold_patch.diff').read_bytes())]
    rows=[]
    for arm,patch in arms:
        with tempfile.TemporaryDirectory(prefix='source_regrade_') as td:
            root = Path(td)
            shutil.copytree(base,root/'app',symlinks=True)
            row={'arm':arm,'patch_sha256':sha(patch),'bytes':len(patch),'exit':None,'reward_file':None,'official_image_reward':None}
            rows.append(row)
            if patch:
                apply=subprocess.run(['git','apply','--whitespace=nowarn','-'],input=patch,cwd=root/'app',capture_output=True)
                if apply.returncode:
                    row['error']='PATCH_APPLY_FAILED';continue
            start=time.monotonic()
            script=Path(__file__).with_name('source_verifier_root_v1.sh').resolve()
            with (root/'verifier.log').open('wb') as log:
                proc=subprocess.Popen(['unshare','-Urmpnf','--kill-child','bash',script,root,tests.resolve(),venv.resolve()],
                       env={'PATH':'/usr/sbin:/usr/bin:/bin','HOME':'/tmp','LC_ALL':'C.UTF-8'},stdin=subprocess.DEVNULL,
                       start_new_session=True,stdout=log,stderr=subprocess.STDOUT)
                try:row['exit']=proc.wait(timeout=verifier_timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait();row['error']='TIMEOUT'
            row['seconds']=round(time.monotonic()-start,3)
            logdir=root/'logs/verifier';out=logdir/'output.json';reward=logdir/'reward.txt'
            row['verifier_log_sha256']=sha((root/'verifier.log').read_bytes())
            if reward.is_file() and reward.read_text().strip() in ('0','1'):row['reward_file']=int(reward.read_text())
            if not out.is_file():
                row['error']=row.get('error','NO_PARSED_TESTS');row['detail']=(root/'verifier.log').read_text(errors='replace')[-300:];continue
            parsed=json.loads(out.read_text())['tests']
            states={r['name']:r['status'] for r in parsed}
            row['parsed']=dict(Counter(states.values()))
            row['required']={k:dict(Counter(states.get(n,'MISSING') for n in subset)) for k,subset in required.items()}
            if not parsed or (not row['parsed'].get('PASSED') and not row['parsed'].get('FAILED')):
                row['error']='NO_COMPLETED_CASES'
                aux=logdir/'run-script-stderr.txt'
                if aux.is_file():row['detail']=aux.read_text(errors='replace')[-400:]
    ok = calibrated_controls(required, *rows[-2:])
    return {'kind':'source-native replay; upstream verifier; NOT locked image or full HARD-51','task':task.name,
            'suite_commit':PIN,'base':commit,'prediction_sha256':sha(captured.read_bytes()),
            'verifier_files_sha256':{f:sha((tests/f).read_bytes()) for f in NAMES},
            'verifier_timeout_s':verifier_timeout,'calibrated_reference_nop':ok,'rows':rows}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('base','task','venv','captured'):p.add_argument(arg,type=Path)
    p.add_argument('--verifier-timeout',type=int,default=220)
    a=p.parse_args();print(json.dumps(replay(a.base,a.task,a.venv,a.captured,verifier_timeout=a.verifier_timeout),indent=2))
