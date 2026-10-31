"""Real parser/cache behavior under changed analysis inputs; no fake parsers."""
import json
import shutil
from pathlib import Path

import pytest

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index

FIXTURE = Path(__file__).parent / 'fixtures/tree_sitter_swe'


@pytest.fixture
def project(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / 'src')
    return tmp_path


def build(root):
    return index.run({'source_root': 'src', 'output_path': 'index.json'}, root)


def read(root):
    return json.loads((root / 'index.json').read_bytes())


def test_real_extractor_reconfiguration_invalidates_all_cached_rows(project, monkeypatch):
    build(project)
    source = project / 'src/python/calc.py'
    original = source.read_bytes()
    # This is a real extractor configuration change, not a replacement parser.
    monkeypatch.setitem(kernel.DEFINITION_KINDS, 'function_definition', 'configured_function')
    result = build(project)
    assert result['parsed_file_count'] == 11
    assert result['reused_file_count'] == 0
    row = next(r for r in read(project)['files'] if r['path'] == 'src/python/calc.py')
    assert {d['kind'] for d in row['definitions']} == {'configured_function'}
    assert source.read_bytes() == original


def test_new_test_file_invalidates_explicit_index_for_consumers(project):
    build(project)
    (project / 'src/python/test_added.py').write_text('def test_added(): pass\n')
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_FILE_SET_CHANGED'):
        kernel.read_index(project, project / 'index.json')


def test_lowered_reference_budget_cannot_be_bypassed_by_warm_cache(project, monkeypatch):
    build(project)
    monkeypatch.setattr(kernel, 'MAX_REFERENCES_PER_FILE', 1)
    with pytest.raises(kernel.TreeSitterSWEError, match='REFERENCE_LIMIT_EXCEEDED'):
        build(project)


def test_context_is_a_snapshot_not_an_alias_of_mutable_policy(monkeypatch):
    before = kernel.analysis_context()
    monkeypatch.setitem(kernel.DEFINITION_KINDS, 'function_definition', 'new_kind')
    after = kernel.analysis_context()
    assert before['policy']['definition_kinds']['function_definition'] == 'function'
    assert after['policy']['definition_kinds']['function_definition'] == 'new_kind'
    assert kernel.json_sha256(before) != kernel.json_sha256(after)


def test_context_binds_actual_versions_and_parser_file_content():
    from importlib.metadata import distribution
    context = kernel.analysis_context()
    assert len(context['implementation_sha256']) == 64
    for name in ['tree-sitter', 'tree-sitter-languages']:
        package = context['packages'][name]
        installed = distribution(name)
        assert package['version'] == installed.version
        assert any(path.endswith(('.so', '.pyd', '.dll', '.dylib')) for path in package['files'])
        for path, digest in package['files'].items():
            assert digest == kernel.bytes_sha256(Path(installed.locate_file(path)).read_bytes())


@pytest.mark.parametrize('field', ['implementation_sha256', 'packages', 'policy'])
def test_obsolete_context_is_reparsed_and_consumers_refuse_it(project, field):
    build(project)
    artifact = read(project)
    artifact['analysis_context'][field] = 'obsolete'
    artifact['analysis_context_sha256'] = kernel.json_sha256(artifact['analysis_context'])
    (project / 'index.json').write_text(json.dumps(artifact))
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_ANALYSIS_CONTEXT_STALE'):
        kernel.read_index(project, project / 'index.json')
    result = build(project)
    assert result['parsed_file_count'] == 11
    assert result['reused_file_count'] == 0
    kernel.read_index(project, project / 'index.json')


def test_legacy_index_is_rebuilt_once_not_silently_trusted(project):
    build(project)
    artifact = read(project)
    artifact.pop('analysis_context')
    artifact.pop('analysis_context_sha256')
    (project / 'index.json').write_text(json.dumps(artifact))
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_ANALYSIS_CONTEXT_STALE'):
        kernel.read_index(project, project / 'index.json')
    assert build(project)['parsed_file_count'] == 11
    raw = (project / 'index.json').read_bytes()
    assert build(project)['reused_file_count'] == 11
    assert (project / 'index.json').read_bytes() == raw


@pytest.mark.parametrize('change', ['delete', 'rename', 'add'])
def test_inventory_changes_refuse_old_index_and_rebuild_to_current_files(project, change):
    build(project)
    path = project / 'src/python/calc.py'
    if change == 'delete':
        path.unlink()
    elif change == 'rename':
        path.rename(path.with_name('renamed.py'))
    else:
        path.with_name('added.py').write_text('def added(): pass\n')
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_FILE_SET_CHANGED'):
        kernel.read_index(project, project / 'index.json')
    result = build(project)
    assert result['file_count'] == (10 if change == 'delete' else 12 if change == 'add' else 11)
    assert result['parsed_file_count'] == (0 if change == 'delete' else 1)
    kernel.read_index(project, project / 'index.json')


@pytest.mark.parametrize('mutation', [
    {'definitions': None}, {'references': 'wrong'}, {'imports': [42]},
    {'node_count': True}, {'byte_count': 0}, {'has_syntax_error': 1},
    {'definitions': [{'name': 'bad', 'kind': 'function', 'node_type': 'function_definition',
                      'start_byte': -1, 'end_byte': 2, 'start_line': 1, 'end_line': 1}]},
])
def test_self_hashed_but_malformed_rows_are_refused_and_recomputed(project, mutation):
    build(project)
    artifact = read(project)
    artifact['files'][0].update(mutation)
    artifact['files'][0] = kernel._row_with_hash(artifact['files'][0])
    (project / 'index.json').write_text(json.dumps(artifact))
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_ROW_SHAPE_INVALID'):
        kernel.read_index(project, project / 'index.json')
    result = build(project)
    assert result['parsed_file_count'] == 1
    assert result['reused_file_count'] == 10
    kernel.read_index(project, project / 'index.json')


def test_duplicate_rows_cannot_be_used_by_consumers(project):
    build(project)
    artifact = read(project)
    artifact['files'].append(artifact['files'][0])
    (project / 'index.json').write_text(json.dumps(artifact))
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_DUPLICATE_PATH'):
        kernel.read_index(project, project / 'index.json')


def test_lowered_file_size_limit_refuses_before_publishing_stale_success(project, monkeypatch):
    build(project)
    before = (project / 'index.json').read_bytes()
    monkeypatch.setattr(kernel, 'MAX_FILE_BYTES', 1)
    with pytest.raises(kernel.TreeSitterSWEError, match='SOURCE_FILE_TOO_LARGE'):
        build(project)
    assert (project / 'index.json').read_bytes() == before


def test_real_discovery_prunes_ignored_directories_before_scanning(project):
    import os
    import sys
    ignored = project / 'src/node_modules/package/deep'
    ignored.mkdir(parents=True)
    (ignored / 'ignored.py').write_text('invalid (((\n')
    scanned = []
    previous = sys.getprofile()
    def observe(frame, event, arg):
        if event == 'c_call' and arg is os.scandir:
            scanned.append(str(frame.f_locals.get('top')))
    try:
        sys.setprofile(observe)
        files = kernel.source_files(project / 'src')
    finally:
        sys.setprofile(previous)
    assert len(files) == 11
    assert scanned
    assert all('node_modules' not in path for path in scanned)
    assert files == sorted(files)


@pytest.mark.parametrize('kind', ['file', 'directory'])
def test_nonignored_symlinks_are_still_refused(project, kind):
    target = project / 'src/python/calc.py' if kind == 'file' else project / 'src/python'
    (project / 'src/link').symlink_to(target, target_is_directory=kind == 'directory')
    with pytest.raises(kernel.TreeSitterSWEError, match='SYMLINK_REFUSED'):
        build(project)


def test_single_read_per_source_and_change_only_real_parsing(project):
    import sys
    def run():
        reads = []
        parses = []
        previous = sys.getprofile()
        def observe(frame, event, arg):
            if event != 'call':
                return
            if frame.f_code is Path.read_bytes.__code__ and project / 'src' in frame.f_locals['self'].parents:
                reads.append(frame.f_locals['self'])
            if frame.f_code is kernel.parse_bytes.__code__:
                parses.append(frame.f_locals['language'])
        try:
            sys.setprofile(observe)
            result = build(project)
        finally:
            sys.setprofile(previous)
        return result, reads, parses
    cold, reads, parses = run()
    assert len(reads) == 11
    assert len(parses) == cold['parsed_file_count'] == 11
    warm, reads, parses = run()
    assert len(reads) == 11
    assert parses == []
    assert warm['reused_file_count'] == 11
    path = project / 'src/python/calc.py'
    path.write_bytes(path.read_bytes() + b'# changed\n')
    changed, reads, parses = run()
    assert len(reads) == 11
    assert parses == ['python']
    assert changed['reused_file_count'] == 10


def test_missing_real_substrate_cannot_be_hidden_by_a_warm_index(project):
    import subprocess
    import sys
    build(project)
    before = (project / 'index.json').read_bytes()
    brain = Path(__file__).resolve().parents[2]
    program = '''import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index
try:
    index.run({'source_root':'src','output_path':'index.json'}, Path(sys.argv[2]))
except kernel.TreeSitterSWEError as error:
    assert str(error) == 'TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE', str(error)
    print(str(error))
else:
    raise AssertionError('warm index hid missing parser dependencies')
'''
    process = subprocess.run([sys.executable, '-I', '-S', '-c', program, str(brain), str(project)],
                             cwd=project, capture_output=True, text=True, timeout=15)
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == 'TREE_SITTER_SUBSTRATE_IDENTITY_UNAVAILABLE'
    assert (project / 'index.json').read_bytes() == before


def test_changed_real_parser_dependency_requires_restart_not_stale_reuse(project):
    from importlib.metadata import distribution
    import subprocess
    import sys
    dependencies = project / 'dependencies'
    dependencies.mkdir()
    # Byte-for-byte copies of actual packages/metadata, not interpreter shims.
    # The installed environment is never changed by this test.
    for name in ['tree-sitter', 'tree-sitter-languages']:
        installed = distribution(name)
        roots = {p.parts[0] for p in installed.files
                 if p.parts[0] in {'tree_sitter', 'tree_sitter_languages'}
                 or p.parts[0].endswith('.dist-info')}
        for root in roots:
            shutil.copytree(installed.locate_file(root), dependencies / root,
                            ignore=shutil.ignore_patterns('__pycache__'))
    brain = Path(__file__).resolve().parents[2]
    program = '''import sys
from pathlib import Path
sys.path[:0] = [sys.argv[1], sys.argv[2]]
from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index
root = Path(sys.argv[3])
args = {'source_root':'src','output_path':'index.json'}
assert index.run(args, root)['parsed_file_count'] == 11
before = (root/'index.json').read_bytes()
source = Path(sys.argv[1])/'tree_sitter_languages/__init__.py'
source.write_bytes(source.read_bytes() + b'\\n# changed dependency\\n')
try:
    index.run(args, root)
except kernel.TreeSitterSWEError as error:
    assert str(error) == 'PARSER_DEPENDENCY_CHANGED_RESTART_REQUIRED', str(error)
    assert (root/'index.json').read_bytes() == before
    print(str(error))
else:
    raise AssertionError('loaded parser identity changed without refusal')
'''
    process = subprocess.run([sys.executable, '-I', '-c', program, str(dependencies), str(brain), str(project)],
                             cwd=project, capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == 'PARSER_DEPENDENCY_CHANGED_RESTART_REQUIRED'


@pytest.mark.parametrize('consumer', ['impact', 'patch'])
def test_real_consumers_refuse_missing_new_test_before_candidate_writes(project, consumer):
    from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as impact
    from canonical.runtime.bound_capabilities import code_tree_sitter_patch_verify_v1 as patch
    build(project)
    selection = {'index_path': 'index.json', 'changed_paths': ['src/python/calc.py'],
                 'output_path': 'selection.json'}
    impact.run(selection, project)
    source = project / 'src/python/calc.py'
    before = source.read_bytes()
    (project / 'src/python/test_new.py').write_text('from calc import add\ndef test_new(): assert add(1, 2) == 3\n')
    with pytest.raises(kernel.TreeSitterSWEError, match='INDEX_FILE_SET_CHANGED'):
        if consumer == 'impact':
            impact.run(selection, project)
        else:
            start = before.index(b'-')
            patch.run({'index_path': 'index.json', 'selection_path': 'selection.json',
                       'edits': [{'path': 'src/python/calc.py', 'start_byte': start,
                                  'end_byte': start+1, 'expected': '-', 'replacement': '+'}],
                       'output_path': 'patch.json', 'test_cwd': 'src'}, project)
    assert source.read_bytes() == before
    assert not (project / 'patch.json').exists()
