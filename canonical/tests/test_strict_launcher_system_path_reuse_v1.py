"""Run actual existing strict namespace backend with restricted caller PATH."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import pytest
from canonical.tests.test_existing_kernel_confinement_reuse_v1 import HOST_PYTHON, ROOT

BOOTSTRAP = '''import json,sys
from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined
result=run_confined({'argv':['/usr/bin/python3','-I','/input/probe.py'],
                     'input_dir':sys.argv[1],'limits':{'wallclock_s':10}})
print(json.dumps({'status':result['status'],'returncode':result['returncode'],
                  'payload':result['broker_payload'].decode()}))
'''


@pytest.mark.parametrize('path', ['/usr/bin:/bin', '', '/nonexistent-caller-tools'])
def test_existing_strict_backend_finds_real_system_primitives_without_caller_path(path):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        (root/'probe.py').write_text('import os,json\nfrom pathlib import Path\n'
                                    'Path("/work/result").write_text("scratch works")\n'
                                    'os.write(int(os.environ["PROJECT_BRAIN_BROKER_FD"]),'
                                    'json.dumps({"scratch":Path("/work/result").read_text(),'
                                    '"sentinel_inherited":"BRAIN_SYNTHETIC_SECRET_PROBE" in os.environ}).encode())\n')
        env=dict(os.environ)
        env['PATH']=path
        env['BRAIN_SYNTHETIC_SECRET_PROBE']='not-a-real-credential'
        process=subprocess.run([HOST_PYTHON,'-c',BOOTSTRAP,str(root)],cwd=ROOT,
                               env=env,capture_output=True,text=True,timeout=20)
        assert process.returncode==0,process.stderr
        result=json.loads(process.stdout)
        assert result['status']=='CHILD_EXITED',result
        assert result['returncode']==0,result
        assert json.loads(result['payload'])=={'scratch':'scratch works','sentinel_inherited':False}
        assert not (root/'result').exists()
