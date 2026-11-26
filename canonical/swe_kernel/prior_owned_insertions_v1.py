"""Goal-directed history arm. Only pure insertions strictly before the receiver base.

Git, rather than a corpus of future repair pairs, is the external store. Limit
reads to localized product paths. Key by path, dotted owner and actual preceding
statement shape; a hunk header is not that statement. Nothing here admits an edit.
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
import re
import subprocess
from typing import Sequence

from canonical.tools import history_template_repair_v1 as H


def _git(root, *args):
    proc = subprocess.run(['git', '--no-replace-objects', '--literal-pathspecs', *args], cwd=root,
                          capture_output=True, text=True, errors='replace', timeout=10)
    if proc.returncode:
        raise ValueError('history unavailable: ' + proc.stderr.strip()[:200])
    return proc.stdout


def _sites(text):
    lines = text.splitlines()
    sites = {}
    def visit(node, scope):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = (*scope, node.name)
        elif scope and isinstance(node, ast.stmt) and node.lineno == node.end_lineno:
            owner = '.'.join(scope)
            line = lines[node.lineno-1]
            sites[node.lineno] = (owner, *H.shape_and_holes(line), line[:len(line)-len(line.lstrip())])
        for child in ast.iter_child_nodes(node):
            visit(child, scope)
    visit(ast.parse(text), ())
    return sites


def mine(root: pathlib.Path, base: str, paths: Sequence[str], limit: int):
    if not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', base) or base != _git(root, 'rev-parse', 'HEAD').strip():
        raise ValueError('expected full receiver HEAD as base')
    if not 0 <= limit <= 4000:
        raise ValueError('history limit outside [0,4000]')
    paths = sorted(set(paths))
    if any(p.startswith(('/', '-')) or '..' in pathlib.PurePath(p).parts or not p.endswith('.py') for p in paths):
        raise ValueError('expected relative Python product paths')
    index = {}
    if not paths or not limit:
        return index
    commits = _git(root, 'log', '--no-merges', '--format=%H', '-n', str(limit), base+'^@', '--', *paths)
    for sha in commits.split():
        # Reject shallow boundaries/root snapshots: not witnessed insertions.
        if len(_git(root, 'rev-list', '--parents', '-1', sha).split()) != 2:
            continue
        changed = _git(root, 'diff-tree', '--no-commit-id', '-r', '--diff-filter=M', '--name-only',
                       '-z', sha, '--', *paths).split('\0')
        for path in sorted(set(changed).intersection(paths)):
            patch = _git(root, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames', '-U0',
                         sha+'^', sha, '--', path)
            hunks = re.findall(r'^@@ -\d+,0 \+(\d+)(?:,(\d+))? @@', patch, re.M)
            if not hunks:
                continue
            source = _git(root, 'show', f'{sha}:{path}')
            try:
                sites = _sites(source)
            except SyntaxError:
                continue
            lines = source.splitlines()
            for start, count in hunks:
                i, n = int(start), int(count or 1)
                if i-1 not in sites or not 1 <= n <= 4:
                    continue
                owner, shape, holes, indent = sites[i-1]
                if any(j not in sites or sites[j][0] != owner or sites[j][3] != indent for j in range(i,i+n)):
                    continue  # no truncated compounds, scope-crossing or invented indentation
                added = lines[i-1:i-1+n]
                row = {'from':sha,'path':path,'owner':owner,'line':i,'anchor_holes':holes,'added':added}
                index.setdefault((path,owner,shape), []).append(row)
    return index


def candidates(source, path, localized_lines, index, *, budget=16):
    sites = _sites(source)
    known = H.habituated(source)
    seen = set()
    for i in localized_lines:
        if i not in sites:
            continue
        owner, shape, holes, indent = sites[i]
        for row in index.get((path,owner,shape), ()):
            body = H.instantiate(row, holes)
            if not body or H.names_introduced(body, known):
                continue
            added = ''.join(indent + line.strip()+'\n' for line in body.splitlines())
            patch = H.insert_after(source, i, added)
            if patch and patch != source and patch not in seen:
                seen.add(patch)
                yield patch, {'from':row['from'],'path':path,'owner':owner,'origin_line':row['line'],
                              'receiver_line':i,'delta_sha256':hashlib.sha256(added.encode()).hexdigest()}
                if len(seen) >= budget:
                    return
