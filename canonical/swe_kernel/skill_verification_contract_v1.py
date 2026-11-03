"""Scoped verification records for skill hypotheses, not capability certificates.

A trusted verifier is still a trust boundary: a declared kind is not an oracle.
ProjectTestOracle obtains TEST_SUITE evidence from the existing copied-tree
measurement runner. Passing that suite does not prove the whole user request.
These local records confer no authenticated executable-skill authority; that
separate boundary remains executable_skill_verification_authenticator_v1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import tempfile
from typing import Any, Mapping

KINDS = frozenset({'CALLER_PREDICATE', 'SYNTAX', 'COMPILATION', 'TEST_SUITE'})


def source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    kind: str
    candidate_sha256: str
    scope_id: str = ''
    evidence: Mapping[str, Any] = field(default_factory=dict)


def evaluate(verifier, candidate: str, required_kind: str = 'CALLER_PREDICATE',
             scope_id: str = '') -> dict[str, Any] | None:
    """Never infer behavioral assurance from truthiness or a callback's name."""
    if required_kind not in KINDS:
        raise ValueError('UNKNOWN_VERIFICATION_KIND')
    try:
        result = verifier(candidate)
        if type(result) is bool:
            result = VerificationResult(result, 'CALLER_PREDICATE', source_sha256(candidate))
        if not isinstance(result, VerificationResult) or result.passed is not True:
            return None
        if result.kind not in KINDS or result.candidate_sha256 != source_sha256(candidate):
            return None
        if required_kind != 'CALLER_PREDICATE' and result.kind != required_kind:
            return None
        if scope_id and result.scope_id != scope_id:
            return None
        evidence = dict(result.evidence)
        if result.kind == 'TEST_SUITE':
            if (not result.scope_id or type(evidence.get('test_count')) is not int
                    or evidence['test_count'] <= 0 or type(evidence.get('returncode')) is not int
                    or evidence.get('returncode') != 0
                    or not evidence.get('measurement_program_sha256')
                    or not evidence.get('measurement_spec_sha256')
                    or not evidence.get('snapshot_sha256')):
                return None
        if result.kind == 'COMPILATION' and (type(evidence.get('returncode')) is not int
                                             or evidence.get('returncode') != 0 or not evidence.get('compiler')):
            return None
        return {'kind': result.kind, 'scope_id': result.scope_id,
                'candidate_sha256': result.candidate_sha256, 'evidence': evidence,
                'whole_task_correctness_proved': False}
    except Exception:
        return None


def normalize_contract(contract: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if contract is None:
        return None
    if (not isinstance(contract, Mapping) or type(contract.get('schema_version')) is not int
            or contract['schema_version'] != 1):
        raise ValueError('SKILL_CONTRACT_VERSION_UNSUPPORTED')
    if not isinstance(contract.get('scope_id'), str) or not contract['scope_id'].strip():
        raise ValueError('SKILL_SCOPE_REQUIRED')
    allowed_fields = {'schema_version', 'scope_id', 'verification_kind', 'dependencies', 'preconditions', 'effects', 'invalidators'}
    if set(contract) - allowed_fields:
        raise ValueError('UNSUPPORTED_SKILL_CONTRACT_FIELD')
    kind = contract.get('verification_kind')
    if kind not in KINDS - {'CALLER_PREDICATE'}:
        raise ValueError('SCOPED_SKILL_REQUIRES_EXPLICIT_VERIFICATION_KIND')
    normalized = {'schema_version': 1, 'scope_id': contract['scope_id'], 'verification_kind': kind}
    for name in ('dependencies', 'preconditions'):
        values = contract.get(name, {})
        if not isinstance(values, Mapping) or any(
            not isinstance(k, str) or not k or type(v) not in (str, int, bool, type(None))
            for k, v in values.items()
        ):
            raise ValueError('INVALID_SKILL_' + name.upper())
        normalized[name] = dict(values)
    # This store proposes source text; it does not have authority to apply it.
    normalized['effects'] = {'allowed': ['PROPOSE_TARGET_SOURCE_REWRITE'],
                             'forbidden': ['MUTATE_TESTS', 'EXECUTE_WITHOUT_CURRENT_VERIFICATION']}
    normalized['invalidators'] = ['SCOPE_CHANGE', 'DEPENDENCY_CHANGE', 'PRECONDITION_CHANGE', 'COUNTEREXAMPLE']
    for name in ('effects', 'invalidators'):
        if name in contract and contract[name] != normalized[name]:
            raise ValueError('UNSUPPORTED_SKILL_' + name.upper())
    return normalized


def applicable(
    contract,
    scope_id: str,
    context: Mapping[str, Any] | None,
    *,
    allow_cross_scope: bool = False,
) -> bool:
    try:
        expected = normalize_contract(contract)
    except (ValueError, TypeError):
        return False
    if expected is None:
        return not scope_id
    if not isinstance(context, Mapping) or not isinstance(scope_id, str) or not scope_id.strip():
        return False
    if expected['scope_id'] != scope_id:
        if not (allow_cross_scope and expected['verification_kind'] == 'TEST_SUITE'):
            return False
    for name in ('dependencies', 'preconditions'):
        observed = context.get(name)
        if not isinstance(observed, Mapping):
            return False
        for key, value in expected[name].items():
            if key not in observed or type(observed[key]) is not type(value) or observed[key] != value:
                return False
    return True


def _resolve_chroot_binary(name: str, fallbacks: tuple[str, ...]) -> str | None:
    found = shutil.which(name)
    if found and (found.startswith('/usr/') or found.startswith('/bin/')) and os.path.isfile(found):
        return found
    for cand in fallbacks:
        if os.path.isfile(cand):
            return cand
    return None


class ProjectTestOracle:
    """Check one candidate in copies of a bounded Python project.

    Original source is never patched. Reuses the existing acceptance measurement
    and suite runner, including zero-test rejection at this verification boundary.
    Test execution is not an OS sandbox; only trusted project tests should run.
    """
    def __init__(self, project_root: Path, target_path: str, test_paths: list[str],
                 scope_id: str, *, timeout_s: int = 20):
        from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement
        self.root = Path(project_root).resolve()
        rel = PurePosixPath(target_path)
        if rel.is_absolute() or '..' in rel.parts or not target_path.endswith('.py'):
            raise ValueError('INVALID_SKILL_TARGET')
        target_path = str(rel)
        path = self.root / rel
        if path.is_symlink() or not path.is_file() or self.root not in path.resolve().parents:
            raise ValueError('INVALID_SKILL_TARGET')
        for parent in path.parents:
            if parent == self.root:
                break
            if parent.is_symlink():
                raise ValueError('SKILL_TARGET_SYMLINK')
        selected = measurement._validate_test_paths(self.root, test_paths, self.root)
        if target_path in selected or measurement._is_test_file_name(path.name) or path.name == 'conftest.py':
            raise ValueError('SKILL_MUST_NOT_REWRITE_ITS_TESTS')
        if not scope_id:
            raise ValueError('VERIFICATION_SCOPE_REQUIRED')
        self.target_path, self.test_paths, self.scope_id = target_path, selected, scope_id
        self.timeout_s = timeout_s
        self.calls = 0

    def __call__(self, candidate: str) -> VerificationResult:
        from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement
        self.calls += 1
        try:
            original_manifest, _ = measurement._tree_manifest(self.root, max_files=1000, max_bytes=16_000_000)
            with tempfile.TemporaryDirectory(prefix='brain-skill-oracle-') as td:
                copied = Path(td) / 'project'
                measurement._copy_source(self.root, copied)
                (copied / self.target_path).write_text(candidate, encoding='utf-8')
                report = measurement.run({'source_root': '.', 'test_paths': self.test_paths,
                                          'output_path': '.brain_skill_measurement.json',
                                          'timeout_s': self.timeout_s, 'max_files': 1000,
                                          'max_bytes': 16_000_000}, copied)
            final_manifest, _ = measurement._tree_manifest(self.root, max_files=1000, max_bytes=16_000_000)
            if final_manifest != original_manifest:
                raise measurement.MeasurementError('ORIGINAL_PROJECT_CHANGED_DURING_VERIFICATION')
            values = report['measurements']
            passed = (values['tests_pass'] and values['test_count'] > 0
                      and values['python_parse_ok'] and values['repository_source_unchanged'])
            evidence = {'test_count': values['test_count'], 'returncode': values['test_returncode'],
                        'measurement_program_sha256': report['measurement_program_sha256'],
                        'measurement_spec_sha256': report['measurement_spec_sha256'],
                        'snapshot_sha256': report['subject']['snapshot_sha256'],
                        'test_evidence': report['test_evidence']}
            return VerificationResult(bool(passed), 'TEST_SUITE', source_sha256(candidate), self.scope_id, evidence)
        except Exception as exc:
            return VerificationResult(False, 'TEST_SUITE', source_sha256(candidate), self.scope_id,
                                      {'error': type(exc).__name__})


class ConfinedLanguageTestOracle:
    """Verify non-Python candidates (`js`/`ts`/`cpp`/`c`/`rust`/`go`) inside `brokered_workspace_execution_v1`.

    Auto-discovers installed polyglot runners (`node --test`, `node --experimental-strip-types --test`,
    `g++ -std=c++17`, `gcc`, `go test -v`, `cargo test --offline` / `rustc --test`), injects the
    candidate via zero-copy `candidate_overrides` (never touching `project_root` or any test file),
    runs inside `zero_ambient_namespace_launcher_v1`, parses real non-zero test count, and verifies
    `project_root` remained byte-for-byte unchanged.
    """

    _EXTS = ('.js', '.mjs', '.cjs', '.ts', '.tsx', '.rs', '.go', '.cpp', '.cc', '.cxx', '.c', '.hpp', '.h')

    def __init__(
        self,
        project_root: Path,
        target_path: str,
        test_paths: list[str],
        scope_id: str,
        *,
        runner_argv: list[str] | None = None,
        timeout_s: int = 20,
    ) -> None:
        from canonical.runtime import repair_candidate_broker_v1 as rcb

        self.root = Path(project_root).resolve()
        rel = PurePosixPath(target_path)
        if rel.is_absolute() or '..' in rel.parts or not any(target_path.endswith(ext) for ext in self._EXTS):
            raise ValueError('INVALID_SKILL_TARGET')
        if not test_paths:
            raise ValueError('TEST_PATHS_REQUIRED')
        clean_tests: list[str] = []
        for tp in test_paths:
            trel = PurePosixPath(tp)
            if trel.is_absolute() or '..' in trel.parts or str(trel) == str(rel):
                raise ValueError('SKILL_MUST_NOT_REWRITE_ITS_TESTS')
            if not (self.root / trel).is_file():
                raise ValueError('MISSING_TEST_FILE')
            clean_tests.append(str(trel))
        if not (self.root / rel).is_file():
            raise ValueError('INVALID_SKILL_TARGET')
        if not scope_id:
            raise ValueError('VERIFICATION_SCOPE_REQUIRED')
        self._initial_snap = rcb.snapshot_project(self.root)
        self.target_path = str(rel)
        self.test_paths = clean_tests
        self.scope_id = scope_id
        self.timeout_s = timeout_s
        if runner_argv is not None:
            self.runner_argv = [str(x) for x in runner_argv]
        else:
            self.runner_argv = self._discover_runner_argv()
        self.calls = 0

    def _discover_runner_argv(self) -> list[str]:
        tp = self.target_path
        if tp.endswith(('.js', '.mjs', '.cjs')):
            node_bin = _resolve_chroot_binary('node', ('/usr/local/bin/node', '/usr/bin/node'))
            if not node_bin:
                raise ValueError('LANGUAGE_RUNNER_UNAVAILABLE:javascript')
            return [node_bin, '--test', *self.test_paths]
        if tp.endswith(('.ts', '.tsx')):
            node_bin = _resolve_chroot_binary('node', ('/usr/local/bin/node', '/usr/bin/node'))
            if not node_bin:
                raise ValueError('LANGUAGE_RUNNER_UNAVAILABLE:typescript')
            return [node_bin, '--experimental-strip-types', '--test', *self.test_paths]
        if tp.endswith(('.cpp', '.cc', '.cxx', '.hpp', '.h', '.c')):
            is_c = tp.endswith('.c') and all(t.endswith('.c') for t in self.test_paths)
            compiler = _resolve_chroot_binary(
                'gcc' if is_c else 'g++',
                ('/usr/bin/gcc', '/usr/local/bin/gcc') if is_c else ('/usr/bin/g++', '/usr/local/bin/g++'),
            )
            if not compiler:
                raise ValueError('LANGUAGE_RUNNER_UNAVAILABLE:cpp')
            sources = list(self.test_paths)
            if tp.endswith(('.cpp', '.cc', '.cxx', '.c')) and tp not in sources:
                # Avoid duplicate symbol definition when test file `#include`s target translation unit directly
                target_name = PurePosixPath(tp).name
                included = any(
                    target_name in (self.root / t).read_text(encoding='utf-8', errors='replace')
                    for t in self.test_paths
                )
                if not included:
                    sources.append(tp)
            std_flag = '-std=c11' if is_c else '-std=c++17'
            quoted_srcs = ' '.join(shlex.quote(s) for s in sources)
            cmd = f'{shlex.quote(compiler)} {std_flag} -O0 -I. {quoted_srcs} -o /work/tmp/cpp_oracle_bin && /work/tmp/cpp_oracle_bin'
            return ['/bin/sh', '-c', cmd]
        if tp.endswith('.go'):
            go_bin = _resolve_chroot_binary('go', ('/usr/local/go/bin/go', '/usr/bin/go'))
            if not go_bin:
                raise ValueError('LANGUAGE_RUNNER_UNAVAILABLE:go')
            return [go_bin, 'test', '-v', './...']
        if tp.endswith('.rs'):
            cargo_bin = _resolve_chroot_binary('cargo', ('/usr/bin/cargo', '/usr/local/bin/cargo'))
            if (self.root / 'Cargo.toml').is_file() and cargo_bin:
                return [cargo_bin, 'test', '--offline']
            rustc_bin = _resolve_chroot_binary('rustc', ('/usr/bin/rustc', '/usr/local/bin/rustc'))
            if rustc_bin:
                t0 = shlex.quote(self.test_paths[0])
                return ['/bin/sh', '-c', f'{shlex.quote(rustc_bin)} --test {t0} -o /work/tmp/rs_oracle_bin && /work/tmp/rs_oracle_bin']
            raise ValueError('LANGUAGE_RUNNER_UNAVAILABLE:rust')
        raise ValueError('RUNNER_ARGV_REQUIRED_FOR_LANGUAGE')

    def __call__(self, candidate: str) -> VerificationResult:
        import json as _json
        import re as _re
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        from canonical.runtime import repair_candidate_broker_v1 as rcb

        self.calls += 1
        try:
            orig_snap = rcb.snapshot_project(self.root)
            res = broker.run_staged_confined_command(
                self.root,
                self.runner_argv,
                publish=False,
                pythonpath_work=False,
                timeout=self.timeout_s,
                candidate_overrides={self.target_path: candidate.encode('utf-8')},
                task_id=f'lang-oracle:{self.scope_id}',
            )
            final_snap = rcb.snapshot_project(self.root)
            if final_snap.digest != orig_snap.digest:
                raise RuntimeError('ORIGINAL_PROJECT_CHANGED_DURING_VERIFICATION')
            if not res.get('confined'):
                return VerificationResult(False, 'TEST_SUITE', source_sha256(candidate), self.scope_id,
                                          {'error': str(res.get('blocked') or 'UNCONFINED')})
            combined = str(res.get('stdout') or '') + '\n' + str(res.get('stderr') or '')
            m_tests = _re.search(r'(?:#\s*tests\s+(\d+)|(\d+)\s+tests?\s+passed)', combined, _re.IGNORECASE)
            m_pass = _re.search(
                r'(?:#\s*pass\s+(\d+)|(\d+)\s+passed|---\s*PASS:|\[PASS\]|\bPASS\b(?::\s*(\d+))?|ok\s+\S+)',
                combined,
            )
            if m_tests:
                test_count = int(m_tests.group(1) or m_tests.group(2))
            elif m_pass:
                num = m_pass.group(1) or m_pass.group(2) or m_pass.group(3)
                test_count = int(num) if num else max(1, len(_re.findall(r'(?:---\s*PASS:|\[PASS\])', combined)))
            else:
                test_count = 0
            rc = int(res.get('exit', -1))
            passed = bool(res.get('ok') and rc == 0 and test_count > 0 and not res.get('changed_files'))
            prog_sha = hashlib.sha256(_json.dumps(self.runner_argv, separators=(',', ':')).encode('utf-8')).hexdigest()
            spec_sha = hashlib.sha256(_json.dumps({'target': self.target_path, 'tests': self.test_paths, 'scope': self.scope_id}, sort_keys=True).encode('utf-8')).hexdigest()
            cand_snap_sha = hashlib.sha256(f'{orig_snap.digest}:{self.target_path}:{source_sha256(candidate)}'.encode('utf-8')).hexdigest()
            evidence = {
                'test_count': test_count,
                'returncode': rc,
                'measurement_program_sha256': prog_sha,
                'measurement_spec_sha256': spec_sha,
                'snapshot_sha256': cand_snap_sha,
            }
            return VerificationResult(passed, 'TEST_SUITE', source_sha256(candidate), self.scope_id, evidence)
        except Exception as exc:
            return VerificationResult(False, 'TEST_SUITE', source_sha256(candidate), self.scope_id,
                                      {'error': type(exc).__name__})
