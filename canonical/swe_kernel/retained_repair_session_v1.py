"""Compose scoped source hypotheses with the existing production repair path.

This is not a new learner or authenticated skill authority. Caller-declared scope
and dependency context remain trusted inputs; actual candidate tests run through
ProjectTestOracle. All proposed patches must still pass the application's gates.
"""
from __future__ import annotations

import difflib
import sqlite3
from pathlib import Path
from typing import Mapping

from canonical.swe_kernel.skill_verification_contract_v1 import (
    ProjectTestOracle, applicable, normalize_contract, source_sha256,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore


class RetainedRepairSession:
    def __init__(self, config: Mapping, repo: Path, source_root: Path, exec_root: Path,
                 test_paths: list[Path], timeout: int):
        if set(config) - {'enabled', 'db_path', 'target_path', 'contract', 'context'}:
            raise ValueError('UNKNOWN_RETAINED_REPAIR_SETTING')
        self.contract = normalize_contract(config.get('contract'))
        if self.contract is None or self.contract['verification_kind'] != 'TEST_SUITE':
            raise ValueError('RETAINED_REPAIR_REQUIRES_TEST_SUITE_CONTRACT')
        self.context = config.get('context')
        self.target = (repo / str(config.get('target_path') or '')).resolve()
        if (not self.target.is_file() or self.target.suffix != '.py'
                or source_root not in self.target.parents):
            raise ValueError('RETAINED_TARGET_OUTSIDE_SOURCE_ROOT')
        raw_db = Path(str(config.get('db_path') or ''))
        self.db_path = (repo / raw_db).resolve()
        if (raw_db.is_absolute() or '..' in raw_db.parts or repo not in self.db_path.parents
                or self.db_path.suffix not in {'.sqlite', '.sqlite3'}
                or '.git' in raw_db.parts):
            raise ValueError('RETAINED_DATABASE_REQUIRES_CONTAINED_SQLITE_PATH')
        self.repo = repo
        self.oracle = ProjectTestOracle(exec_root, self.target.relative_to(exec_root).as_posix(),
                                        [p.relative_to(exec_root).as_posix() for p in test_paths],
                                        self.contract['scope_id'], timeout_s=min(timeout, 60))
        self.applicable = applicable(self.contract, self.contract['scope_id'], self.context)
        self.store = None
        self.metadata = {'enabled': True, 'applicable': self.applicable, 'hit': False,
                         'oracle_calls': 0, 'teaching': None,
                         'whole_task_correctness_proved': False}
        if self.applicable:
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self.store = VerifiedSkillStore(self.db_path, seed=False)
            except (sqlite3.Error, OSError) as exc:
                self.metadata['retention_error']=type(exc).__name__

    def propose(self):
        if self.store is None:
            return []
        before = self.target.read_text(encoding='utf-8')
        try:
            hit = self.store.recall_and_apply_verified(
                source_text=before, language='python', verifier=self.oracle,
                required_verification_kind='TEST_SUITE', scope_id=self.contract['scope_id'],
                context=self.context,
            )
        except (sqlite3.Error, OSError, ValueError) as exc:
            self.metadata['retention_error']=type(exc).__name__
            self.metadata['oracle_calls']=self.oracle.calls
            self.store=None
            return []
        self.metadata['oracle_calls'] = self.oracle.calls
        if hit is None:
            return []
        after = hit['patched_source']
        rel = self.target.relative_to(self.repo).as_posix()
        self.metadata.update(hit=True, skill_id=hit['skill_id'], verification=hit['verification'])
        return [{'source_path': rel,
                 'unified_diff': ''.join(difflib.unified_diff(before.splitlines(keepends=True),
                    after.splitlines(keepends=True), fromfile='a/' + rel, tofile='b/' + rel)),
                 'original_sha256': source_sha256(before), 'candidate_sha256': source_sha256(after),
                 'operator': 'scoped_retained_repair'}]

    def learn(self, originals: Mapping[Path, bytes]):
        if self.store is None or self.metadata['hit']:
            return
        if len(originals) != 1 or self.target not in originals:
            self.metadata['teaching'] = {'crystallized': False, 'reason': 'SINGLE_TARGET_TEACHING_ONLY'}
            return
        try:
            self.metadata['teaching'] = self.store.crystallize_code_fix(
                before_snippet=originals[self.target].decode('utf-8'),
                after_snippet=self.target.read_text(encoding='utf-8'), language='python',
                error_class='production_project_repair', contract=self.contract,
                training_verifier=self.oracle,
            )
        except Exception as exc:
            # A completed source repair is not undone because retention failed.
            self.metadata['teaching'] = {'crystallized': False, 'reason': type(exc).__name__}
        self.metadata['oracle_calls'] = self.oracle.calls
