"""A reproducible source reachability *proxy*, not a census of executing capabilities.

Supply an exported revision, NOT an agent room. Count physical lines (including
comments and blanks) of Python under canonical/{runtime,swe_kernel,tools}.
Resolve syntactic imports, including local/conditional ones. Separately include
exact string addresses. Neither graph models dispatch through JSON or proves a
function ran. Tests, evidence, generated non-Python, and PR branches are not
summed into a single putative deployed model.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import warnings

ROOTS = ('canonical.runtime.brain_unified_model_v1','canonical.runtime.creature_runtime_v1',
         'canonical.runtime.unified_hidden_capability_federation_v1')


def census(tree, nominees=()):
    files = {}
    aliases = defaultdict(set)
    digest = hashlib.sha256()
    for section in ('runtime','swe_kernel','tools'):
        for p in sorted((tree/'canonical'/section).rglob('*.py')):
            rel = p.relative_to(tree).as_posix(); name = rel[:-3].replace('/','.')
            if p.name=='__init__.py':name=name[:-9]
            files[name] = p
            for k in (name, rel, rel[:-3], p.name, p.stem):
                aliases[k].add(name)
    imports, literals, lines, errors = {}, {}, {}, []
    for name,p in files.items():
        data = p.read_bytes(); rel=p.relative_to(tree).as_posix()
        digest.update(rel.encode()+b'\0'+hashlib.sha256(data).digest())
        lines[name] = len(data.splitlines())
        i, l = set(), set(); imports[name], literals[name] = i,l
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore'); mod = ast.parse(data,filename=rel)
        except (ValueError,SyntaxError) as exc:
            errors.append([rel,type(exc).__name__]); continue
        for n in ast.walk(mod):
            if isinstance(n,ast.Import):
                i.update(a.name for a in n.names if a.name in files)
            elif isinstance(n,ast.ImportFrom):
                base=n.module or ''
                if n.level:
                    prefix=(name if p.name=='__init__.py' else name.rpartition('.')[0]).split('.')
                    base='.'.join(prefix[:len(prefix)-n.level+1]+([base] if base else []))
                if base in files:i.add(base)
                i.update(base+'.'+a.name for a in n.names if base+'.'+a.name in files)
            elif isinstance(n,ast.Constant) and isinstance(n.value,str):
                found=aliases.get(n.value)
                if found and len(found)==1:l.update(found)
        i.discard(name);l.discard(name)
    def reach(extra):
        seen=set();todo=list(ROOTS)
        while todo:
            n=todo.pop()
            if n not in seen and n in imports:
                seen.add(n);todo.extend(imports[n]);todo.extend(literals[n] if extra else ())
        return seen
    a,b=reach(False),reach(True)
    def counts(names):return {'modules':len(names),'physical_lines':sum(lines[n] for n in names)}
    return {'roots':ROOTS, 'tree_files_sha256':digest.hexdigest(),'all':counts(files),'parse_errors':errors,
            'reachable_imports':counts(a),'outside_imports':counts(files.keys()-a),
            'reachable_with_literal_addresses':counts(b),'outside_even_with_addresses':counts(files.keys()-b),
            'nominees':{k:{'import_reachable':k in a,'address_reachable':k in b,
                           'direct_importers':sorted(n for n in imports if k in imports[n])}
                        for k in nominees if k in files}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('tree',type=Path);p.add_argument('nominees',nargs='*')
    args=p.parse_args();print(json.dumps(census(args.tree,args.nominees),indent=2))
