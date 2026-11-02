"""A report-shaped JSON file does not verify a root-cause diagnosis."""
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
from canonical.runtime.live_brain_route_admission_v1 import compile_contract


class DiagnosisAcceptanceIntegrityTests(unittest.TestCase):
    def test_fabricated_root_cause_report_is_not_accepted(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='diagnosis_verdict_', dir=tmp) as td:
            report = Path(td) / 'report.json'
            report.write_text(json.dumps({'operation': 'diagnose_test_suite',
                                           'root_causes': ['entirely fabricated'],
                                           'verified': True, 'gate': 'PASS'}), encoding='utf-8')
            rel = report.relative_to(root).as_posix()
            result = {'verified': True, 'gate': 'PASS', 'output_path': rel}
            ok, reason, evidence = acceptance.INSPECTORS['software.analysis.diagnose_and_architect.v1'](
                {'operation': 'find_root_cause', 'output_path': rel}, result, root)
            self.assertFalse(ok, evidence)
            self.assertEqual(reason, 'DIAGNOSIS_ROOT_CAUSE_NOT_INDEPENDENTLY_VERIFIED')

    def test_full_acceptance_refuses_fabricated_diagnosis(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='diagnosis_verdict_', dir=tmp) as td:
            report = Path(td) / 'report.json'
            report.write_text('{"operation":"diagnose_test_suite", "root_causes":["fabricated"]}', encoding='utf-8')
            rel = report.relative_to(root).as_posix()
            goal = 'Find the root cause of the failure in example.py.'
            cid = 'software.analysis.diagnose_and_architect.v1'
            args = {'capability_id': cid, 'operation': 'find_root_cause', 'output_path': rel}
            result = {'capability_id': cid, 'verified': True, 'gate': 'PASS', 'output_path': rel}
            trace = [{'plan': {'args': args}, 'result': result},
                     {'plan': {'args': {}}, 'result': {'type': 'finish'}}]
            contract = compile_contract(goal, source_id='user', routing_target_effects=[rel])
            self.assertTrue(contract['pass'])
            verdict = acceptance.verify(goal=goal, compiled_plan={'selected_capability': cid},
                                        execution=trace, raw_contract=contract, root=root)
            self.assertFalse(verdict['pass'], verdict)
            self.assertFalse(verdict['semantic_acceptance_complete'])
            self.assertIn('DIAGNOSIS_ROOT_CAUSE_NOT_INDEPENDENTLY_VERIFIED', str(verdict))

    def test_report_cannot_hide_the_requested_diagnosis_operation(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='diagnosis_verdict_', dir=tmp) as td:
            report = Path(td) / 'report.json'
            report.write_text('{"operation":"review_api_design"}', encoding='utf-8')
            rel = report.relative_to(root).as_posix()
            ok, reason, _ = acceptance.INSPECTORS['software.analysis.diagnose_and_architect.v1'](
                {'operation': 'find_root_cause', 'output_path': rel},
                {'verified': True, 'gate': 'PASS', 'output_path': rel}, root)
            self.assertFalse(ok)
            self.assertEqual(reason, 'DIAGNOSIS_ROOT_CAUSE_NOT_INDEPENDENTLY_VERIFIED')

    def test_other_analysis_report_is_not_verified_just_by_its_operation_name(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='diagnosis_verdict_', dir=tmp) as td:
            report = Path(td) / 'report.json'
            report.write_text('{"operation":"review_api_design"}', encoding='utf-8')
            rel = report.relative_to(root).as_posix()
            ok, reason, _ = acceptance.INSPECTORS['software.analysis.diagnose_and_architect.v1'](
                {'operation': 'review_api_design', 'output_path': rel},
                {'verified': True, 'gate': 'PASS', 'output_path': rel}, root)
            self.assertFalse(ok)
            self.assertEqual(reason, 'DIAGNOSE_ARCHITECT_REPORT_NOT_INDEPENDENTLY_VERIFIED')

    def test_no_root_cause_is_not_verified_just_because_report_is_parseable(self):
        root = Path(__file__).resolve().parents[2]
        tmp = root / 'canonical/astra_runtime/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='diagnosis_verdict_', dir=tmp) as td:
            report = Path(td) / 'report.json'
            report.write_text('{"operation":"find_root_cause"}', encoding='utf-8')
            rel = report.relative_to(root).as_posix()
            ok, reason, _ = acceptance.INSPECTORS['software.analysis.diagnose_and_architect.v1'](
                {'operation': 'find_root_cause', 'output_path': rel},
                {'verified': True, 'gate': 'PASS', 'output_path': rel}, root)
            self.assertFalse(ok)
            self.assertEqual(reason, 'DIAGNOSIS_ROOT_CAUSE_NOT_INDEPENDENTLY_VERIFIED')


if __name__ == '__main__':
    unittest.main()
