"""Regression checks for project-relative inputs mistaken for report paths.

The live check observes the filesystem and test behavior, not the adapter's
self-reported verification flag. Temporary projects are disposable fixtures.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import swe_typed_plan_v1 as plan
from canonical.runtime import live_brain_route_admission_v1 as door
from advanced_swe_probe_20261030 import RACE, RACE_TEST


class ReportBindingTests(unittest.TestCase):
    def test_relative_input_is_relocated_but_explicit_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            app = root / 'project' / 'app'
            tests = root / 'project' / 'tests'
            app.mkdir(parents=True)
            tests.mkdir()
            (tests / 'test_worker.py').write_text('original\n')
            (app / 'typed_swe_report.json').write_text('keep me\n')
            args = {'source_root': 'project/app', 'output_path': 'tests/test_worker.py'}
            goal = 'The test tests/test_worker.py in project is failing. Fix project/app/worker.py.'
            self.assertEqual(plan._fresh_output_path(goal, root, args),
                             'project/app/typed_swe_report_1.json')
            self.assertEqual((app / 'typed_swe_report.json').read_text(), 'keep me\n')
            (app / 'typed_swe_report_1.json').symlink_to(app / 'missing-target')
            self.assertEqual(plan._fresh_output_path(goal, root, args),
                             'project/app/typed_swe_report_2.json')
            explicit = goal + ' Save the report to tests/test_worker.py.'
            self.assertIsNone(plan._fresh_output_path(explicit, root, args))

    def test_unsubstantiated_and_non_code_paths_are_not_relocated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root / 'project' / 'app').mkdir(parents=True)
            for name in ('tests/missing.py', 'tests/report.json', '../outside.py'):
                args = {'source_root': 'project/app', 'output_path': name}
                self.assertIsNone(plan._fresh_output_path('Fix project/app.', root, args))

    def test_live_repair_does_not_write_relative_input_in_brain_root(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='relative_binding_', dir=work) as temp:
            project = pathlib.Path(temp)
            (project / 'app').mkdir()
            (project / 'tests').mkdir()
            (project / 'app/__init__.py').write_text('')
            (project / 'tests/__init__.py').write_text('')
            (project / 'app/counter.py').write_text(RACE)
            test_name = 'test_' + project.name + '.py'
            project_test = project / 'tests' / test_name
            project_test.write_text(RACE_TEST)
            unintended = ROOT / 'tests' / test_name
            self.assertFalse(unintended.exists(), 'test requires a previously absent root path')
            relative_project = project.relative_to(ROOT).as_posix()
            goal = (f'The test tests/{test_name} in {relative_project} is flaky. '
                    f'Fix the race condition in {relative_project}/app/counter.py.')
            before_test = project_test.read_bytes()
            try:
                result = door.solve({'task_id': 'RELATIVE_REPORT_SAFETY', 'goal': goal})
                self.assertFalse(unintended.exists(), 'report escaped into Brain tests')
                self.assertEqual(project_test.read_bytes(), before_test)
                self.assertTrue(result.get('pass'), result)
                env = dict(os.environ, PYTHONPATH=str(project))
                check = subprocess.run(
                    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.'],
                    cwd=project, env=env, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            finally:
                # Only remove the unique file this test proved absent initially.
                unintended.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
