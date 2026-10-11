from pathlib import Path
import ast,hashlib,json,sys
BASE='cbe7d34fc17168b975a9b38097c3b4e75f8ee509c39f84e2c23852347ee0038d'
TARGET='bdc69baf4e75991e6b5abd1ec271886c43a02ac08a422656374f19122ffb9bd0'
SELECT=[
('mpmath/ctx_mp_python.py','PythonMPContext.convert'),
('mpmath/libmp/gammazeta.py','euler_fixed'),
('mpmath/libmp/gammazeta.py','mertens_fixed'),
('mpmath/libmp/gammazeta.py','catalan_fixed'),
('mpmath/libmp/gammazeta.py','apery_fixed'),
('mpmath/ctx_mp_python.py','PythonMPContext.npconvert'),
('mpmath/ctx_mp_python.py','PythonMPContext.isinf'),
('mpmath/ctx_mp_python.py','PythonMPContext.isnan'),
('mpmath/ctx_mp_python.py','_constant.__call__'),
('mpmath/libmp/libmpf.py','from_npfloat'),
]
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def patch(root,rel,qual):
 p=Path(root)/rel;text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);stack=[];hits=[]
 class V(ast.NodeVisitor):
  def visit_ClassDef(self,n):stack.append(n.name);self.generic_visit(n);stack.pop()
  def visit_FunctionDef(self,n):
   q='.'.join(stack+[n.name])
   if q==qual:hits.append(n);return
   stack.append(n.name);self.generic_visit(n);stack.pop()
  visit_AsyncFunctionDef=visit_FunctionDef
 V().visit(tree)
 if len(hits)!=1:raise RuntimeError((rel,qual,len(hits)))
 n=hits[0];a=n.body[0].lineno-1;b=n.body[-1].end_lineno;ind=' '*n.body[0].col_offset
 old=''.join(lines[a:b]);new=ind+'raise NotImplementedError("outside Brain bounded exact-symbolic contract")\n';lines[a:b]=[new]
 out=''.join(lines);compile(out,str(p),'exec');p.write_text(out);return len(old.encode())-len(new.encode())
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 cuts=[(rel,q,patch(root,rel,q)) for rel,q in SELECT]
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'saved':sum(x[2] for x in cuts),'raw_python_source_bytes':sum(x['bytes'] for x in items),'cuts':cuts}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
