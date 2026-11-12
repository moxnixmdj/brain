"""A required mount failure must stop before entering the candidate program.

These are unit simulations of the launcher, not hostile-code isolation tests or
carrier qualification. The mocked mount calls do not touch the host filesystem.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from canonical.runtime import confine_v1 as confine


class RequiredMountFailureTests(TestCase):
    def test_failed_required_mount_never_enters_project_or_program(self):
        base = '/candidate/root'
        project = '/candidate/project'
        script = '/candidate/script.py'
        required = (
            ('-t', 'tmpfs', 'none', base),
            ('--bind', '/usr', base + '/usr'),
            ('-o', 'remount,ro,bind', base + '/usr'),
            ('--bind', project, base + '/project'),
            ('-o', 'remount,ro,bind', base),
            ('-t', 'tmpfs', 'none', base + '/work'),
        )
        for failed in required:
            calls = []
            def launch(argv, **kwargs):
                calls.append(tuple(argv))
                if tuple(argv[1:]) == failed:
                    return SimpleNamespace(returncode=1, stderr='injected mount failure', stdout='')
                return SimpleNamespace(returncode=0, stderr='', stdout='')
            helper = confine._HELPER.replace('__MOUNTS__', repr(['/usr']))
            with self.subTest(failed=failed), \
                 mock.patch.object(sys, 'argv', ['helper', base, project, script, '0']), \
                 mock.patch.object(subprocess, 'run', side_effect=launch), \
                 mock.patch.object(confine.os, 'makedirs'), \
                 mock.patch.object(confine.os.path, 'isdir', return_value=True), \
                 mock.patch.object(confine.os, 'chroot') as chroot, \
                 mock.patch.object(confine.os, 'chdir'), \
                 mock.patch('shutil.copyfile'), \
                 mock.patch.object(sys, 'stderr'):
                with self.assertRaises(SystemExit) as error:
                    exec(compile(helper, '<confine-helper>', 'exec'), {})
                self.assertEqual(error.exception.code, 90)
                chroot.assert_not_called()
                self.assertNotIn((sys.executable, '/work/program.py'), calls)

    def test_failed_resource_limit_prevents_program_exec(self):
        import resource
        helper = confine._HELPER.replace('__MOUNTS__', repr(['/usr']))
        ran = []
        def launch(argv, **kwargs):
            if argv[0] != 'mount':
                kwargs['preexec_fn']()
                ran.append(argv)
            return SimpleNamespace(returncode=0, stderr='', stdout='')
        with mock.patch.object(sys, 'argv', ['helper', '/candidate/root', '/candidate/project', '/candidate/script.py', '0']), \
             mock.patch.object(subprocess, 'run', side_effect=launch), \
             mock.patch.object(confine.os, 'makedirs'), \
             mock.patch.object(confine.os.path, 'isdir', return_value=True), \
             mock.patch.object(confine.os, 'chroot'), mock.patch.object(confine.os, 'chdir'), \
             mock.patch('shutil.copyfile'), \
             mock.patch.object(resource, 'setrlimit', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                exec(compile(helper, '<confine-helper>', 'exec'), {})
        self.assertEqual(ran, [])

    def test_solve_does_not_turn_a_setup_refusal_into_confined_true(self):
        from canonical.runtime import solve_v1
        candidate = SimpleNamespace(available=lambda: True,
                                    run=lambda *a, **kw: {'verdict': 'FAILED', 'exit_status': 90,
                                                          'output': 'mount failed', 'confined': None})
        with mock.patch.dict(sys.modules, {'confine_v1': candidate}), \
             mock.patch.object(subprocess, 'run') as unconfined:
            result = solve_v1.act('/candidate', 'print(1)')
        unconfined.assert_not_called()
        self.assertFalse(result['confined'])
        self.assertFalse(result['carrier_qualified'])
        self.assertEqual(result['exit'], 90)

    def test_helper_failure_and_timeout_do_not_claim_confinement(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.object(confine, 'available', return_value=True):
            with mock.patch.object(subprocess, 'run', return_value=SimpleNamespace(returncode=90, stdout='', stderr='mount failed')):
                result = confine.run('print(1)', root)
            self.assertEqual(result['verdict'], 'FAILED')
            self.assertIsNot(result.get('confined'), True)
            with mock.patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired('unshare', 1)):
                result = confine.run('print(1)', root, timeout=1)
            self.assertEqual(result['verdict'], 'INDETERMINATE')
            self.assertIsNot(result.get('confined'), True)


class ChrootInterpreterTests(TestCase):
    """The helper must be launched with an interpreter the chroot will contain."""

    def test_a_venv_interpreter_is_not_the_one_spawned_into_the_chroot(self):
        # sys.executable outside _MOUNTS (a venv) cannot exist inside the
        # helper's chroot; the launch must fall back to a mounted system
        # python, or every confined run dies before the program starts.
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(confine, 'available', return_value=True):
            captured = {}

            def launch(argv, **kwargs):
                captured['argv'] = list(argv)
                return SimpleNamespace(returncode=0, stdout='ok', stderr='')

            with mock.patch.object(sys, 'executable', '/tmp/elsewhere/venv/bin/python3'), \
                    mock.patch.object(subprocess, 'run', side_effect=launch):
                result = confine.run('print(1)', root)
            self.assertEqual(result['verdict'], 'OK')
            spawned = [tok for tok in captured['argv']
                       if tok.endswith('python') or tok.endswith('python3')]
            self.assertEqual(len(spawned), 1, captured['argv'])
            self.assertNotIn('/tmp/elsewhere/venv/bin/python3', spawned)
            self.assertTrue(
                spawned[0].startswith('/usr/') or spawned[0].startswith('/bin/'),
                spawned,
            )
