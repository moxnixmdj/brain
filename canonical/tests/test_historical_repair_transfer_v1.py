"""Current-tree historical repair probes, including failures and required refusals.

No process/import/filesystem substitution; no authoritative capability promotion.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
from canonical.tests.historical_repair_curriculum_v1 import (
    FIXTURES, FAMILIES, build_case, execute,
)


def test_exact_historical_source_and_upstream_tests_are_pinned():
    manifest = json.loads((FIXTURES / 'PROVENANCE.json').read_text())
    assert len(manifest['cases']) == 4
    for row in manifest['files']:
        data = (FIXTURES / row['local_file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert len(row['commit']) == 40 and row['commit'] in row['source_url']
        assert len(row['git_blob_sha']) == 40


@pytest.mark.parametrize('case_id', [c for pair in FAMILIES.values() for c in pair])
def test_real_historical_bug_fails_and_upstream_fix_passes_unchanged_tests(tmp_path, case_id):
    case = build_case(tmp_path, case_id, 'project')
    before = case['target'].read_bytes()
    protected = {p: p.read_bytes() for p in case['project'].glob('test_*.py')}
    assert execute('corpus', tmp_path, case)['result']['returncode'] != 0
    assert execute('audit', tmp_path, case)['result']['returncode'] != 0
    assert case['target'].read_bytes() == before
    case['target'].write_bytes((FIXTURES / case_id / 'after.py').read_bytes())
    assert execute('corpus', tmp_path, case)['result']['returncode'] == 0
    assert execute('audit', tmp_path, case)['result']['returncode'] == 0
    assert all(p.read_bytes() == data for p, data in protected.items())
    manifest = json.loads((FIXTURES / 'PROVENANCE.json').read_text())
    spec = next(row for row in manifest['cases'] if row['id'] == case_id)
    source = (FIXTURES / case_id / 'upstream_tests.txt').read_text()
    node = next(n for n in ast.parse(source).body if getattr(n, 'name', None) == spec['selected_test'])
    assert ast.get_source_segment(source, node) in case['test'].read_text()


def test_comparison_reserve_preserves_old_slots_and_pair_inventory(tmp_path):
    case = build_case(tmp_path, 'unit_boundary', 'project')
    tree = ast.parse(case['target'].read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'bytes2human')
    row = {'path': case['target'], 'symbols': [
        {'lineno': fn.lineno, 'end_lineno': fn.end_lineno, 'score': 1}]}
    tests = [tmp_path / p for p in case['args']['test_paths']]
    pool = apply._REPAIR._COUPLED._pool
    old = pool(row, tests, 24)
    expanded = pool(row, tests, 24, comparison_reserve=4)
    retained = [e for e in expanded if e['family'] != 'comparison_reserve']
    extra = [e for e in expanded if e['family'] == 'comparison_reserve']
    assert retained == old  # every old edit, byte span, budget slot and order
    items = apply._REPAIR._items
    old_pairs = items([row], tests, 24)
    extended_items = items([row], tests, 24, comparison_reserve=4)
    assert [it for it in extended_items if it[1]['family'] != 'comparison_reserve'] == old_pairs
    assert 1 <= len(extra) <= 4
    assert not any(e['mutation']['kind'] == 'COMPARE_SWAP' for e in old)
    assert all(e['mutation']['kind'] == 'COMPARE_SWAP' for e in extra)
    assert len({(e['start'], e['end'], e['replacement']) for e in expanded}) == len(expanded)
    # The old default path has no new reserve and is not silently reordered.
    assert pool(row, tests, 24, comparison_reserve=0) == old


@pytest.mark.parametrize('trial', range(2))
@pytest.mark.parametrize('family', tuple(FAMILIES))
def test_historical_cross_issue_transfer_against_the_same_capable_solver(tmp_path, family, trial, record_property):
    teacher_id, held_id = FAMILIES[family]
    teaching = build_case(tmp_path, teacher_id, 'teaching')
    original_teacher = teaching['target'].read_bytes()
    taught = execute('teach', tmp_path, teaching)
    assert teaching['target'].read_bytes() == original_teacher
    if family == 'boundary':
        assert taught['result']['crystallized'] is True
    else:
        # A real insertion-only lesson remains outside the current token/twin
        # representation. Record refusal, never substitute expert held-out code.
        assert taught['result']['crystallized'] is False
        assert taught['result']['reason'] == 'FAILED_MUTATED_TWIN_VERIFICATION'
    cold_case = build_case(tmp_path, held_id, 'baseline')
    cold_case['args']['retained_learning']['enabled'] = False
    warm_case = build_case(tmp_path, held_id, 'learning_enabled')
    cases = {'baseline': cold_case, 'learning_enabled': warm_case}
    protected = {p: p.read_bytes() for c in cases.values() for p in c['project'].glob('test_*.py')}
    originals = {arm: c['target'].read_bytes() for arm, c in cases.items()}
    runs = {arm: execute('apply', tmp_path, c) for arm, c in cases.items()}
    audits = {arm: execute('audit', tmp_path, c) for arm, c in cases.items()}
    assert len({taught['pid'], *(r['pid'] for r in runs.values())}) == 3
    expected_success = family == 'boundary'
    for arm, run in runs.items():
        result = run['result']
        assert result['repair_search_invocations'] == 1
        assert result['pass'] is expected_success
        assert result['applied'] is expected_success
        if expected_success:
            assert audits[arm]['result']['returncode'] == 0
            target = cases[arm]['target']
            path = cases[arm]['args']['retained_learning']['target_path']
            assert result['applied_source_sha256'][path] == hashlib.sha256(target.read_bytes()).hexdigest()
            assert result['files_written'] == [path]
        else:
            assert audits[arm]['result']['returncode'] != 0
            assert cases[arm]['target'].read_bytes() == originals[arm]
            assert result['files_written'] == []
    assert runs['learning_enabled']['result']['retained_learning']['hit'] is False
    assert all(p.read_bytes() == data for p, data in protected.items())
    # Upstream regression consumer and extra audit are separate actual executions.
    record_property('historical_repair_run', json.dumps({
        'family': family, 'trial': trial, 'teaching_issue': teacher_id, 'heldout_issue': held_id,
        'teaching': taught, 'runs': runs, 'audits': audits,
        'baseline_has_same_search_and_trace_fallback': True,
        'expert_heldout_source_supplied_to_solver': False,
        'upstream_test_bodies_unchanged': True,
        'independent_certification': False,
        'scope': 'Pinned real historical bugs in exact source subsets, unchanged selected upstream tests, authored consumers/audits; not complete repositories or multi-source-patch qualification'}))


def test_incompatible_declared_environment_refuses_memory_but_keeps_search(tmp_path, record_property):
    teaching = build_case(tmp_path, 'bits_capacity', 'teaching')
    manifest = json.loads((FIXTURES / 'PROVENANCE.json').read_text())
    revisions = {c['id']: c['before_commit'] for c in manifest['cases']}
    old_revision = revisions['bits_capacity']
    new_revision = revisions['unit_boundary']
    assert old_revision != new_revision
    for key in ('contract', 'context'):
        teaching['args']['retained_learning'][key]['dependencies']['boltons_source_revision'] = old_revision
    taught = execute('teach', tmp_path, teaching)
    assert taught['result']['crystallized'] is True
    case = build_case(tmp_path, 'unit_boundary', 'changed_environment')
    config = case['args']['retained_learning']
    config['contract']['dependencies']['boltons_source_revision'] = old_revision
    config['context']['dependencies']['boltons_source_revision'] = new_revision
    run = execute('apply', tmp_path, case)
    result = run['result']
    assert result['retained_learning']['applicable'] is False
    assert result['retained_learning']['hit'] is False
    assert result['retained_learning']['oracle_calls'] == 0
    assert result['repair_search_invocations'] == 1
    assert result['pass'] is True
    audit = execute('audit', tmp_path, case)
    assert audit['result']['returncode'] == 0
    # Declarations reflect the two actual pinned source revisions, but checking
    # trusted context is still not automatic environment/version attestation.
    record_property('historical_negative_run', json.dumps({
        'negative_kind': 'declared_pinned_source_revision_mismatch',
        'teaching': taught, 'run': run, 'audit': audit,
        'teaching_revision': old_revision, 'heldout_revision': new_revision,
        'automatic_environment_attestation': False}))


def test_misleading_syntactic_similarity_is_rejected_by_real_project_oracle(tmp_path, record_property):
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        anti_unify_code_rule, apply_crystallized_code_rule,
    )
    teaching = build_case(tmp_path, 'bits_capacity', 'teaching')
    taught = execute('teach', tmp_path, teaching)
    assert taught['result']['crystallized'] is True
    case = build_case(tmp_path, 'unit_boundary', 'misleading_similarity')
    # Explicitly authored negative control; not misrepresented as upstream code.
    decoy = '\n\ndef render_threshold_counterexample(value, width):\n    if value > 2 ** width:\n        raise ValueError("above inclusive threshold")\n    return value, width\n'
    case['target'].write_text(case['target'].read_text() + decoy)
    consumer = case['project'] / 'test_consumer.py'
    consumer.write_text(consumer.read_text() + '\n\ndef test_misleading_similarity():\n    from boltons.strutils import render_threshold_counterexample\n    assert render_threshold_counterexample(8, 3) == (8, 3)\n')
    rule = anti_unify_code_rule(
        (FIXTURES / 'bits_capacity/before.py').read_text(),
        (FIXTURES / 'bits_capacity/after.py').read_text(), language='python')
    preview = apply_crystallized_code_rule(case['target'].read_text(), rule)
    assert preview is not None
    assert 'if value >= 2 ** width:' in preview
    tests = {p: p.read_bytes() for p in case['project'].glob('test_*.py')}
    run = execute('apply', tmp_path, case)
    result = run['result']
    assert result['retained_learning']['applicable'] is True
    assert result['retained_learning']['hit'] is False
    assert result['retained_learning']['oracle_calls'] >= 1
    assert result['repair_search_invocations'] == 1
    assert result['pass'] is True
    assert case['target'].read_text().endswith(decoy)
    assert execute('audit', tmp_path, case)['result']['returncode'] == 0
    assert all(p.read_bytes() == content for p, content in tests.items())
    record_property('historical_negative_run', json.dumps({
        'negative_kind': 'authored_misleading_similarity', 'teaching': taught, 'run': run,
        'candidate_syntactically_available_but_not_accepted': True,
        'correct_inclusive_decoy_preserved': True}))


def test_successful_historical_search_is_retained_for_same_issue_replay_not_transfer(tmp_path, record_property):
    first_case = build_case(tmp_path, 'unit_boundary', 'first_encounter')
    first = execute('apply', tmp_path, first_case)
    assert first['result']['pass'] is True
    assert first['result']['repair_search_invocations'] == 1
    assert first['result']['retained_learning']['teaching']['crystallized'] is True
    output = tmp_path / first_case['args']['output_path']
    report = json.loads(output.with_name('.apply_repair_' + output.name).read_text())
    guidance = report['guidance']
    assert guidance['guided_candidate_item_count'] == guidance['guided_base_candidate_item_count'] + guidance['comparison_reserve_item_count']
    assert guidance['guided_single_candidate_item_count'] == guidance['guided_candidate_item_count']
    assert guidance['candidate_item_reduction'] == guidance['control_candidate_item_count'] - guidance['guided_single_candidate_item_count']
    replay_case = build_case(tmp_path, 'unit_boundary', 'same_issue_replay')
    replay = execute('apply', tmp_path, replay_case)
    result = replay['result']
    assert first['pid'] != replay['pid']
    assert result['pass'] is True and result['applied'] is True
    assert result['retained_learning']['hit'] is True
    assert result['repair_search_invocations'] == 0
    audit = execute('audit', tmp_path, replay_case)
    assert audit['result']['returncode'] == 0
    record_property('historical_replay_run', json.dumps({
        'first_encounter': first, 'same_issue_replay': replay, 'audit': audit,
        'expert_solution_supplied': False, 'counts_as_unseen_issue_transfer': False}))
