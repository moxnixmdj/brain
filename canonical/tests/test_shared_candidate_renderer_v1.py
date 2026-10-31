"""Differential byte rendering and real execution: no test-result caching."""
import ast
import hashlib
import sys

import pytest

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch
from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as strict


def reference_render(text, key, replace):
    """Independently express the original parse-per-candidate algorithm."""
    tree = ast.parse(text)
    target = next((n for n in ast.walk(tree) if patch._node_key(n) == key), None)
    if target is None or any(getattr(target, attr, None) is None for attr in
                             ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')):
        return None
    replacement = replace(target)
    ast.fix_missing_locations(replacement)
    raw = text.encode()
    lines = raw.splitlines(keepends=True)
    start = sum(map(len, lines[:target.lineno - 1])) + target.col_offset
    end = sum(map(len, lines[:target.end_lineno - 1])) + target.end_col_offset
    return (raw[:start] + ast.unparse(replacement).encode() + raw[end:]).decode()


@pytest.mark.parametrize('text', [
    'def f(x): return x < 3\n',
    'def f(x):\r\n    return not (x < 3 and x != 2)\r\n',
    "def f(x):\n    label = 'é'; return x + 2 if x > 0 else -1\n",
    'def f(x):\n    s = "😀"; return x > 3\n',
    'class C:\n    async def f(self,x):\n        while x < 3:\n            x = x + 1\n        return x\n',
    'def f(x):\n    return (\n        x > 3\n        and x < 9\n    )\n',
    'def f(x):\n    assert x > 0\n    return {"a": x, "b": False}\n',
])
def test_prepared_renderer_preserves_every_candidate_byte_order_and_descriptor(text):
    tree = ast.parse(text)
    original_tree = ast.dump(tree, include_attributes=True)
    renderer = patch._CandidateRenderer(text, tree)
    expected = []
    actual = []
    for key, desc, replace in patch._candidate_specs(tree, [0, 2, 9], ['a', 'old', 'é']):
        wanted = reference_render(text, key, replace)
        candidate = renderer.render(key, replace)
        assert candidate == wanted
        expected.append((desc, hashlib.sha256(wanted.encode()).hexdigest()))
        actual.append((desc, hashlib.sha256(candidate.encode()).hexdigest()))
        raw = text.encode()
        edit = renderer.edit(key, desc, replace)
        if wanted == text:
            assert edit is None
        else:
            assert raw[:edit['start']] + edit['replacement'] + raw[edit['end']:] == wanted.encode()
    assert len(actual) > 0
    assert actual == expected
    assert ast.dump(tree, include_attributes=True) == original_tree


def test_mutating_replacer_cannot_change_reused_tree_or_later_candidates():
    text = 'def f(x): return x < 3\n'
    tree = ast.parse(text)
    before = ast.dump(tree, include_attributes=True)
    renderer = patch._CandidateRenderer(text, tree)
    key = patch._node_key(next(n for n in ast.walk(tree) if isinstance(n, ast.Compare)))
    def mutate(node):
        node.ops = [ast.LtE()]
        node.comparators[0].value = 9
        return node
    assert renderer.render(key, mutate) == 'def f(x): return x <= 9\n'
    assert renderer.render(key, lambda n: n) == text
    assert ast.dump(tree, include_attributes=True) == before


def test_absent_key_missing_span_and_noop_preserve_compatibility():
    text = 'x = 3\n'
    renderer = patch._CandidateRenderer(text)
    assert renderer.render(('absent',), lambda n: n) is None
    assert renderer.render(patch._node_key(ast.Module(body=[], type_ignores=[])), lambda n: n) is None
    constant = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Constant))
    key = patch._node_key(constant)
    assert renderer.render(key, lambda n: n) == text
    assert renderer.edit(key, {}, lambda n: n) is None
    assert patch._render_candidate(text, key, lambda n: ast.Constant(value=4)) == 'x = 4\n'


def test_prepared_renderer_parses_once_and_never_reuses_a_changed_source_index():
    text = ''.join(f'def f{i}(x): return x < {i}\n' for i in range(50))
    previous = sys.getprofile()
    calls = []
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code is ast.parse.__code__:
            calls.append(frame.f_locals.get('source'))
    try:
        sys.setprofile(observe)
        renderer = patch._CandidateRenderer(text)
        for key, _, replace in patch._candidate_specs(ast.parse(text), [], []):
            renderer.render(key, replace)
    finally:
        sys.setprofile(previous)
    assert calls == [text, text]  # one renderer parse, one explicit specs parse
    changed = text.replace('x < 0', 'x < 99')
    changed_tree = ast.parse(changed)
    new = patch._CandidateRenderer(changed, changed_tree)
    key = patch._node_key(next(n for n in ast.walk(changed_tree) if isinstance(n, ast.Compare)))
    assert 'return x <= 99' in new.render(key, lambda n: ast.Compare(left=n.left, ops=[ast.LtE()], comparators=n.comparators))


@pytest.mark.parametrize('engine', ['single', 'iterative'])
def test_real_bounded_search_parses_source_once_but_executes_every_trial(tmp_path, engine):
    text = ''.join(f'def f{i}(x): return x < {i+3}\n' for i in range(50))
    source = tmp_path / 'm.py'
    source.write_text(text)
    test = tmp_path / 'test_m.py'
    test.write_text('import unittest\nfrom pathlib import Path\nfrom m import f49\n'
                    "with Path('calls.txt').open('a') as stream: stream.write('ran\\n')\n"
                    'class T(unittest.TestCase):\n def test_target(self): self.assertEqual(f49(0),9999)\n'
                    'if __name__=="__main__": unittest.main()\n')
    args = {'source_path': 'm.py', 'source_root': '.', 'test_paths': ['test_m.py'],
            'test_argv': [sys.executable, str(test)], 'output_path': 'report.json',
            'max_candidates': 4, 'max_rounds': 1, 'max_files': 1,
            'max_candidates_per_file': 4, 'max_total_candidates': 4}
    calls = []
    previous = sys.getprofile()
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code is ast.parse.__code__ and frame.f_locals.get('source') == text:
            calls.append(frame.f_locals.get('filename'))
    try:
        sys.setprofile(observe)
        result = (patch if engine == 'single' else strict).run(args, tmp_path)
    finally:
        sys.setprofile(previous)
    assert len(calls) == 1
    assert result['pass'] is False
    # Upstream single search reserves six neighborhood trials independently
    # of the four legacy slots; the iterative engine retains its total cap.
    expected_trials = 10 if engine == 'single' else 4
    assert result['tested_candidate_count'] == expected_trials
    assert len((tmp_path / 'calls.txt').read_text().splitlines()) == expected_trials + 1
    assert source.read_bytes() == text.encode()
    assert result['source_restored'] is True
