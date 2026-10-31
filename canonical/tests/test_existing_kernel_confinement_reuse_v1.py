"""Real namespace/chroot probes of existing confine_v1; no simulated sandbox.

Use the resolved interpreter under /usr: a workspace venv path is deliberately
not mounted inside this backend. These tests do not audit sandbox escape resistance.
"""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST_PYTHON = str(Path(sys.executable).resolve())
BOOTSTRAP = ('import json,sys\nfrom canonical.runtime import confine_v1 as c\n'
             'print(json.dumps(c.run(sys.argv[1],sys.argv[2],timeout=10,network=False)))\n')


class ExistingKernelConfinementReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run([HOST_PYTHON,'-c',
                                'from canonical.runtime import confine_v1 as c; print(c.available())'],
                               cwd=ROOT,capture_output=True,text=True,timeout=15)
        if probe.returncode != 0:
            raise RuntimeError(probe.stderr)
        if probe.stdout.strip() != 'True':
            raise unittest.SkipTest('Existing user namespace/chroot backend unavailable on this host')

    def confined(self, program, project):
        process = subprocess.run([HOST_PYTHON,'-c',BOOTSTRAP,program,str(project)],cwd=ROOT,
                                 capture_output=True,text=True,timeout=20)
        self.assertEqual(process.returncode,0,process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result['verdict'],'OK',result)
        self.assertTrue(result['confined'])
        self.assertFalse(result['network'])
        return json.loads(result['output'])

    def test_project_write_persists_but_outside_sentinel_cannot_be_read_or_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base/'project'
            project.mkdir()
            sentinel = base/'outside-secret.txt'
            sentinel.write_text('private caller bytes')
            program = '''import json
from pathlib import Path
outside = Path(%r)
failures=[]
for operation in (lambda: outside.read_text(), lambda: outside.write_text("changed")):
    try:
        operation()
    except OSError:
        failures.append(True)
Path("result.txt").write_text("persistent project output")
print(json.dumps({"blocked":len(failures),"cwd":str(Path.cwd())}))
''' % str(sentinel)
            result = self.confined(program,project)
            self.assertEqual(result,{'blocked':2,'cwd':'/project'})
            self.assertEqual((project/'result.txt').read_text(),'persistent project output')
            self.assertEqual(sentinel.read_text(),'private caller bytes')

    def test_root_and_host_user_paths_not_writable_or_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            program = '''import json
from pathlib import Path
paths=["/brain_probe_write", "/tmp/brain_probe_write", "/usr/brain_probe_write"]
blocked=[]
for name in paths:
    try:
        Path(name).write_text("probe")
    except OSError:
        blocked.append(name)
print(json.dumps({"blocked":blocked,"host_home_visible":Path("/home").exists(),"host_proc_visible":Path("/proc").exists()}))
'''
            result = self.confined(program,Path(directory))
            self.assertEqual(len(result['blocked']),3)
            self.assertFalse(result['host_home_visible'])
            self.assertFalse(result['host_proc_visible'])

    def test_host_loopback_listener_unreachable_with_default_network_namespace(self):
        with socket.socket() as server, tempfile.TemporaryDirectory() as directory:
            server.bind(('127.0.0.1',0))
            server.listen(1)
            port = server.getsockname()[1]
            program = '''import json,socket
try:
    socket.create_connection(("127.0.0.1",%d),timeout=1).close()
    blocked=False
except OSError:
    blocked=True
print(json.dumps({"blocked":blocked}))
''' % port
            self.assertTrue(self.confined(program,Path(directory))['blocked'])

    def test_kernel_resource_hard_limits_match_existing_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            program = '''import json,resource
names=["RLIMIT_CPU","RLIMIT_AS","RLIMIT_FSIZE","RLIMIT_NPROC","RLIMIT_NOFILE"]
print(json.dumps({name:list(resource.getrlimit(getattr(resource,name))) for name in names}))
'''
            limits = self.confined(program,Path(directory))
            for name,expected in {'RLIMIT_CPU':60,'RLIMIT_AS':2<<30,'RLIMIT_FSIZE':1<<30,
                                  'RLIMIT_NPROC':512,'RLIMIT_NOFILE':1024}.items():
                with self.subTest(resource=name):
                    self.assertEqual(limits[name],[expected,expected])

    def test_execution_diagnostic_discovers_existing_syscall_backend(self):
        script = ('import json\nfrom canonical.runtime import execute_v1 as e, confine_v1 as c\n'
                  'print(json.dumps({"diagnostic":e.confinement_available(),"backend":c.available()}))\n')
        process = subprocess.run([HOST_PYTHON,'-c',script],cwd=ROOT,
                                 capture_output=True,text=True,timeout=20)
        self.assertEqual(process.returncode,0,process.stderr)
        result = json.loads(process.stdout)
        self.assertTrue(result['backend'])
        self.assertTrue(result['diagnostic']['confinement'],result)
        self.assertTrue(result['diagnostic']['namespace_chroot'])
