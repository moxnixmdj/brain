"""Metered frozen qualification; uses existing real-project worker/oracle helpers.

This is an experiment, not a capability registry, third-party certificate or a
runtime planner. Historical provenance is reused locally; development/model costs
outside the run are explicitly not included in its end-to-end qualification cost.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import resource
import tempfile
import time

from canonical.tests.historical_repair_curriculum_v1 import FIXTURES, build_case, execute

FROZEN = Path(__file__).parent / 'fixtures/scoped_python_learning_curriculum_v1.json'


def run_campaign():
    started = time.monotonic()
    repo_root = Path(__file__).resolve().parents[2]
    producers = ['canonical/swe_kernel/verified_skill_crystallizer_v1.py',
                 'canonical/swe_kernel/python_scoped_edit_rule_v1.py',
                 'canonical/swe_kernel/skill_verification_contract_v1.py',
                 'canonical/swe_kernel/retained_repair_session_v1.py',
                 'canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py',
                 'canonical/runtime/bound_capabilities/python_provenance_guided_coupled_repair_v1.py']
    hashes = {p: hashlib.sha256((repo_root / p).read_bytes()).hexdigest() for p in producers}
    phases = []
    def usage():
        own = resource.getrusage(resource.RUSAGE_SELF)
        child = resource.getrusage(resource.RUSAGE_CHILDREN)
        return own.ru_utime + own.ru_stime + child.ru_utime + child.ru_stime
    initial_cpu = usage()
    def measured(label, fn):
        wall, cpu = time.monotonic(), usage()
        result = fn()
        phases.append({'phase': label, 'wall_s': time.monotonic() - wall,
                       'self_and_waited_children_cpu_s': usage() - cpu})
        return result
    def discover():
        frozen = json.loads(FROZEN.read_text())
        provenance = FIXTURES / 'PROVENANCE.json'
        assert hashlib.sha256(provenance.read_bytes()).hexdigest() == frozen['historical_provenance_sha256']
        manifest = json.loads(provenance.read_text())
        for row in manifest['files']:
            assert hashlib.sha256((FIXTURES / row['local_file']).read_bytes()).hexdigest() == row['sha256']
        return frozen
    frozen = measured('discover_and_verify_reused_local_provenance', discover)
    rows, receipts = [], []
    with tempfile.TemporaryDirectory(prefix='brain_scoped_campaign_') as td:
        root = Path(td)
        for teaching_id, held_id in frozen['pairs']:
            for trial in range(frozen['repetitions']):
                repo = root / f'{teaching_id}_{trial}'
                teacher = measured('build_teacher', lambda: build_case(repo, teaching_id, 'teacher'))
                protected_teacher = teacher['target'].read_bytes()
                taught = measured('teach', lambda: execute('teach', repo, teacher))
                assert teacher['target'].read_bytes() == protected_teacher
                assert taught['result']['crystallized'] is True
                cases = {arm: measured('build_' + arm, lambda arm=arm: build_case(repo, held_id, arm))
                         for arm in ('baseline', 'learning_enabled')}
                cases['baseline']['args']['retained_learning']['enabled'] = False
                protected = {p: p.read_bytes() for case in cases.values() for p in case['project'].glob('test_*.py')}
                originals = {arm: case['target'].read_bytes() for arm, case in cases.items()}
                order = ('baseline', 'learning_enabled') if trial == 0 else ('learning_enabled', 'baseline')
                runs, audits = {}, {}
                for arm in order:
                    case = cases[arm]
                    runs[arm] = measured('apply_' + arm, lambda: execute('apply', repo, case))
                    audits[arm] = measured('audit_' + arm, lambda: execute('audit', repo, case))
                    expected = held_id == 'unit_boundary' or arm == 'learning_enabled'
                    assert runs[arm]['result']['pass'] is expected
                    assert (audits[arm]['result']['returncode'] == 0) is expected
                    if not expected:
                        assert case['target'].read_bytes() == originals[arm]
                    if held_id == 'chunked_even_zero' and arm == 'learning_enabled':
                        assert runs[arm]['result']['retained_learning']['hit'] is True
                        assert runs[arm]['result']['retained_learning']['oracle_calls'] >= 2
                        assert runs[arm]['result']['repair_search_invocations'] == 0
                assert all(p.read_bytes() == value for p, value in protected.items())
                rows.append({'teaching_issue': teaching_id, 'heldout_issue': held_id, 'trial': trial,
                             'order': list(order), 'teaching': taught, 'runs': runs, 'audits': audits})
                receipts += [taught, *runs.values(), *audits.values()]
        # Real differing pinned revision declarations: refuse memory before its oracle.
        repo = root / 'version_negative'
        teacher = measured('build_version_teacher', lambda: build_case(repo, 'ichunked_zero', 'teacher'))
        manifest = json.loads((FIXTURES / 'PROVENANCE.json').read_text())
        versions = {r['id']: r['before_commit'] for r in manifest['cases']}
        cfg = teacher['args']['retained_learning']
        for key in ('contract', 'context'):
            cfg[key]['dependencies']['source_revision'] = versions['ichunked_zero']
        taught = measured('teach_version_negative', lambda: execute('teach', repo, teacher))
        case = measured('build_version_negative', lambda: build_case(repo, 'chunked_even_zero', 'heldout'))
        cfg = case['args']['retained_learning']
        cfg['contract']['dependencies']['source_revision'] = versions['ichunked_zero']
        cfg['context']['dependencies']['source_revision'] = versions['chunked_even_zero']
        original = case['target'].read_bytes()
        refused = measured('apply_version_negative', lambda: execute('apply', repo, case))
        assert refused['result']['retained_learning']['applicable'] is False
        assert refused['result']['retained_learning']['oracle_calls'] == 0
        assert refused['result']['pass'] is False
        assert case['target'].read_bytes() == original
        receipts += [taught, refused]
        version_negative = {'teaching': taught, 'run': refused,
                            'automatic_environment_attestation': False}
        # The original misleading-match control remains behaviorally enforced.
        repo = root / 'similarity_negative'
        teacher = measured('build_similarity_teacher', lambda: build_case(repo, 'bits_capacity', 'teacher'))
        taught = measured('teach_similarity_negative', lambda: execute('teach', repo, teacher))
        case = measured('build_similarity_negative', lambda: build_case(repo, 'unit_boundary', 'heldout'))
        decoy = '\n\ndef inclusive(value, width):\n    if value > 2 ** width:\n        raise ValueError("above threshold")\n    return value\n'
        case['target'].write_text(case['target'].read_text() + decoy)
        consumer = case['project'] / 'test_consumer.py'
        consumer.write_text(consumer.read_text() + '\n\ndef test_inclusive():\n    from boltons.strutils import inclusive\n    assert inclusive(8, 3) == 8\n')
        run = measured('apply_similarity_negative', lambda: execute('apply', repo, case))
        audit = measured('audit_similarity_negative', lambda: execute('audit', repo, case))
        assert run['result']['pass'] is True
        assert run['result']['retained_learning']['hit'] is False
        assert case['target'].read_text().endswith(decoy)
        assert audit['result']['returncode'] == 0
        similarity_negative = {'teaching': taught, 'run': run, 'audit': audit}
        receipts += [taught, run, audit]
    return {'schema': 'SCOPED_PYTHON_LEARNING_CAMPAIGN_V1', 'frozen_curriculum': frozen,
            'frozen_curriculum_sha256': hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
            'producer_sha256_at_start': hashes,
            'paired_runs': rows, 'version_negative': version_negative,
            'similarity_negative': similarity_negative, 'phases': phases,
            'end_to_end_qualification_wall_s': time.monotonic() - started,
            'end_to_end_self_and_waited_children_cpu_s': usage() - initial_cpu,
            'worker_count': len(receipts),
            'worker_observed_subprocess_launches': sum(r['subprocess_calls'] for r in receipts),
            'development_and_model_assisted_reasoning_cost_included': False,
            'discovery_scope': 'Existing immutable local fixtures and maintained code; no new network acquisition. Historical acquisition cost is sunk and not reconstructed as zero.',
            'independent_certification': False, 'capability_credit_delta': 0,
            'full_upstream_repository_coverage': False,
            'multi_source_file_patch_qualification': False}


if __name__ == '__main__':
    import sys
    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(run_campaign(), indent=2, sort_keys=True) + '\n')
    print(destination)
