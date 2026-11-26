"""Pre-grader diagnostic for the pinned CLI-library study, not a general shell agent.

Separate namespace jobs for (1) source-only recall, and (2) each receiver-native
help request. Evaluator not imported. The output of (2) is a scoped observation,
never a label saying which behavior the user wants. See RECEIVER_CONTRAST_PROTOCOL.
"""
from __future__ import annotations

import argparse
import ast
import base64
import configparser
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib

ARMS = ('empty', 'raw_traces', 'generalized')
HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(p, obj):
    p.write_text(json.dumps(obj, indent=2) + '\n')


def job(room, mode, deadline):
    from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined
    r = run_confined({'input_dir': str(room), 'argv': ['/usr/bin/python3', '-I', '-B', '/input/tools/driver.py', mode],
                      'expose_runtime_devices': True,
                      'limits': {'wallclock_s': deadline, 'cpu_seconds': deadline, 'memory_mb': 512,
                                 'scratch_mb': 32, 'nofile': 64, 'max_file_mb': 4, 'pids': 32}})
    raw = r.pop('broker_payload')
    return r, json.loads(raw) if raw and not r['returncode'] else None


def py_sources(src, dest):
    # No symlinks, hidden dirs, task tests, caches, metadata or scripts from a grader.
    for f in sorted(src.rglob('*.py')):
        rel = f.relative_to(src)
        if f.resolve() != f or not f.is_file() or any(n.startswith('.') or n in ('tests', 'test') for n in rel.parts):
            continue
        if rel.name == 'conftest.py' or rel.name.startswith('test_') or rel.name.endswith('_test.py'):
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, out)


def recall_in_room():
    sys.path.insert(0, '/input')
    from canonical.tools.subtree_transfer_probe_v1 import probe
    scratch = Path('/work/frozen')
    r = probe(Path('/input/product'), Path('/input/store.json'), scratch)
    blobs = {a: base64.b64encode((scratch / a / c['path']).read_bytes()).decode()
             for a in ARMS if (c := r['arms'][a]['first_candidate'])}
    return {'record': r, 'candidates': blobs}


def freeze(product, store, out):
    with tempfile.TemporaryDirectory() as td:
        room = Path(td)
        py_sources(product, room / 'product')
        for name in ('tools/subtree_transfer_probe_v1', 'swe_kernel/__init__', 'swe_kernel/petri_cow_splicing_engine_v1',
                     'swe_kernel/effect_contract_composition_v1', 'swe_kernel/consistency_vs_equivalence_v1',
                     'swe_kernel/incremental_semantic_graph_v1'):
            p = Path('canonical', name + '.py')
            (room / p.parent).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p, room / p)
        (room / 'tools').mkdir()
        shutil.copyfile(HERE, room / 'tools/driver.py')
        shutil.copyfile(store, room / 'store.json')
        launch, r = job(room, '--recall', 60)
    if not r:
        dump(out / 'recall_error.json', launch)
        raise RuntimeError('incomplete recall')
    record = r['record']
    for a, encoded in r['candidates'].items():
        c = record['arms'][a]['first_candidate']
        path = Path(c['path'])
        data = base64.b64decode(encoded, validate=True)
        if path.is_absolute() or '..' in path.parts or path.suffix != '.py' or sha(data) != c['sha256']:
            raise ValueError('invalid frozen candidate')
        dest = out / 'frozen' / a / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    dump(out / 'probe.json', {'targets': [record], 'launcher': launch, 'input_store_sha256': sha(store.read_bytes())})
    return record


def example_programs(examples):
    """Declarative local entry points; never execute setup.py to discover commands."""
    programs, errors = [], []
    for f in sorted(examples.rglob('*')):
        rel = f.relative_to(examples)
        if not f.is_file() or f.resolve() != f or any(p.startswith('.') or p in ('tests', 'test') for p in rel.parts):
            continue
        if f.name.startswith('test_') or f.name.endswith('_test.py') or f.name == 'conftest.py':
            continue
        scripts = {}
        try:
            if f.name == 'pyproject.toml':
                scripts = tomllib.loads(f.read_text()).get('project', {}).get('scripts', {})
            elif f.name == 'setup.cfg':
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.read(f)
                scripts = dict(s.strip().split('=', 1) for s in cfg.get('options.entry_points', 'console_scripts', fallback='').splitlines() if '=' in s)
            elif f.suffix == '.py':
                tree = ast.parse(f.read_bytes())
                if f.name == 'setup.py':
                    for n in ast.walk(tree):
                        if isinstance(n, ast.keyword) and n.arg == 'entry_points' and isinstance(n.value, ast.Dict):
                            for k, v in zip(n.value.keys, n.value.values):
                                if isinstance(k, ast.Constant) and k.value == 'console_scripts':
                                    scripts.update(s.split('=', 1) for s in ast.literal_eval(v))
                elif any(isinstance(n, ast.If) and ast.unparse(n.test) in ("__name__ == '__main__'", "'__main__' == __name__") for n in tree.body):
                    programs.append({'path': str(rel), 'name': f.name, 'entry': None})
        except (OSError, TypeError, ValueError, SyntaxError, configparser.Error) as e:
            errors.append([str(rel), type(e).__name__])
            continue
        for name, entry in scripts.items():
            if isinstance(entry, str) and re.fullmatch(r'(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*:[A-Za-z_]\w*', entry.strip()):
                programs.append({'path': str(rel), 'name': name.strip(), 'entry': entry.strip()})
    return sorted(programs, key=lambda x: (x['path'], x['name'])), errors


def changed_functions(old, new):
    def defs(text):
        def walk(body, scope):
            for n in body:
                if isinstance(n, ast.ClassDef):
                    yield from walk(n.body, scope + n.name + '.')
                elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield scope + n.name, ast.dump(n)
        return dict(walk(ast.parse(text).body, ''))
    a, b = defs(old), defs(new)
    return sorted(k for k in a.keys() & b.keys() if a[k] != b[k])



def related_examples(examples, programs, subjects):
    # Names come from the actual AST delta, not a task, known test or package vocabulary.
    wanted = {part.casefold() for subject in subjects for part in subject.split('::')[-1].split('.')}
    related = {}
    for program in programs:
        path = program['path']
        matches = set()
        for f in sorted((examples / path).parent.rglob('*.py')):
            if f.resolve() != f or f.name.startswith('test_') or f.name.endswith('_test.py') or f.name == 'conftest.py' or any(
                    n.startswith('.') or n in ('test', 'tests') for n in f.relative_to(examples).parts):
                continue
            try:
                tree = ast.parse(f.read_bytes())
            except (OSError, SyntaxError, ValueError):
                continue
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names = {n.attr.casefold() if isinstance(n, ast.Attribute) else n.id.casefold()
                             for d in fn.decorator_list for n in ast.walk(d) if isinstance(n, (ast.Attribute, ast.Name))}
                    if names & wanted:
                        matches.add(fn.name.replace('_', '-'))
        related[path] = sorted(matches)
    return sorted(programs, key=lambda p: (-len(related[p['path']]), p['path'], p['name'])), related


def advertised(output):
    lines = output.decode(errors='replace').splitlines()
    start = next((i for i, s in enumerate(lines) if s == 'Commands:'), len(lines))
    names = []
    for line in lines[start + 1:]:
        if not line.startswith(' '):
            break
        m = re.fullmatch(r'  ([A-Za-z][A-Za-z0-9_-]*)(?:  .*| *)', line)
        if m:
            names.append(m[1])
    return names

def command():
    s = json.loads(Path('/input/request.json').read_bytes())
    p = s['program']
    path = Path('/input/examples', p['path'])
    sys.path[:0] = ['/input/pkg', str(path.parent), str(path.parent / 'src')]
    hits = dict.fromkeys(s['subjects'], 0)
    filenames = set(k.split('::', 1)[0] for k in hits)
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code.co_filename in filenames:
            key = frame.f_code.co_filename + '::' + frame.f_code.co_qualname
            if key in hits:
                hits[key] += 1
    local = False
    sys.argv[:] = [p['name'], *([p['child']] if 'child' in p else []), '--help']
    try:
        pkg = importlib.import_module(s['package'])
        local = Path(pkg.__file__).is_relative_to('/input/pkg')
        if not local:
            raise ImportError('package is not staged source')
        sys.setprofile(profile)
        if p['entry']:
            module, name = p['entry'].split(':')
            raise SystemExit(getattr(importlib.import_module(module), name)())
        runpy.run_path(str(path), run_name='__main__')
    finally:
        sys.setprofile(None)
        dump(Path('/tmp/observation.json'), {'local_product': local, 'calls': hits})


def observe_in_room():
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C.UTF-8', 'HOME': '/tmp', 'TERM': 'dumb', 'COLUMNS': '80'}
    try:
        p = subprocess.run(['/usr/bin/python3', '-I', '-B', '/input/tools/driver.py', '--command'],
                           env=env, cwd='/work', timeout=5, capture_output=True, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT'}
    path = Path('/tmp/observation.json')
    metadata = json.loads(path.read_bytes()) if path.exists() else {}
    return {'status': 'OBSERVED' if metadata.get('local_product') else 'INCOMPLETE', 'exit': p.returncode,
            'stdout_sha256': sha(p.stdout), 'stdout_bytes': len(p.stdout), 'advertised': advertised(p.stdout), 'stderr_sha256': sha(p.stderr),
            'stderr_bytes': len(p.stderr), 'diagnostic': p.stderr.decode(errors='replace')[-240:] if p.returncode else '', **metadata}



@contextmanager
def staged_room(product, examples, candidate):
    with tempfile.TemporaryDirectory() as td:
        room = Path(td)
        (room / 'tools').mkdir()
        shutil.copyfile(HERE, room / 'tools/driver.py')
        py_sources(product, room / 'pkg' / product.name)
        py_sources(examples, room / 'examples')
        if candidate:
            rel, data = candidate
            dest = room / 'pkg' / product.name / rel
            if Path(rel).is_absolute() or '..' in Path(rel).parts or not dest.is_file():
                raise ValueError('not a staged product file')
            dest.write_bytes(data)
        yield room


def intervention(out, arm, record):
    c = record['arms'][arm]['first_candidate']
    if not c:
        return None
    rel = Path(c['path'])
    if rel.is_absolute() or '..' in rel.parts or rel.suffix != '.py':
        raise ValueError('invalid frozen path')
    data = (out / 'frozen' / arm / rel).read_bytes()
    if sha(data) != c['sha256']:
        raise ValueError('changed frozen intervention')
    return rel, data

def measure(checkout, rel, store, out, *, directed=False):
    started = time.monotonic()
    out.mkdir(exist_ok=False)
    pkg = rel.name
    product = checkout / rel
    record = freeze(product, store, out)
    subjects = {}
    for a in ARMS:
        c = record['arms'][a]['first_candidate']
        subjects[a] = [] if not c else ['/input/pkg/' + pkg + '/' + c['path'] + '::' + n for n in changed_functions(
            (product / c['path']).read_bytes(), (out / 'frozen' / a / c['path']).read_bytes())]
    # Observer only: union permits the same counters on unchanged code; not used for retrieval or ranking.
    observe = sorted(set().union(*subjects.values()))
    examples = checkout / 'examples'
    programs, errors = example_programs(examples)
    related = {}
    if directed:
        programs, related = related_examples(examples, programs, observe)
    rows = {}
    for a in ARMS:
        c = record['arms'][a]['first_candidate']
        with staged_room(product, examples, intervention(out, a, record)) as room:
            rows[a] = []
            queue = list(programs) if a == 'empty' else [r['program'] for r in rows['empty']]
            while queue and len(rows[a]) < 4:
                i = len(rows[a])
                program = queue.pop(0)
                dump(room / 'request.json', {'package': pkg, 'program': program, 'subjects': observe})
                launch, obs = job(room, '--observe', 10)
                obs = obs or {'status': 'INCOMPLETE'}
                if directed and a == 'empty' and 'child' not in program and obs.get('exit') == 0:
                    children = sorted(set(related[program['path']]).intersection(obs.get('advertised', [])))
                    if children:
                        queue.insert(0, {**program, 'child': children[0]})
                result = 'BASELINE'
                if a != 'empty':
                    base = rows['empty'][i]['observation']
                    if not c:
                        result = 'NO_PROPOSAL'
                    elif base['status'] != 'OBSERVED' or obs['status'] != 'OBSERVED' or base['exit'] != 0:
                        result = 'NO_COMPARABLE_BASELINE_OR_OBSERVATION'
                    elif not any(base['calls'][k] for k in subjects[a]) or not any(obs['calls'][k] for k in subjects[a]):
                        result = 'NO_PAIRED_REACH'
                    else:
                        fields = ('exit', 'stdout_sha256', 'stderr_sha256')
                        result = 'OBSERVABLE_CHANGE' if any(base[k] != obs[k] for k in fields) else 'PRESERVED_ON_REQUEST'
                rows[a].append({'program': program, 'observation': obs, 'comparison': result, 'launcher': launch})
    dump(out / 'contrast.json', {'policy': 'directed' if directed else 'lexical', 'related_functions': related,
                                 'eligible_programs': len(programs), 'discovery_errors': errors, 'changed_functions': subjects,
                                 'rows': rows, 'elapsed_s': round(time.monotonic() - started, 3), 'skill_admitted': False})


def record_reversible_effects(checkout, rel, out, destination):
    """Post-freeze A/B/A recheck; retain only the compact *conditional* witness.

    The predicate is byte preservation for this exact interaction. It cannot
    blacklist the candidate under a goal that wants the new output instead.
    This is a host-side diagnostic on trusted release sources, never a grader.
    """
    from canonical.swe_kernel.epistemic_admission_and_self_play_v1 import EpistemicStoreV1
    destination.mkdir(exist_ok=False)
    store_path = destination / 'evidence.json'
    memory = EpistemicStoreV1(store_path)
    ct = json.loads((out / 'contrast.json').read_bytes())
    record = json.loads((out / 'probe.json').read_bytes())['targets'][0]
    product, examples = checkout / rel, checkout / 'examples'
    programs, _ = example_programs(examples)
    results = []
    for arm in ARMS[1:]:
        for i, row in enumerate(ct['rows'][arm]):
            if row['comparison'] != 'OBSERVABLE_CHANGE':
                continue
            program = row['program']
            parent = {k: v for k, v in program.items() if k != 'child'}
            if parent not in programs or (program.get('child') is not None and not any(
                    b['program'] == parent and program['child'] in b['observation'].get('advertised', [])
                    for b in ct['rows']['empty'])):
                raise ValueError('stale or unknown receiver affordance')
            subjects = ct['changed_functions'][arm]
            path, data = intervention(out, arm, record)
            if subjects != ['/input/pkg/' + product.name + '/' + str(path) + '::' + name
                            for name in changed_functions((product / path).read_bytes(), data)]:
                raise ValueError('changed observation subject; reacquire evidence')
            expected = [ct['rows']['empty'][i]['observation'], row['observation']]
            fields = ('status', 'local_product', 'exit', 'stdout_sha256', 'stderr_sha256', 'calls')
            verified = expected[0]['exit'] == 0
            runs = []
            for kind in (0, 1, 0):
                c = intervention(out, arm if kind else 'empty', record)
                with staged_room(product, examples, c) as room:
                    if not kind:
                        def manifest(root):
                            h = hashlib.sha256()
                            for f in sorted(root.rglob('*.py')):
                                h.update(f.relative_to(root).as_posix().encode() + b'\0' + hashlib.sha256(f.read_bytes()).digest())
                            return h.hexdigest()
                        if manifest(room / 'pkg' / product.name) != record['source_manifest_sha256']:
                            raise ValueError('receiver product changed; reacquire evidence')
                        examples_hash = manifest(room / 'examples')
                    dump(room / 'request.json', {'program': program, 'package': product.name, 'subjects': subjects})
                    launch, obs = job(room, '--observe', 10)
                obs = obs or {}
                verified &= (obs.get('status') == 'OBSERVED' and obs.get('local_product') is True
                             and any(obs['calls'].values()) and all(obs.get(k) == expected[kind].get(k) for k in fields))
                runs.append({'edit': bool(kind), 'observation': obs, 'wall_ms': launch['wallclock_ms']})
            verified &= any(expected[0][k] != expected[1][k] for k in ('exit', 'stdout_sha256', 'stderr_sha256'))
            sid = None
            if verified:
                sig = record['arms'][arm]['first_candidate']['sha256']
                ctx = {'obligation': 'preserve exit, stdout and stderr bytes on this request', 'probe': program,
                       'receiver_product': record['source_manifest_sha256'], 'example_sources': examples_hash,
                       'driver': sha(HERE.read_bytes()), 'python': sys.version.split()[0]}
                sid = memory.record_l3_negative_invariant(domain='cli_help_contrast', forbidden_signature=sig,
                    precondition_predicates=ctx, failure_cause='OBSERVED_OUTPUT_CHANGED',
                    counterexample_witness={'baseline': {k: expected[0][k] for k in fields},
                                            'edited': {k: expected[1][k] for k in fields}, 'subjects': subjects},
                    provenance={'arm': arm, 'protocol': 'receiver-native --help; fresh no-edit/edit/no-edit rooms',
                                'candidate_path': record['arms'][arm]['first_candidate']['path']})
                fresh = EpistemicStoreV1(store_path)
                if (fresh.is_violating_l3_invariant(domain='cli_help_contrast', candidate_signature=sig, context_state=ctx)
                        != (True, sid) or fresh.is_violating_l3_invariant(domain='cli_help_contrast', candidate_signature=sig,
                             context_state={**ctx, 'obligation': 'change the output'})[0]):
                    raise ValueError('stored predicate lost its scope')
            results.append({'arm': arm, 'invariant': sid, 'reproduced': bool(verified), 'runs': runs})
            break  # first distinguishing request only; do not select by grade
    dump(destination / 'recheck.json', {'nature': 'post-grade repeat, not another task', 'results': results})


if __name__ == '__main__':
    if sys.argv[1:] == ['--command']:
        command()
    elif sys.argv[1:] in (['--recall'], ['--observe']):
        with os.fdopen(int(os.environ['PROJECT_BRAIN_BROKER_FD']), 'wb') as f:
            f.write(json.dumps(recall_in_room() if sys.argv[1] == '--recall' else observe_in_room()).encode())
    else:
        p = argparse.ArgumentParser(description=__doc__)
        for arg in ('checkout', 'out'):
            p.add_argument('--' + arg, type=Path, required=True)
        p.add_argument('--product', choices=['src/click', 'typer'], required=True)
        p.add_argument('--directed', action='store_true')
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument('--store', type=Path, help='teacher store for new proposal/contrast measurement')
        g.add_argument('--recheck-to', type=Path, help='replay a previously frozen contrast into a new evidence directory')
        a = p.parse_args()
        if a.recheck_to:
            record_reversible_effects(a.checkout.resolve(), Path(a.product), a.out, a.recheck_to)
        else:
            measure(a.checkout.resolve(), Path(a.product), a.store, a.out, directed=a.directed)
