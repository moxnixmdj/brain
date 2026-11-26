"""Local source-room Terminal-Bench replay with the released rewardkit verifier.

Grade separate, frozen workspace changes. Only the reference arm runs the
released solution in a room without the tests. The candidate never sees either.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def run(root, assets, env, phase):
    cmd=['unshare','-Urmpnf','--kill-child','bash',Path(__file__).with_name('source_verifier_root_v1.sh').resolve(),
         root,assets.resolve(),env.resolve(),phase]
    start=time.monotonic()
    with (root/(phase+'.log')).open('wb') as f:
        p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,
                           env={'PATH':'/usr/sbin:/usr/bin:/bin','HOME':'/tmp','LC_ALL':'C.UTF-8'})
        try:code=p.wait(timeout=200)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait();code=None
    out=(root/(phase+'.log')).read_bytes()
    return {'exit':code,'seconds':round(time.monotonic()-start,3),'log_sha256':hashlib.sha256(out).hexdigest(),
            **({'diagnostic':out.decode(errors='replace')[-350:]} if code!=0 else {})}


def grade(base,task,env,capture):
    raw=capture.read_bytes();frozen=json.loads(raw); data=frozen['rows'][0]; m=data['measurement']
    if m['capture_exit']!=0 or data['launcher']['returncode']!=0:raise ValueError('unmeasured capture')
    if m['base']!=subprocess.check_output(['git','-C',base,'rev-parse','HEAD'],text=True).strip():raise ValueError('base mismatch')
    if subprocess.check_output(['git','-C',base,'status','--porcelain','-uall']):raise ValueError('dirty base')
    patch=base64.b64decode(m.get('patch_base64',''),validate=True)
    if len(patch)!=m['patch_bytes'] or hashlib.sha256(patch).hexdigest()!=m['patch_sha256']:raise ValueError('bad capture')
    rows=[]
    for arm in (data['producer_revision'],'nop','reference'):
        with tempfile.TemporaryDirectory(prefix='tb_source_') as tmp:
            root=Path(tmp);app=root/'app';shutil.copytree(base,app,symlinks=True)
            row={'arm':arm,'grade':None};rows.append(row)
            if arm==data['producer_revision'] and patch:
                r=subprocess.run(['git','apply','-'],cwd=app,input=patch,capture_output=True)
                if r.returncode:row['error']='PATCH_APPLY_FAILED';continue
            if arm=='reference':
                with tempfile.TemporaryDirectory(prefix='tb_oracle_') as wd:
                    oracle=Path(wd);shutil.copytree(base,oracle/'app',symlinks=True)
                    row['reference_run']=run(oracle,task/'solution',env,'solution')
                    if row['reference_run']['exit']!=0:row['error']='REFERENCE_EXECUTION_FAILED';continue
                    shutil.rmtree(app);shutil.copytree(oracle/'app',app,symlinks=True)
            row['verifier_run']=run(root,task/'tests',env,'tests')
            logs=root/'logs/verifier';reward=logs/'reward.json'
            if not reward.is_file():row['error']='NO_REWARD';continue
            row['reward_file']=json.loads(reward.read_text())
            ctrf=logs/'ctrf.json'
            if ctrf.is_file():row['ctrf_summary']=json.loads(ctrf.read_text()).get('results',{}).get('summary')
            if row['verifier_run']['exit']==0:row['grade']=row['reward_file'].get('reward')
    return {'kind':'unaltered TB verifier in local Python source room; not official Docker','task':task.name,
            'suite_commit':'4070d6cef56a7d20cb5dc98d5e10ada88a6b9440','capture_sha256':hashlib.sha256(raw).hexdigest(),
            'python':subprocess.check_output([env/'bin/python3','-V'],text=True).strip(),
            'verifier_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((task/'tests').iterdir()) if p.is_file()},
            'calibrated_reference_nop':rows[-2]['grade']==0 and rows[-1]['grade']==1,'rows':rows}


if __name__=='__main__':print(json.dumps(grade(*map(Path,sys.argv[1:])),indent=2))
