"""Controlled tests of a read-only repair candidate, not carrier qualification."""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import effect_broker_contract_v1 as effects
from canonical.runtime import repair_candidate_broker_v1 as broker


class RepairCandidateBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='repair_candidate_')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'project'
        (self.project / 'src').mkdir(parents=True)
        (self.project / 'tests').mkdir()
        (self.project / 'src' / 'm.py').write_text('def f(): return 0\n')
        (self.project / 'tests' / 'test_m.py').write_text('def test_f(): assert True\n')
        self.original = broker.snapshot_project(self.project)
        self.staging_parent = self.base / 'staging'
        self.staging_parent.mkdir()
        self.stage = broker.stage_project(self.original, staging_parent=self.staging_parent)

    def candidate(self):
        return broker.compare_candidate(self.original, broker.snapshot_project(self.stage),
                                        target='src/m.py', protected_tests=('tests/test_m.py',))

    def test_staging_is_separate_and_a_changed_candidate_is_not_an_approval(self):
        self.assertEqual(broker.snapshot_project(self.stage).digest, self.original.digest)
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        result = self.candidate()
        self.assertEqual((self.project / 'src' / 'm.py').read_text(), 'def f(): return 0\n')
        self.assertEqual(result['status'], 'CANDIDATE_ONLY__NOT_VERIFIED_OR_AUTHORIZED')
        self.assertFalse(result['publication_authority'])
        self.assertFalse(result['execution_authority'])
        self.assertFalse(result['semantic_acceptance_complete'])
        self.assertFalse(result['metadata_checked'])
        self.assertNotEqual(result['expected_pre_sha256'], result['candidate_sha256'])

    def test_unsigned_effect_request_does_not_grant_publication(self):
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        after = broker.snapshot_project(self.stage)
        request = broker.effect_request(self.original, after, target='src/m.py',
                                        protected_tests=('tests/test_m.py',), mission_id='test',
                                        capsule_head_sha256='a' * 64, action_ref='repair')
        self.assertEqual(effects.verify_request(request), request)
        self.assertEqual(request['effect_kind'], 'REPO_WRITE')
        self.assertEqual(request['resource'], 'project:src/m.py')
        self.assertEqual(request['payload']['candidate_sha256'], self.candidate()['candidate_sha256'])
        self.assertFalse(effects.admit(request, {})['allowed'])
        self.assertEqual((self.project / 'src' / 'm.py').read_text(), 'def f(): return 0\n')

    def test_permission_changes_are_not_mistaken_for_checked_metadata(self):
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        (self.stage / 'tests' / 'test_m.py').chmod(0o777)
        result = self.candidate()
        self.assertFalse(result['metadata_checked'])
        self.assertFalse(result['publication_authority'])

    def test_stage_write_failure_does_not_change_source(self):
        with patch.object(broker.os, 'write', side_effect=OSError('simulated full disk')):
            with self.assertRaisesRegex(broker.CandidateDenied, 'STAGING_FAILED'):
                broker.stage_project(self.original, staging_parent=self.staging_parent)
        self.assertEqual(broker.snapshot_project(self.project).digest, self.original.digest)
        self.assertEqual(len(list(self.staging_parent.iterdir())), 1)  # preexisting stage only

    def test_acceptance_subject_binds_goal_policy_patch_and_test_bytes_without_authority(self):
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        after = broker.snapshot_project(self.stage)
        options = {'target': 'src/m.py', 'protected_tests': ('tests/test_m.py',),
                   'task_id': 'task', 'goal': 'make f return 1', 'learning_mode': 'off'}
        subject = broker.acceptance_subject(self.original, after, **options)
        self.assertFalse(subject['semantic_acceptance_complete'])
        self.assertFalse(subject['publication_authority'])
        self.assertEqual(subject['declared_test_sha256']['tests/test_m.py'],
                         broker._sha((self.project / 'tests/test_m.py').read_bytes()))
        for field, value in (('goal', 'make f return 2'), ('task_id', 'another'), ('learning_mode', 'use')):
            changed = broker.acceptance_subject(self.original, after, **{**options, field: value})
            self.assertNotEqual(subject['subject_sha256'], changed['subject_sha256'])
        request = broker.acceptance_effect_request(self.original, after, **options,
                  mission_id='test', capsule_head_sha256='a' * 64, action_ref='repair')
        self.assertEqual(request['payload'], subject)
        self.assertFalse(effects.admit(request, {})['allowed'])
        (self.stage / 'src/m.py').write_text('def f(): return 2\n')
        changed_patch = broker.acceptance_subject(self.original, broker.snapshot_project(self.stage), **options)
        self.assertNotEqual(subject['subject_sha256'], changed_patch['subject_sha256'])
        (self.stage / 'tests/test_m.py').write_text('pass\n')
        with self.assertRaisesRegex(broker.CandidateDenied, 'ONLY_ONE_TARGET_MAY_CHANGE'):
            broker.acceptance_subject(self.original, broker.snapshot_project(self.stage), **options)

    def test_acceptance_subject_rejects_missing_or_ambiguous_inputs(self):
        (self.stage / 'src/m.py').write_text('def f(): return 1\n')
        after = broker.snapshot_project(self.stage)
        options = {'target': 'src/m.py', 'protected_tests': ('tests/test_m.py',),
                   'task_id': 'task', 'goal': 'goal', 'learning_mode': 'off'}
        for field, value in (('task_id', ''), ('goal', ''), ('goal', 'x' * 4097),
                             ('learning_mode', False), ('learning_mode', 'enabled')):
            with self.subTest(field=field, value=value), self.assertRaises(broker.CandidateDenied):
                broker.acceptance_subject(self.original, after, **{**options, field: value})

    def test_scope_checker_does_not_claim_wrong_code_is_correct(self):
        # Scope alone cannot distinguish this intentionally wrong repair.
        (self.stage / 'src' / 'm.py').write_text('def f(): return -999\n')
        result = self.candidate()
        self.assertFalse(result['semantic_acceptance_complete'])
        self.assertFalse(result['publication_authority'])

    def test_no_change_and_additional_changed_test_are_denied(self):
        with self.assertRaisesRegex(broker.CandidateDenied, 'ONLY_ONE_TARGET_MAY_CHANGE'):
            self.candidate()
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        (self.stage / 'tests' / 'test_m.py').write_text('pass\n')
        with self.assertRaisesRegex(broker.CandidateDenied, 'ONLY_ONE_TARGET_MAY_CHANGE'):
            self.candidate()

    def test_extra_file_empty_directory_and_deleted_file_are_denied(self):
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        extra = self.stage / 'extra.txt'
        extra.write_text('extra')
        with self.assertRaisesRegex(broker.CandidateDenied, 'PROJECT_LAYOUT_CHANGED'):
            self.candidate()
        extra.unlink()
        (self.stage / 'newdir').mkdir()
        with self.assertRaisesRegex(broker.CandidateDenied, 'PROJECT_LAYOUT_CHANGED'):
            self.candidate()
        (self.stage / 'newdir').rmdir()
        (self.stage / 'tests' / 'test_m.py').unlink()
        with self.assertRaisesRegex(broker.CandidateDenied, 'PROJECT_LAYOUT_CHANGED'):
            self.candidate()

    def test_symlink_hardlink_and_fifo_are_denied_without_reading_them(self):
        outside = self.base / 'outside'
        outside.write_text('private')
        link = self.stage / 'new'
        link.symlink_to(outside)
        with self.assertRaisesRegex(broker.CandidateDenied, 'SYMLINK_OR_SPECIAL_FILE_DENIED'):
            broker.snapshot_project(self.stage)
        link.unlink()
        os.link(outside, link)
        with self.assertRaisesRegex(broker.CandidateDenied, 'HARDLINK_DENIED'):
            broker.snapshot_project(self.stage)
        link.unlink()
        os.mkfifo(link)
        with self.assertRaisesRegex(broker.CandidateDenied, 'SYMLINK_OR_SPECIAL_FILE_DENIED'):
            broker.snapshot_project(self.stage)
        self.assertEqual(outside.read_text(), 'private')

    def test_symlinked_root_and_git_are_denied(self):
        link = self.base / 'alias'
        link.symlink_to(self.project, target_is_directory=True)
        with self.assertRaisesRegex(broker.CandidateDenied, 'PROJECT_SNAPSHOT_FAILED'):
            broker.snapshot_project(link)
        (self.stage / '.git').mkdir()
        with self.assertRaisesRegex(broker.CandidateDenied, 'PATH_INVALID'):
            broker.snapshot_project(self.stage)

    def test_staging_in_source_or_nested_source_is_denied(self):
        for parent in (self.project, self.project / 'src'):
            with self.subTest(parent=parent), self.assertRaisesRegex(broker.CandidateDenied, 'STAGING_PARENT_INSIDE_SOURCE'):
                broker.stage_project(self.original, staging_parent=parent)
        self.assertEqual(broker.snapshot_project(self.project).digest, self.original.digest)

    def test_invalid_paths_and_test_scope_are_denied(self):
        (self.stage / 'src' / 'm.py').write_text('def f(): return 1\n')
        after = broker.snapshot_project(self.stage)
        for target in ('../outside.py', '/src/m.py', 'src//m.py', 'src/./m.py', 'src\\m.py', 'src/m.py\x00'):
            with self.subTest(target=target), self.assertRaises(broker.CandidateDenied):
                broker.compare_candidate(self.original, after, target=target, protected_tests=('tests/test_m.py',))
        for protected in ((), ('missing.py',), ('src/m.py',), ('tests/test_m.py', 'tests/test_m.py')):
            with self.subTest(protected=protected), self.assertRaises(broker.CandidateDenied):
                broker.compare_candidate(self.original, after, target='src/m.py', protected_tests=protected)

    def test_snapshot_rejects_a_file_changed_during_read(self):
        target = self.project / 'src/m.py'
        inode = target.stat().st_ino
        original_read = os.read
        changed = []
        def read_and_mutate(fd, count):
            data = original_read(fd, count)
            if os.fstat(fd).st_ino == inode and not changed:
                target.write_bytes(b'concurrent edit\n')
                changed.append(True)
            return data
        with patch.object(broker.os, 'read', side_effect=read_and_mutate):
            with self.assertRaisesRegex(broker.CandidateDenied, 'TREE_CHANGED_DURING_SNAPSHOT'):
                broker.snapshot_project(self.project)
        self.assertEqual(changed, [True])

    def test_forged_snapshot_and_resource_excess_are_denied(self):
        path, data = self.original.files[0]
        forged = replace(self.original, files=((path, data + b'x'),) + self.original.files[1:])
        with self.assertRaisesRegex(broker.CandidateDenied, 'SNAPSHOT_INVALID'):
            broker.stage_project(forged, staging_parent=self.staging_parent)
        with patch.object(broker, 'MAX_FILE_BYTES', 3):
            with self.assertRaisesRegex(broker.CandidateDenied, 'PROJECT_BYTES_EXCEEDED'):
                broker.snapshot_project(self.project)
        with patch.object(broker, 'MAX_FILES', 1):
            with self.assertRaisesRegex(broker.CandidateDenied, 'TOO_MANY_FILES'):
                broker.snapshot_project(self.project)
