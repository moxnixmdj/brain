"""Fresh checks for the live taint adapter's contextual-sanitizer false negative."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import time
import unittest
from unittest.mock import patch

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1

ROOT = pathlib.Path(__file__).resolve().parents[2]
CID = 'python.source.taint_flow.v1'


class ContextualTaintGuardTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='taint_context_', dir=work)
        self.addCleanup(temp.cleanup)
        self.base = pathlib.Path(temp.name)
        self.src = self.base / 'handler.py'
        self.out = self.base / 'report.json'
        self.entry = dict(live_integrated_brain_v1.load_verified_registry()[CID])
        self.args = {'capability_id': CID, 'source_root': self.src.relative_to(ROOT).as_posix(),
                     'output_path': self.out.relative_to(ROOT).as_posix(),
                     'source_function': 'parse_request', 'sink': 'exec'}
        self.action = {'type': 'invoke_capability', 'args': self.args,
                       'expect': {'field': 'output_verified', 'type': 'field_equals', 'value': True}}

    def _source(self, expression):
        self.src.write_text('import html, json, shlex\n'
                            'def parse_request(raw):\n    return json.loads(raw)\n'
                            'def handle(raw):\n    ' + expression + '\n')

    def _invoke(self):
        return door.run_adapter_locally(self.entry, self.action)

    def test_html_escape_does_not_protect_exec_and_no_is_not_published(self):
        self._source('exec(html.escape(parse_request(raw)))')
        spec = importlib.util.spec_from_file_location('taint_context_fixture', self.src)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            module.handle(json.dumps('print(123)'))
        self.assertEqual(output.getvalue().strip(), '123')
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            self._invoke()
        self.assertIn('CONTEXTUAL_SANITIZER_MAY_HIDE_TAINT', str(exc.exception))
        self.assertFalse(self.out.exists())

    def test_separate_assignment_does_not_bypass_guard(self):
        self._source('value = html.escape(parse_request(raw))\n    exec(value)')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertFalse(self.out.exists())

    def test_shell_quote_cannot_be_assumed_safe_for_python_exec(self):
        self._source('exec(shlex.quote(parse_request(raw)))')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertFalse(self.out.exists())

    def test_direct_positive_flow_remains_available(self):
        self._source('exec(parse_request(raw))')
        result = self._invoke()
        self.assertEqual(result['answer'], 'yes')
        self.assertEqual(result['adapter'], 'python_source_taint_flow')
        self.assertTrue(result['trace'])
        self.assertEqual(json.loads(self.out.read_text())['answer'], 'yes')
        self.assertEqual(result['output_sha256'], hashlib.sha256(self.out.read_bytes()).hexdigest())

    def test_numeric_coercion_control_remains_available(self):
        self._source('exec(str(int(parse_request(raw))))')
        result = self._invoke()
        self.assertEqual(result['answer'], 'no')
        self.assertTrue(self.out.is_file())

    def test_positive_finding_is_not_blocked_by_unrelated_escaping(self):
        self._source('exec(parse_request(raw))')
        with self.src.open('a') as f:
            f.write('def unrelated(value):\n    return html.escape(value)\n')
        result = self._invoke()
        self.assertEqual(result['answer'], 'yes')
        self.assertTrue(self.out.is_file())

    def test_escaping_without_a_sink_does_not_block_negative(self):
        self._source('return html.escape(parse_request(raw))')
        result = self._invoke()
        self.assertEqual(result['answer'], 'no')
        self.assertTrue(self.out.is_file())

    def test_implicit_sink_vocabulary_still_detects_context_hazard(self):
        self._source('exec(html.escape(parse_request(raw)))')
        args = dict(self.args)
        args.pop('sink')
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            door.run_adapter_locally(self.entry, dict(self.action, args=args))
        self.assertIn('CONTEXTUAL_SANITIZER_MAY_HIDE_TAINT', str(exc.exception))
        self.assertFalse(self.out.exists())

    def test_cross_file_sanitizer_and_sink_are_checked(self):
        self.src.write_text('import json, html\n'
                            'def parse_request(raw): return json.loads(raw)\n'
                            'def clean(raw): return html.escape(parse_request(raw))\n')
        (self.base / 'consumer.py').write_text('from handler import clean\n'
                                               'def handle(raw): exec(clean(raw))\n')
        args = dict(self.args, source_root=self.base.relative_to(ROOT).as_posix())
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            door.run_adapter_locally(self.entry, dict(self.action, args=args))
        self.assertIn('CONTEXTUAL_SANITIZER_MAY_HIDE_TAINT', str(exc.exception))
        self.assertFalse(self.out.exists())

    def test_unparseable_subject_cannot_produce_a_negative_verdict(self):
        self._source('return parse_request(raw)')
        (self.base / 'broken.py').write_text('def broken(:\n')
        args = dict(self.args, source_root=self.base.relative_to(ROOT).as_posix())
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            door.run_adapter_locally(self.entry, dict(self.action, args=args))
        self.assertIn('TAINT_SUBJECT_UNPARSEABLE', str(exc.exception))
        self.assertFalse(self.out.exists())

    def test_existing_report_is_not_overwritten_on_uncertain_result(self):
        self._source('exec(html.escape(parse_request(raw)))')
        self.out.write_text('previous report\n')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertEqual(self.out.read_text(), 'previous report\n')

    def test_report_hardlink_must_not_overwrite_source(self):
        self._source('exec(parse_request(raw))')
        before = self.src.read_bytes()
        os.link(self.src, self.out)
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertEqual(self.src.read_bytes(), before)

    def test_live_controller_does_not_repeat_the_refused_action(self):
        self._source('exec(html.escape(parse_request(raw)))')
        entry = dict(self.entry, action_template=self.action)
        compiled = {'selected_capability': CID, 'inputs': {}, 'target_effects': ['software.task.completed']}
        retried = []
        def controller(*args):
            retried.append(True)
            return None, 'CONTROL_PLAN_INVALID'
        with patch.object(door.live_integrated_brain_v1, 'drive_controller', controller):
            result = door._execute('TAINT_CONTEXT_GUARD', 'Check source for untrusted exec.',
                                   compiled, {CID: entry}, time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertIn('CONTEXTUAL_SANITIZER_MAY_HIDE_TAINT', result['reason'])
        self.assertEqual(retried, [])
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
