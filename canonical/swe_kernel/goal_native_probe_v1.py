"""Select a bounded set of native tests and observe calls to explicitly named product symbols.

A failure that never called a named symbol is not a repair witness for it.
A call is necessary evidence for this route, not a proof of causal relevance.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path
import re
import sys
import time

def select(root, goal, broad, bm25, explicit=()):
    def tokens(s):
        words = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', s)
        # Exact compound names and their pieces; no trained vocabulary.
        return [x.casefold() for x in words if '_' in x] + [
            x.casefold() for w in words for x in w.split('_') if len(x) > 1 and x.casefold() not in bm25.GENERIC]
    q = tokens(goal)
    def ranked(names, docs):
        scores = (v[0] if isinstance(v, tuple) else v for v in bm25._bm25_scores(q, docs))
        return [p for _, p in sorted(zip(scores, names), key=lambda r: (-r[0], r[1]))]
    paths = sorted(p.relative_to(root).as_posix() for p in root.rglob('*.py')
                   if (p.name.startswith('test_') or p.name.endswith('_test.py')) and p.is_file()
                   and not p.is_symlink() and not any(x.startswith('.') for x in p.relative_to(root).parts)
                   and p.stat().st_size <= 200_000)
    t0 = time.monotonic()
    order = ranked(paths, [tokens(p) for p in paths])
    priority = [p for p in explicit if p in paths]
    order = list(dict.fromkeys([*priority, *order]))
    acquired = order if broad else order[:6]
    docs, size = [], 0
    for p in acquired:
        raw = (root / p).read_bytes()
        size += len(raw)
        docs.append(tokens(p) + tokens(raw.decode(errors='replace')))
    return {'eligible_files': len(paths), 'bodies_read': len(acquired), 'bytes_read': size,
            'selected': list(dict.fromkeys([*priority, *ranked(acquired, docs)]))[:4], 'ranking_seconds_excluding_enumeration': round(time.monotonic() - t0, 4)}


def named_symbols(text):
    calls = re.findall(r'\b([A-Za-z_]\w*)\s*\(', text)
    quoted = re.findall(r'`(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*)`', text)
    return sorted(set(calls + quoted))


def observe(test, names):
    import pytest
    root = Path.cwd()
    names = set(names)
    reached_failed = []
    counts = collections.Counter()
    seen = set()
    touched = set()
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code.co_name in names:
            filename = Path(frame.f_code.co_filename)
            if filename.is_relative_to(root):
                rel = filename.relative_to(root)
                if not {'test', 'tests'}.intersection(rel.parts) and not rel.name.startswith('test_'):
                    touched.add((rel.as_posix(), frame.f_code.co_name))
    class Observer:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_call(self, item):
            touched.clear()
            prev = sys.getprofile()
            sys.setprofile(profile)
            try:
                yield
            finally:
                sys.setprofile(prev)
        def pytest_runtest_logreport(self, report):
            if report.when == 'call':
                counts[report.outcome] += 1
                if touched:
                    counts[report.outcome + '_reached_named_subject'] += 1
                    seen.update(touched)
                    if report.failed:
                        reached_failed.append(report.nodeid)
            elif report.failed:
                counts['error_' + report.when] += 1
    rc = pytest.main([test, '-q', '--tb=no', '-o', 'addopts=', '-p', 'no:cacheprovider'], plugins=[Observer()])
    return {'exit': int(rc), 'call_outcomes': counts, 'observed_subjects': sorted(seen),
            'failed_nodes_reaching_subject': reached_failed}


if __name__=='__main__':
    print('BRAIN_NATIVE_PROBE:' + json.dumps(observe(sys.argv[1], json.loads(sys.argv[2]))))
