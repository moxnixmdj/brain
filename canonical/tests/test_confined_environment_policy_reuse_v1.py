"""Real confined workload must not inherit synthetic caller secrets/startup paths."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import pytest
from canonical.tests.test_existing_kernel_confinement_reuse_v1 import HOST_PYTHON, ROOT, BOOTSTRAP


@pytest.fixture(scope='module', autouse=True)
def require_existing_kernel_backend():
    probe = subprocess.run([HOST_PYTHON,'-c','from canonical.runtime import confine_v1 as c; print(c.available())'],
                           cwd=ROOT,capture_output=True,text=True,timeout=15,check=True)
    if probe.stdout.strip() != 'True':
        pytest.skip('Existing namespace/chroot backend unavailable on this host')


@pytest.mark.parametrize('name', ['BRAIN_SYNTHETIC_SECRET_PROBE','CI_JOB_TOKEN','PYTHONPATH','LD_LIBRARY_PATH'])
def test_caller_environment_does_not_reach_confined_program(name):
    with tempfile.TemporaryDirectory() as directory:
        env = dict(os.environ)
        env[name] = 'synthetic-not-a-real-credential-or-path'
        program = ('import os,json\nfrom pathlib import Path\n'
                   'Path("output.txt").write_text("project write works")\n'
                   f'print(json.dumps({{"inherited":{name!r} in os.environ}}))\n')
        process = subprocess.run([HOST_PYTHON,'-c',BOOTSTRAP,program,directory],cwd=ROOT,
                                 capture_output=True,text=True,env=env,timeout=20,check=True)
        result = json.loads(process.stdout)
        assert result['verdict'] == 'OK', result
        assert result['confined'] is True
        assert json.loads(result['output'])['inherited'] is False
        assert (Path(directory)/'output.txt').read_text() == 'project write works'
        assert env[name] == 'synthetic-not-a-real-credential-or-path'


def test_confined_home_is_project_not_caller_home():
    with tempfile.TemporaryDirectory() as directory:
        env = dict(os.environ)
        env['HOME'] = 'synthetic-caller-home'
        program = 'import os,json; print(json.dumps({"home":os.environ.get("HOME"),"path":os.environ.get("PATH")}))'
        process = subprocess.run([HOST_PYTHON,'-c',BOOTSTRAP,program,directory],cwd=ROOT,
                                 capture_output=True,text=True,env=env,timeout=20,check=True)
        result = json.loads(process.stdout)
        assert result['verdict'] == 'OK',result
        payload = json.loads(result['output'])
        assert payload['home'] == '/project'
        assert payload['path'] == '/usr/bin:/bin'


@pytest.mark.parametrize('declarations', [{}, {'LANG':'C','TZ':'UTC','PYTHONHASHSEED':'0'}])
def test_shared_minimal_environment_uses_only_explicit_allowed_values(declarations):
    from canonical.runtime.zero_ambient_namespace_launcher_v1 import isolated_environment
    original = dict(declarations)
    result = isolated_environment(home='/project',env=declarations)
    assert result == {'PATH':'/usr/bin:/bin','HOME':'/project','PYTHONDONTWRITEBYTECODE':'1',**declarations}
    assert declarations == original


@pytest.mark.parametrize('declarations', [{'API_KEY':'synthetic'}, {'PATH':'/untrusted'},
                                         {'TZ':'bad\x00value'}, {'LANG':'x'*513}])
def test_shared_environment_validation_keeps_existing_fail_closed_rules(declarations):
    from canonical.runtime.zero_ambient_namespace_launcher_v1 import isolated_environment, NamespaceConfinementError
    with pytest.raises(NamespaceConfinementError):
        isolated_environment(env=declarations)
