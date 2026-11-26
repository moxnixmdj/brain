"""Engineering positive control: can the actual source-only Harbor worker emit a composed edit?

Deliberately constructed, not a benchmark task. No memory or supplied gold. Compare
both frozen revisions on identical public tests. The fresh checker is not mounted.
Example: python -m canonical.tools.probe_staged_composition_v1 NEW_DIR NATIVE_VENV
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from canonical.tools.harbor_source_route_control_v1 import paired

PRODUCT='''def octets(value: str) -> bytes:
    return value.encode()


def measure(data: bytes) -> int:
    return sum(data)


def label(value: str) -> int:
    return len(value)
'''
TEST="from local import label\n\ndef test_nonempty(): assert label('ab') == 195\ndef test_empty(): assert label('') == 0\n"
TASK='Repair `label` so it returns the sum of the UTF-8 byte values of its input. Preserve behavior on the empty input.\n'
REVISIONS=('bee38f7000851a9b16a055d7ef7e2ec01d7c7217','d17cb7c1cad4f8baba35395306a20287723322d0')
CHECK="""import json,sys
from local import label
xs=['','A','ab','cd','ß','🌍','a\\0b','é'*257]; bad=[]
for i,x in enumerate(xs):
 v=label(x)
 if type(v) is not int or v!=sum(x.encode('utf-8')):bad.append(i)
print(json.dumps({'inputs':len(xs),'failures':bad}));sys.exit(bool(bad))"""


def grade(capture,base):
    if capture['input_instruction_sha256']!=hashlib.sha256(TASK.encode()).hexdigest():raise ValueError('unexpected instruction')
    rows=[]
    for run in capture['rows']:
        m=run['measurement']; row={'revision':run['producer_revision']}; rows.append(row)
        if not m or run['launcher']['returncode']!=0 or m['capture_exit']!=0:
            row['error']='UNMEASURED_CAPTURE';continue
        patch=base64.b64decode(m.get('patch_base64',''),validate=True)
        if hashlib.sha256(patch).hexdigest()!=m['patch_sha256'] or len(patch)!=m['patch_bytes']:raise ValueError('capture mismatch')
        with tempfile.TemporaryDirectory() as td:
            app=Path(td)/'repo';shutil.copytree(base,app)
            if subprocess.check_output(['git','rev-parse','HEAD'],cwd=app,text=True).strip()!=m['base']:raise ValueError('wrong base')
            if patch:subprocess.run(['git','apply','-'],cwd=app,input=patch,check=True)
            r=subprocess.run(['unshare','-c','-n',sys.executable,'-Bc',CHECK],env={'HOME':td,'PATH':'/usr/bin:/bin','LC_ALL':'C.UTF-8'},
                             cwd=app,capture_output=True,timeout=5)
            row.update(exit=r.returncode,check=json.loads(r.stdout),patch_bytes=len(patch),patch_sha256=m['patch_sha256'])
    return rows


def main(dest,venv):
    dest=dest.resolve()
    if dest.is_relative_to(Path(__file__).resolve().parents[2]):raise ValueError('external scratch required')
    dest.mkdir();seed=dest/'seed';base=dest/'base';goal=dest/'task.md'
    subprocess.run(['git','init','-q','--template=',seed],check=True)
    (seed/'local.py').write_text(PRODUCT);(seed/'test_usage.py').write_text(TEST);goal.write_text(TASK)
    subprocess.run(['git','add','.'],cwd=seed,check=True)
    subprocess.run(['git','-c','user.name=Control','-c','user.email=control@invalid','-c','commit.gpgsign=false','commit','-qm','worksheet'],
                   cwd=seed,env={**os.environ, 'GIT_AUTHOR_DATE':'2026-11-26T00:00:00Z','GIT_COMMITTER_DATE':'2026-11-26T00:00:00Z'},check=True)
    subprocess.run(['git','clone','--depth=1','-q',seed.as_uri(),base],check=True)
    capture=paired(base,goal,venv.resolve(),list(REVISIONS));(dest/'capture.json').write_text(json.dumps(capture,indent=2)+'\n')
    print(json.dumps(grade(capture,base),indent=2))


if __name__=='__main__':main(*map(Path,sys.argv[1:]))
