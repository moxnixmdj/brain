"""Real namespace probes; unavailable hosts skip, never report confinement PASS."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import confine_v1 as confine


class ConfinementPrivilegeBoundaryTests(unittest.TestCase):
    def test_missing_privilege_drop_primitive_does_not_execute_workload(self):
        real = confine.shutil.which
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(confine.shutil, 'which', side_effect=lambda name: None if name == 'setpriv' else real(name)):
                result = confine.run("open('should_not_exist', 'w').write('bad')", directory, timeout=5)
            self.assertEqual(result['verdict'], 'INDETERMINATE')
            self.assertFalse((pathlib.Path(directory) / 'should_not_exist').exists())

    @unittest.skipUnless(confine.available(), 'host does not support user/mount namespaces')
    def test_failed_mount_setup_never_executes_workload(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = confine._HELPER.replace('m("--make-rprivate", "/")', 'm("--brain-invalid-mount-option")')
            self.assertNotEqual(helper, confine._HELPER)
            with patch.object(confine, '_HELPER', helper):
                result = confine.run("open('should_not_exist', 'w').write('bad')", directory, timeout=5)
            self.assertEqual(result['verdict'], 'FAILED', result)
            self.assertEqual(result['exit_status'], 90)
            self.assertFalse((pathlib.Path(directory) / 'should_not_exist').exists())

    @unittest.skipUnless(confine.available(), 'host does not support user/mount namespaces')
    def test_real_workload_has_no_privileges_and_can_still_write_project(self):
        program = '''
import ctypes, json, pathlib
libc = ctypes.CDLL(None, use_errno=True)
class Header(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint32), ('pid', ctypes.c_int)]
class Data(ctypes.Structure):
    _fields_ = [('effective', ctypes.c_uint32), ('permitted', ctypes.c_uint32), ('inheritable', ctypes.c_uint32)]
h = Header(0x20080522, 0)
d = (Data * 2)()
assert libc.capget(ctypes.byref(h), d) == 0
caps = [(v.effective, v.permitted, v.inheritable) for v in d]
bounding = [libc.prctl(23, cap, 0, 0, 0) for cap in range(41)]
# A private tmpfs mount inside this namespace is harmless, but a workload
# must not have the authority to perform it or undo the read-only mounts.
pathlib.Path('mountpoint').mkdir()
mount_result = libc.mount(b'none', b'/project/mountpoint', b'tmpfs', 0, None)
pathlib.Path('legitimate.txt').write_text('ok')
print(json.dumps(dict(caps=caps, bounding=bounding, no_new_privs=libc.prctl(39, 0, 0, 0, 0),
                     mount_result=mount_result, host_hidden=not pathlib.Path('/home/user/brain').exists())))
'''
        with tempfile.TemporaryDirectory() as directory:
            result = confine.run(program, directory, timeout=10)
            self.assertEqual(result['verdict'], 'OK', result)
            self.assertEqual((pathlib.Path(directory) / 'legitimate.txt').read_text(), 'ok')
            evidence = json.loads(result['output'])
        self.assertEqual(evidence['caps'], [[0, 0, 0], [0, 0, 0]])
        self.assertNotIn(1, evidence['bounding'])
        self.assertEqual(evidence['no_new_privs'], 1)
        self.assertEqual(evidence['mount_result'], -1)
        self.assertTrue(evidence['host_hidden'])


if __name__ == '__main__':
    unittest.main()
