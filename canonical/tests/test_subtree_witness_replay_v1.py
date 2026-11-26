"""Mechanism checks only. These are not single-shot benchmark results."""
import ast
from pathlib import Path
import tempfile
import unittest

from canonical.swe_kernel.causal_swe_repair_v1 import _passed_baseline_nodes, _regression_check
from canonical.swe_kernel.petri_cow_splicing_engine_v1 import AdmissionFilteredSkillStore


def admit(store, before, after, **overrides):
    return store.try_admit_subtree(**dict(dict(
        domain='format', concrete_before=before, concrete_after=after, verified=True,
        goal_relevant=True, probes_before_success=1, raw_episode_bytes=2048,
        source_fingerprint='v1', witness_inputs=[{'case': 'baseline'}],
        revalidation_probe={'test_target': 'tests/test_format.py'},
    ), **overrides))


class SubtreeReplayTests(unittest.TestCase):
    def test_derive_and_replay_a_nested_window_not_the_enclosing_file(self):
        before = 'class One:\n    def fmt(self, text):\n        if text is None:\n            return None\n        return self.title(), text\n'
        after = before.replace('return None', "return self.title(), ''")
        target = '# untouched: π\nclass Other:\n    def show(me, label):\n        try:\n            do_work()\n        finally:\n            if label is None:\n                return None\n            return me.heading(), label\n\n# untouched footer\n'
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / 'rules.json'
            store = AdmissionFilteredSkillStore(fp)
            ok, sid = admit(store, before, after)
            self.assertTrue(ok, sid)
            self.assertNotIn('class One', store.records[sid].concrete_before)
            fresh = AdmissionFilteredSkillStore(fp)
            ((candidate, found_id),) = fresh.retrieve_for_subtree(target)
            self.assertEqual(found_id, sid)
            self.assertTrue(candidate.startswith(target.split('            if label')[0]))
            self.assertTrue(candidate.endswith('\n\n# untouched footer\n'))
            self.assertEqual(ast.dump(ast.parse(candidate)),
                             ast.dump(ast.parse(target.replace('return None', "return me.heading(), ''"))))
            raw = AdmissionFilteredSkillStore(fp, mode='raw_traces')
            self.assertEqual(raw.retrieve_for_subtree(target), [])
            self.assertEqual(len(raw.retrieve_for_subtree(before)), 1)
            self.assertTrue(fresh.remove_skill(sid))
            self.assertEqual(AdmissionFilteredSkillStore(fp).retrieve_for_subtree(target), [])

    def test_bound_placeholders_and_witness_must_replay_before_admission(self):
        store = AdmissionFilteredSkillStore()
        # New API names are requirements, not unbound schematic attributes.
        self.assertTrue(admit(store, 'return text', 'return text.strip()')[0])
        ((proposal, _),) = store.retrieve_for_subtree('return name')
        self.assertEqual(proposal, 'return name.strip()')
        self.assertEqual(admit(store, 'x = 2', 'x = 2 # not a code change'),
                         (False, 'REJECTED__NO_STRUCTURAL_EDIT'))
        self.assertEqual(admit(store, 'return x', 'return x + 1', raw_episode_bytes=1),
                         (False, 'REJECTED__NOT_COMPRESSIBLE'))
        self.assertEqual(admit(store, 'return x', 'return helper(x)'),
                         (False, 'REJECTED__FOREIGN_IDENT_UNBOUND:helper'))
        # Induction from the second of two indistinguishable LHSs cannot
        # certify applying just the first match; no entry goes on disk.
        self.assertEqual(admit(store, 'a = 1\na = 1', 'a = 1\na = 2'),
                         (False, 'REJECTED__WITNESS_NOT_REPLAYED'))

    def test_full_width_edit_cache_invalidation_and_literal_types(self):
        store = AdmissionFilteredSkillStore()
        old = '\n'.join(f'a = {i}' for i in range(6))
        new = old.replace('= 0', '= -1').replace('= 5', '= 7')
        ok, sid = admit(store, old, new)
        self.assertTrue(ok, sid)
        target = 'def f():\n' + '\n'.join('    ' + line.replace('a =', 'b =') for line in old.splitlines())
        ((proposal, _),) = store.retrieve_for_subtree(target)
        self.assertEqual(proposal, target.replace('= 0', '= -1').replace('= 5', '= 7'))
        self.assertEqual(store.retrieve_for_subtree(target.replace('= 0', '= False')), [])
        store.edit_skill(sid, lhs_ir_sexpr='return True', rhs_ir_sexpr='return False')
        self.assertEqual(store.retrieve_for_subtree(target), [])
        self.assertEqual(store.retrieve_for_subtree('return True'), [])  # edited, not revalidated
        store.check_and_refresh_staleness({'format': 'v2'})
        self.assertEqual(store.retrieve_for_subtree('return True'), [])
        store.check_and_refresh_staleness({'format': 'v2'}, lambda p: p == {'test_target': 'tests/test_format.py'})
        self.assertEqual(store.retrieve_for_subtree('return True'), [('return False', sid)])

    def test_missing_test_identity_cannot_make_a_repair_green(self):
        base = {'passing': ['old-pass'], 'failing': ['old-fail']}
        for ok, names in [(False, base['passing'] + base['failing']), (True, []),
                          (True, ['old-pass', 'different']), (True, ['different', 'old-fail'])]:
            self.assertFalse(_passed_baseline_nodes(base, {'ok': ok, 'passing': names}))
        self.assertTrue(_passed_baseline_nodes(base, {'ok': True, 'passing': ['old-pass', 'old-fail']}))

    def test_witness_identity_and_completeness_in_regression_controls(self):
        before = {'returncode': 1, 'passing': ['a'], 'failing': ['b']}
        self.assertIsNone(_regression_check(before, before))  # pre-existing failure
        self.assertIsNone(_regression_check(before, dict(returncode=0, passing=['a', 'b'], failing=[])))
        self.assertEqual(_regression_check(before, dict(returncode=1, passing=['b'], failing=['a'])),
                         'REGRESSED_CROSS_MODULE_IMPACTED_TESTS')
        for after in ({}, dict(returncode=1, passing=['a', 'b'], failing=[]),
                      dict(returncode=2, passing=['a', 'b'], failing=[]),
                      dict(returncode=0, passing=['a'], failing=[])):
            self.assertEqual(_regression_check(before, after), 'INCOMPLETE_REGRESSION_CHECK')
