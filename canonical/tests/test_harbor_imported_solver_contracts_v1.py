"""Local donor-engine contract checks; not Harbor isolation or benchmark evidence."""
from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime import causal_angelic_swe_engine_v1 as py_engine
from canonical.runtime import epistemic_doc_compiler_agent_v1 as cli_engine
from canonical.runtime import epistemic_world_model_planner_v1 as world_engine
from canonical.runtime import multilang_causal_swe_engine_v1 as js_engine
from canonical.runtime import oe_sygus_synthesizer_v1 as synth


class ImportedSolverContracts(unittest.TestCase):
    def test_three_language_expression_synthesis_and_world_import(self):
        for lang in ('python', 'js', 'c'):
            with self.subTest(lang=lang):
                predicates = synth.synthesize_separating_predicates(
                    [{'x': -3}, {'x': -1}], [{'x': 0}, {'x': 2}], lang=lang)
                self.assertEqual(predicates[0]['code'], '(x < 0)')
        self.assertEqual(world_engine.AUTHORITY, 'NONE')

    @unittest.skipUnless(shutil.which('base64') and shutil.which('sort'), 'base64 and sort required')
    def test_cli_multi_step_fixture_checked_by_exact_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'input.b64').write_bytes(base64.b64encode(b'b\na\nb\n'))
            result = cli_engine.solve_multi_step_with_instant_knowledge(
                'Use base64 to decode input.b64 and save to raw.txt, then use sort with unique on raw.txt and write to final.txt',
                workspace=root, timeout_s=6,
                verifier=lambda state: (state['output_text'] == 'a\nb\n', 'exact output'))
            self.assertEqual(result['status'], 'VERIFIED')
            self.assertEqual(result['steps_completed'], 2)
            self.assertEqual((root / 'final.txt').read_bytes(), b'a\nb\n')
            self.assertEqual(result['model_calls'], 0)
            self.assertEqual(result['parameters_stored'], 0)

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_js_engine_finds_candidate_on_local_fixture(self):
        source = "function fmt(v, enc) {\n  const out = v ? enc(v) : '';\n  return out;\n}\nmodule.exports = {fmt};\n"
        tests = ("const test = require('node:test');\nconst assert = require('node:assert/strict');\n"
                 "const {fmt} = require('./fmt.js');\n"
                 "test('empty', () => assert.equal(fmt('', s => '[' + s + ']'), '[]'));\n"
                 "test('nonempty', () => assert.equal(fmt('x', s => '[' + s + ']'), '[x]'));\n")
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as verify:
            root, external = Path(temp), Path(verify)
            for p in (root, external):
                (p / 'package.json').write_text('{"scripts":{"test":"node --test"}}\n')
                (p / 'fmt.js').write_text(source)
                (p / 'fmt.test.js').write_text(tests)
            self.assertNotEqual(subprocess.run(['node', '--test', 'fmt.test.js'], cwd=external,
                                               capture_output=True, timeout=20).returncode, 0)
            result = js_engine.solve_js_repository(root, timeout_s=10, max_candidates=30)
            self.assertEqual(result['status'], 'VERIFIED')
            self.assertTrue(result['winner']['diff'])
            self.assertEqual((root / 'fmt.js').read_text(), source)
            (external / 'fmt.js').write_text(result['winner']['patched_source'])
            self.assertEqual(subprocess.run(['node', '--test', 'fmt.test.js'], cwd=external,
                                            capture_output=True, timeout=20).returncode, 0)

    @unittest.skipUnless(importlib.util.find_spec('pytest'), 'pytest required by Python donor engine')
    def test_python_engine_finds_candidate_on_local_fixture(self):
        source = 'def add(a, b):\n    return a - b\n'
        tests = 'from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n    assert add(3, 4) == 7\n'
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as verify:
            root, external = Path(temp), Path(verify)
            for p in (root, external):
                (p / 'calc.py').write_text(source)
                (p / 'test_calc.py').write_text(tests)
            command = [sys.executable, '-m', 'pytest', '-q', 'test_calc.py']
            self.assertNotEqual(subprocess.run(command, cwd=external, capture_output=True, timeout=20).returncode, 0)
            result = py_engine.solve_repository(root, ['test_calc.py'], max_probes=3, max_candidates=20,
                                                timeout_s=10, learn_into_store=False)
            self.assertEqual(result['status'], 'VERIFIED')
            self.assertTrue(result['winner']['diff'])
            self.assertEqual((root / 'calc.py').read_text(), source)
            (external / 'calc.py').write_text(result['winner']['patched_source'])
            self.assertEqual(subprocess.run(command, cwd=external, capture_output=True, timeout=20).returncode, 0)

    def test_copied_worktrees_do_not_prove_symlink_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src, py_copy, js_copy = root / 'src', root / 'py_copy', root / 'js_copy'
            src.mkdir()
            outside = root / 'outside.txt'
            outside.write_text('outside')
            (src / 'link.txt').symlink_to(outside)
            (src / 'node_modules').mkdir()
            (src / 'node_modules' / 'module.txt').write_text('not read-only')
            py_engine.copy_worktree(src, py_copy)
            js_engine._copy_js_worktree(src, js_copy)
            self.assertTrue((py_copy / 'link.txt').is_symlink())
            self.assertTrue((js_copy / 'node_modules').is_symlink())
            self.assertEqual(os.path.realpath(js_copy / 'node_modules'), str(src / 'node_modules'))
            # A top-level source symlink is dereferenced by copy2.
            self.assertFalse((js_copy / 'link.txt').is_symlink())
            self.assertEqual((js_copy / 'link.txt').read_text(), 'outside')
            self.assertEqual(outside.read_text(), 'outside')


if __name__ == '__main__':
    unittest.main()
