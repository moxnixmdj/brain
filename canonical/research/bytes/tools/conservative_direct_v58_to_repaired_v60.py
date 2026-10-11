from pathlib import Path
import ast, hashlib, json, sys
BASE='409dd682c47e2a25acc2915af689650757f02cf828826a9854d06c0e386bb1c1'
TARGET='6ab3ad3366fe10d0d081784d61838d097eac1c242cee729453d78d48ede5033e'
PATH='mpmath/libmp/libmpf.py'
FAIL='raise NotImplementedError("outside Brain bounded exact-symbolic contract")'

def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(mb).hexdigest(),items,mb

def replace_body(p,qual,body_lines):
    text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); hits=[]; stack=[]
    class V(ast.NodeVisitor):
        def visit_ClassDef(self,n): stack.append(n.name); self.generic_visit(n); stack.pop()
        def visit_FunctionDef(self,n):
            q='.'.join(stack+[n.name])
            if q==qual: hits.append(n); return
            stack.append(n.name); self.generic_visit(n); stack.pop()
        visit_AsyncFunctionDef=visit_FunctionDef
    V().visit(tree)
    if len(hits)!=1: raise RuntimeError((qual,len(hits)))
    n=hits[0]; a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=' '*n.body[0].col_offset
    old=''.join(lines[a:b]); new=''.join(ind+x+'\n' for x in body_lines); lines[a:b]=[new]
    out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    return len(old.encode()),len(new.encode())

def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    p=root/PATH; deltas=[]
    old,new=replace_body(p,'mpf_abs',[
        'sign, man, exp, bc = s',
        'if not man or (not prec and not sign):',
        '    '+FAIL,
        'if prec:',
        '    return normalize1(0, man, exp, bc, prec, rnd)',
        'return (0, man, exp, bc)',
    ]); deltas.append(['mpf_abs',old,new,new-old])
    old,new=replace_body(p,'mpf_perturb',[
        'if rnd != round_down or eps_sign not in (0, 1) or x[0] or not x[1]:',
        '    '+FAIL,
        'if eps_sign:',
        '    return mpf_add(x, (1, MPZ_ONE, x[2] + x[3] - prec - 1, 1), prec, rnd)',
        'return mpf_pos(x, prec, rnd)',
    ]); deltas.append(['mpf_perturb',old,new,new-old])
    for qual in ['mpf_nint','mpf_ceil','mpf_floor','to_bstr','to_man_exp','mpf_eq']:
        old,new=replace_body(p,qual,[FAIL]); deltas.append([qual,old,new,new-old])
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest drift: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'deltas':deltas,'net_delta_bytes':sum(x[3] for x in deltas)}
if __name__=='__main__': print(json.dumps(apply(sys.argv[1]),indent=2))
