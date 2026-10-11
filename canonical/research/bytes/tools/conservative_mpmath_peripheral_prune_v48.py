from pathlib import Path
import ast, hashlib, json
BASE='65a5f292a0a1bbe64961f02eb84d204391d6aa8cdee1f970c34f648b7615d7f7'
TARGET='cbe7d34fc17168b975a9b38097c3b4e75f8ee509c39f84e2c23852347ee0038d'
SELECT=set(tuple(x) for x in [
('mpmath/ctx_mp_python.py','PythonMPContext.fsum'),
('mpmath/ctx_mp_python.py','PythonMPContext._convert_param'),
('mpmath/ctx_mp_python.py','PythonMPContext.isint'),
('mpmath/ctx_mp_python.py','PythonMPContext.mag'),
('mpmath/ctx_mp_python.py','PythonMPContext.isnormal'),
('mpmath/libmp/gammazeta.py','khinchin_fixed'),
('mpmath/libmp/gammazeta.py','twinprime_fixed'),
('mpmath/libmp/libmpf.py','to_digits_exp'),
('mpmath/libmp/libmpf.py','mpf_hash'),
('mpmath/ctx_mp_python.py','_mpf.mpf_convert_arg'),
('mpmath/ctx_mp_python.py','_mpc.__mul__'),
('mpmath/libmp/libmpf.py','mpf_round_int'),
('mpmath/libmp/libmpf.py','gmpy_mpf_mul'),
])
def manifest(root):
    root=Path(root); items=[]
    for p in sorted(root.rglob('*.py')):
        b=p.read_bytes(); items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode(); return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
    root=Path(root); before,_,_=manifest(root)
    if before!=BASE: raise RuntimeError(f'base manifest drift: {before}')
    by={}
    for rel,q in SELECT: by.setdefault(rel,set()).add(q)
    total=0; cut=[]
    for rel,qs in by.items():
        p=root/rel; text=p.read_text(); lines=text.splitlines(True); tree=ast.parse(text); stack=[]; reps=[]
        class V(ast.NodeVisitor):
            def visit_ClassDef(self,n): stack.append(n.name); self.generic_visit(n); stack.pop()
            def visit_FunctionDef(self,n):
                qq='.'.join(stack+[n.name])
                if qq in qs:
                    a=n.body[0].lineno-1; b=n.body[-1].end_lineno; ind=' '*n.body[0].col_offset
                    old=''.join(lines[a:b]); new=ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n'
                    reps.append((a,b,new,qq,len(old.encode())-len(new.encode()))); return
                stack.append(n.name); self.generic_visit(n); stack.pop()
            visit_AsyncFunctionDef=visit_FunctionDef
        V().visit(tree)
        found={x[3] for x in reps}
        if found!=qs: raise RuntimeError((rel,qs,found))
        for a,b,new,q,s in sorted(reps,reverse=True): lines[a:b]=[new]; total+=s; cut.append((rel,q,s))
        out=''.join(lines); compile(out,str(p),'exec'); p.write_text(out)
    after,items,mb=manifest(root)
    if after!=TARGET: raise RuntimeError(f'target manifest mismatch: {after}')
    (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
    return {'manifest':after,'saved':total,'raw_python_source_bytes':sum(x['bytes'] for x in items),'changed':sorted(cut)}
if __name__=='__main__':
    import sys; print(json.dumps(apply(sys.argv[1]),indent=2))
