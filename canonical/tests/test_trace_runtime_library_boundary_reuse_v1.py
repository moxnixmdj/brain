"""Real nested interpreters distinguish runtime libraries from project code."""
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
import venv

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as runner

REPO = Path(__file__).resolve().parents[2]


class RuntimeLibraryBoundaryControls:
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_runtime_boundary_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # No pip or network: this is an actual interpreter environment, not a
        # fabricated executable or a package-installation substitute.
        self.runtime = self.root / '.tools' / 'custom_python'
        venv.EnvBuilder(with_pip=False).create(self.runtime)
        self.python = self.runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        self.library = Path(subprocess.check_output(
            [str(self.python), '-c', "import sysconfig;print(sysconfig.get_path('purelib'))"],
            text=True).strip())
        self.library.mkdir(parents=True, exist_ok=True)
        self.source = self.root / 'src'
        self.source.mkdir()

    def run_tool(self, source, subject_root=None, max_events=10000):
        root = subject_root or self.root
        args = {'source_root': str(source.relative_to(root)),
                'test_paths': [str((source / 'test_m.py').relative_to(root))],
                'output_path': 'report.json', 'max_trace_events': max_events}
        code = ('import sys\n' + f'sys.path.insert(0,{str(REPO)!r})\n'
                'from canonical.runtime.bound_capabilities import '
                + self.adapter + ' as tool\n'
                + f'tool.run({args!r},{str(root)!r})\n')
        result = runner._run_tests(root, [str(self.python), '-c', code], 15)
        self.assertFalse(result['timed_out'], result)
        self.assertEqual(result['returncode'], 0, result['stderr'])
        report = json.loads((root / 'report.json').read_bytes())
        self.assertEqual(report['failing_test_count'], 1)
        self.assertIs(report['test_traces'][0]['pass'], False)
        return report['test_traces'][0]['events']

    def paths(self, events):
        if self.adapter == 'python_dynamic_fault_localizer_v1':
            return {event[0] for event in events}
        return {event['callee']['path'] for event in events}

    def test_actual_runtime_dependency_is_not_project_evidence(self):
        (self.library / 'dependency_fixture.py').write_text(
            'def helper(x):\n    return (lambda y: y+1)(x)\n')
        (self.source / 'm.py').write_text(
            'from dependency_fixture import helper\ndef f():\n    return helper(1)\n')
        (self.source / 'test_m.py').write_text('from m import f\nassert f()==3\n')
        paths = self.paths(self.run_tool(self.source))
        self.assertIn('src/m.py', paths)
        dependency = str((self.library / 'dependency_fixture.py').relative_to(self.root)).replace('\\', '/')
        self.assertNotIn(dependency, paths)

    def test_dependency_activity_does_not_exhaust_project_trace_budget(self):
        (self.library / 'dependency_fixture.py').write_text(
            'def helper(x):\n'
            '    for _ in range(500): x=(lambda y:y+1)(x)\n'
            '    return x\n')
        (self.source / 'm.py').write_text(
            'from dependency_fixture import helper\n'
            'def after(x):\n    return x\n'
            'def f():\n    return after(helper(0))\n')
        (self.source / 'test_m.py').write_text('from m import f\nassert f()==999\n')
        events = self.run_tool(self.source, max_events=100)
        if self.adapter == 'python_dynamic_fault_localizer_v1':
            functions = {event[2] for event in events}
        else:
            functions = {event['callee']['function'] for event in events}
        self.assertIn('after', functions)

    def test_project_build_and_env_directories_are_not_blanket_excluded(self):
        for folder in ('build', 'env'):
            package = self.source / folder
            package.mkdir()
            (package / '__init__.py').touch()
            (package / 'logic.py').write_text('def helper(x):\n    return x+1\n')
        (self.source / 'm.py').write_text(
            'from build.logic import helper as generated\n'
            'from env.logic import helper as configured\n'
            'def f():\n    return configured(generated(0))\n')
        (self.source / 'test_m.py').write_text('from m import f\nassert f()==3\n')
        paths = self.paths(self.run_tool(self.source))
        self.assertIn('src/build/logic.py', paths)
        self.assertIn('src/env/logic.py', paths)
        self.assertIn('src/m.py', paths)

    def test_explicit_library_subject_root_is_still_observable(self):
        (self.library / 'm.py').write_text('def f():\n    return 2\n')
        (self.library / 'test_m.py').write_text('from m import f\nassert f()==3\n')
        paths = self.paths(self.run_tool(self.library, subject_root=self.library))
        self.assertIn('m.py', paths)


class LocalizerRuntimeLibraryBoundaryTests(RuntimeLibraryBoundaryControls, unittest.TestCase):
    adapter = 'python_dynamic_fault_localizer_v1'


class ProvenanceRuntimeLibraryBoundaryTests(RuntimeLibraryBoundaryControls, unittest.TestCase):
    adapter = 'python_interprocedural_value_provenance_v1'


if __name__ == '__main__':
    unittest.main()
