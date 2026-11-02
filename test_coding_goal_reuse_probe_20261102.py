"""Checks the disposable coding-loop instrument, not universal learning."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent


class CodingGoalReuseProbeTests(unittest.TestCase):
    def test_real_repair_reuse_and_raw_goal_outcomes_are_observed(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'coding_goal_reuse_probe_20261102.py')],
                              cwd=ROOT, capture_output=True, text=True, check=True, timeout=180)
        report = json.loads(proc.stdout)
        rows = {row['role']: row for row in report['rows']}
        self.assertEqual(set(rows), {'teaching', 'cold', 'warm', 'direct_teaching',
                                     'direct_cold', 'direct_warm'})
        self.assertEqual(len({row['worker_pid'] for row in rows.values()}), 6)
        for row in rows.values():
            self.assertTrue(row['tests_unchanged'], row)
            self.assertFalse(row['separate_audit_pass_before'], row)
        for name in ('direct_teaching', 'direct_cold', 'direct_warm'):
            self.assertTrue(rows[name]['pass'], rows[name])
            self.assertTrue(rows[name]['source_changed'], rows[name])
            self.assertTrue(rows[name]['separate_audit_pass'], rows[name])
        self.assertTrue(rows['direct_teaching']['crystallized'])
        self.assertEqual(rows['direct_teaching']['search_invocations'], 1)
        self.assertFalse(rows['direct_cold']['retained_enabled'])
        self.assertEqual(rows['direct_cold']['search_invocations'], 1)
        self.assertTrue(rows['direct_warm']['retained_hit'])
        self.assertEqual(rows['direct_warm']['search_invocations'], 0)
        # The goal asks for repair, not an audit. Until there is enough authority
        # to execute a repair, fail closed without changing source or claiming a
        # successful task. If repair becomes available, check the world, not just
        # the returned status or a report file.
        for name in ('teaching', 'cold', 'warm'):
            row = rows[name]
            self.assertNotEqual(row['selected_capability'], 'python.tests.audit.unittest', row)
            if row['pass']:
                self.assertTrue(row['source_changed'], row)
                self.assertTrue(row['separate_audit_pass'], row)
            else:
                self.assertFalse(row['source_changed'], row)
                self.assertFalse(row['permanent_reuse_authorized'], row)

        if 'BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT' in (report['repair_bound_gate'] or ''):
            self.assertEqual(rows['teaching']['knowledge_gap']['status'], 'RECORDED')
            self.assertEqual(rows['teaching']['gap_count'], 1)
            self.assertIsNone(rows['cold']['knowledge_gap'])
            self.assertTrue(rows['cold']['gap_store_unchanged'])
            self.assertEqual(rows['warm']['gap_count'], 1)
            self.assertEqual(rows['teaching']['knowledge_gap']['gap_id'],
                             rows['warm']['knowledge_gap']['gap_id'])

        controls = {row['role']: row for row in report['controls']}
        for name, row in controls.items():
            if name != 'alternate_repair' or not row['pass']:
                self.assertFalse(row['source_changed'], row)
            else:
                self.assertTrue(row['separate_audit_pass'], row)
            self.assertTrue(row['tests_unchanged'], row)
        self.assertTrue(controls['already_correct']['separate_audit_pass_before'])
        self.assertTrue(controls['already_correct']['separate_audit_pass'])
        audit = controls['audit']
        self.assertEqual(audit['selected_capability'], 'python.tests.audit.unittest')
        self.assertTrue(audit['pass'])
        self.assertTrue(audit['report_exists'])
        for name in ('run_failing_tests', 'question', 'unrelated'):
            self.assertNotEqual(controls[name]['selected_capability'],
                                'python.software.repair.apply.verified.v1', controls[name])
        unavailable = controls['typed_plan_unavailable']
        self.assertEqual(unavailable['status'], 'FAIL_CLOSED__STATED_REPAIR_ROUTE_UNAVAILABLE')
        self.assertEqual(unavailable['refused_capability'], 'python.tests.audit.unittest')
        self.assertFalse(unavailable['pass'])
        self.assertFalse(unavailable['report_exists'])
        for name in ('alternate_repair', 'already_correct'):
            self.assertNotEqual(controls[name]['selected_capability'],
                                'python.tests.audit.unittest', controls[name])
        explicit = controls['explicit_audit']
        self.assertFalse(explicit['pass'])
        self.assertFalse(explicit['report_exists'])
        # If the registry lacks independent evidence, rerouting must not evade
        # the bound execution gate. A later legitimate certification may make
        # this capability executable, at which point the audit above is decisive.
        if 'BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT' in (report['repair_bound_gate'] or ''):
            for name in ('teaching', 'cold', 'warm'):
                self.assertIn('BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT',
                              rows[name]['reason'])


if __name__ == '__main__':
    unittest.main()
