"""The same evidence boundary exercised through three actual adapter entrypoints."""
import json
import os
from pathlib import Path
import pytest
from canonical.runtime.bound_capabilities import python_review_diff_static_triage as lint
from canonical.runtime.bound_capabilities import python_review_diff_type_gate as types
from canonical.runtime.bound_capabilities import python_review_diff_security_gate as security
from canonical.runtime.write_authority_v1 import WriteAuthorityViolation

ADAPTERS = [lint, types, security]


def project(root):
    (root/'wt').mkdir()
    source = root/'wt/m.py'
    source.write_text('value = 2\n')
    diff = root/'change.diff'
    diff.write_text('--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n')
    return source, diff


def args(root, output='report.json', real_tool=False):
    out = {'diff_path': 'change.diff', 'worktree_path': 'wt', 'output_path': output, 'timeout_s': 10}
    if not real_tool:
        out['python_executable'] = str(root/'nonexistent-interpreter')
    return out


@pytest.mark.parametrize('adapter', ADAPTERS, ids=['ruff','mypy','bandit'])
@pytest.mark.parametrize('kind', ['source','diff','source-hardlink','diff-hardlink','source-symlink','worktree-data','new-source'])
def test_report_identity_refuses_before_any_tool(adapter, kind, tmp_path):
    source, diff = project(tmp_path)
    originals = source.read_bytes(), diff.read_bytes(), source.stat().st_mode
    if kind == 'source':
        output = 'wt/m.py'
    elif kind == 'diff':
        output = 'change.diff'
    elif kind in ('source-hardlink','diff-hardlink'):
        os.link(source if kind == 'source-hardlink' else diff, tmp_path/'alias.json')
        output = 'alias.json'
    elif kind == 'source-symlink':
        (tmp_path/'alias.json').symlink_to(source)
        output = 'alias.json'
    elif kind == 'worktree-data':
        (tmp_path/'wt/config.json').write_text('{"setting": 1}\n')
        output = 'wt/config.json'
    else:
        output = 'new.py'
    with pytest.raises(WriteAuthorityViolation, match='^REPORT_'):
        adapter.run(args(tmp_path, output), tmp_path)
    assert (source.read_bytes(), diff.read_bytes(), source.stat().st_mode) == originals
    if kind == 'worktree-data':
        assert (tmp_path/'wt/config.json').read_text() == '{"setting": 1}\n'
    if kind == 'new-source':
        assert not (tmp_path/'new.py').exists()


@pytest.mark.parametrize('adapter', ADAPTERS, ids=['ruff','mypy','bandit'])
@pytest.mark.parametrize('kind', ['parent','symlink'])
def test_review_target_escape_refuses_before_any_tool(adapter, kind, tmp_path):
    source, diff = project(tmp_path)
    outside = tmp_path/'outside.py'
    outside.write_text('value = 2\n')
    if kind == 'parent':
        diff.write_text(diff.read_text().replace('a/m.py','a/../outside.py').replace('b/m.py','b/../outside.py'))
    else:
        source.unlink()
        source.symlink_to(outside)
    with pytest.raises(SystemExit, match='TOUCHED_FILE_OUTSIDE_WORKTREE'):
        adapter.run(args(tmp_path), tmp_path)
    assert outside.read_text() == 'value = 2\n'
    assert not (tmp_path/'report.json').exists()


@pytest.mark.parametrize('adapter', ADAPTERS, ids=['ruff','mypy','bandit'])
def test_fresh_report_replay_and_source_preservation(adapter, tmp_path):
    source, diff = project(tmp_path)
    originals = source.read_bytes(), diff.read_bytes()
    first = adapter.run(args(tmp_path, real_tool=True), tmp_path)
    payload = (tmp_path/'report.json').read_bytes()
    second = adapter.run(args(tmp_path, real_tool=True), tmp_path)
    assert first == second
    assert first['output_verified'] is True
    assert (tmp_path/'report.json').read_bytes() == payload
    assert json.loads(payload)['files_touched'] == 1
    assert (source.read_bytes(), diff.read_bytes()) == originals
