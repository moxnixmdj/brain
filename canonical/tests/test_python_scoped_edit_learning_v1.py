"""Real-source regressions for bounded Python edit learning; no harness substitution."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    anti_unify_code_rule, apply_crystallized_code_rule,
    iter_crystallized_code_rule_candidates, skill_identity, verify_rule_on_mutated_twin,
)

FIXTURES = Path(__file__).parent / 'fixtures/historical_repair_projects_v1'
BEFORE = '''def batches(values, width):
    """An iterable consumer; strings and comments are not executable patterns."""
    iterator = iter(values)
    yield from iterator
'''
AFTER = BEFORE.replace('    iterator = iter(values)', '''    if width < 0:
        raise ValueError('negative width')
    if width == 0:
        return

    iterator = iter(values)''')


@pytest.mark.parametrize('case', ['bits_capacity', 'unit_boundary', 'ichunked_zero', 'chunked_even_zero'])
def test_historical_fix_is_reproducible_and_transports_to_renamed_twin(case):
    before = (FIXTURES / case / 'before.py').read_text()
    after = (FIXTURES / case / 'after.py').read_text()
    rule = anti_unify_code_rule(before, after)
    assert rule is not None
    assert after in list(iter_crystallized_code_rule_candidates(before, rule))
    assert verify_rule_on_mutated_twin(before, rule, expected_after_snippet=after)
    if case.endswith('_zero'):
        assert rule['python_scope'] == 'entry'
        assert len(rule['pattern_tokens']) < 32


def test_new_parameter_reference_binds_signature_position_not_training_name():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    target = BEFORE.replace('batches', 'sections').replace('values', 'source').replace('width', 'amount')
    result = apply_crystallized_code_rule(target, rule)
    assert 'if amount < 0:' in result
    assert 'if amount == 0:' in result
    namespace = {}
    exec(result, namespace)
    source = iter([3, 5, 7])
    assert list(namespace['sections'](source, 0)) == []
    assert list(source) == [3, 5, 7]
    assert list(namespace['sections']([3, 5, 7], 2)) == [3, 5, 7]
    with pytest.raises(ValueError, match='negative width'):
        list(namespace['sections']([3], -1))


def test_opaque_strings_and_comments_are_not_candidate_locations():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    target = '''def text(values, width):
    """iterator = iter(values)"""
    # iterator = iter(values)
    payload = "iterator = iter(values)"
    yield payload
'''
    assert list(iter_crystallized_code_rule_candidates(target, rule)) == []


def test_entry_shape_does_not_cross_signature_roles_or_non_generators():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    wrong_roles = BEFORE.replace('(values, width)', '(width, values)')
    assert list(iter_crystallized_code_rule_candidates(wrong_roles, rule)) == []
    ordinary = BEFORE.replace('yield from iterator', 'return list(iterator)')
    assert list(iter_crystallized_code_rule_candidates(ordinary, rule)) == []


def test_scoped_metadata_is_in_content_identity():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    assert skill_identity(rule) == rule['skill_id']
    altered = copy.deepcopy(rule)
    altered['parameter_bindings'][0][2] = 9
    assert skill_identity(altered) != rule['skill_id']
    altered = copy.deepcopy(rule)
    altered['python_scope'] = 'function'
    assert skill_identity(altered) != rule['skill_id']


def test_whole_function_multi_hunk_preserves_unicode_comments_and_outside_bytes():
    before = '# π header\n\ndef calculate(value):\n    """A triple quoted description."""\n    # café\n    return value - 1\n\nTAIL = "untouched"\n'
    after = before.replace('A triple quoted description.', 'A revised triple quoted description.').replace('value - 1', 'value + 1')
    rule = anti_unify_code_rule(before, after)
    # A working legacy rule is deliberately preferred; behavior, not a forced
    # representation label, is the contract here.
    assert apply_crystallized_code_rule(before, rule) == after
    assert verify_rule_on_mutated_twin(before, rule, expected_after_snippet=after)


def test_scoped_twin_requires_the_supplied_edit_not_just_valid_python():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    assert not verify_rule_on_mutated_twin(BEFORE, rule, expected_after_snippet=BEFORE)


def test_unknown_format_is_not_interpreted_as_legacy():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    rule['pattern_format'] = 'future_unknown_format'
    assert apply_crystallized_code_rule(BEFORE, rule) is None


def test_entry_anchor_cannot_match_inside_a_conditional_first_statement():
    rule = anti_unify_code_rule(BEFORE, AFTER)
    target = 'def sections(values, width):\n    if width:\n        iterator = iter(values)\n        yield from iterator\n'
    assert list(iter_crystallized_code_rule_candidates(target, rule)) == []


def test_candidate_verification_has_a_bounded_per_rule_budget(tmp_path):
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    store = VerifiedSkillStore(tmp_path / 'skills.sqlite', seed=False)
    lesson = store.crystallize_code_fix(before_snippet=BEFORE, after_snippet=AFTER, language='python')
    assert lesson['crystallized'] is True
    source = '\n'.join(BEFORE.replace('batches', f'section_{i}') for i in range(20))
    calls = []
    def reject(candidate):
        calls.append(candidate)
        return False
    assert store.recall_and_apply_verified(source_text=source, language='python', verifier=reject) is None
    assert len(calls) == 16
    # This boolean oracle tests enumeration/budgeting only, not behavioral assurance.


def test_invalidation_stops_remaining_locations_of_the_same_rule(tmp_path):
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    store = VerifiedSkillStore(tmp_path / 'skills.sqlite', seed=False)
    lesson = store.crystallize_code_fix(before_snippet=BEFORE, after_snippet=AFTER, language='python')
    assert lesson['crystallized'] is True
    source = BEFORE + '\n' + BEFORE.replace('batches', 'another')
    calls = []
    def invalidate(candidate):
        calls.append(candidate)
        assert VerifiedSkillStore(store.db_path, seed=False).invalidate(lesson['skill_id'], 'counterexample')
        return True
    assert store.recall_and_apply_verified(source_text=source, language='python', verifier=invalidate) is None
    assert len(calls) == 1


def test_crlf_insertion_preserves_actual_line_endings():
    before = BEFORE.replace('\n', '\r\n')
    after = AFTER.replace('\n', '\r\n')
    rule = anti_unify_code_rule(before, after)
    assert after in list(iter_crystallized_code_rule_candidates(before, rule))
    assert verify_rule_on_mutated_twin(before, rule, expected_after_snippet=after)
