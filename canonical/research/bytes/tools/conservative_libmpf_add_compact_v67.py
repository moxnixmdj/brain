from pathlib import Path
import ast,hashlib,json,sys
BASE='d1952da89ebbc7a8a925979cbf2ff2f9c4401144b4e657fc84c27c42f6c7994b'
TARGET='57a12fdb5e4b82d65a1160df8754732b98b94a3e2e8d55f55845639db7acb029'
PATH='mpmath/libmp/libmpf.py'
BODY=[
'a,b,c,d=s;e,f,g,h=t;e^=_sub',
'if b and f:',
'    o=c-g',
'    if o:',
'        if o>0:',
'            if o>100 and prec:',
'                q=d+c-h-g',
'                if q>prec+4:',
'                    o=prec+4;b<<=o;b+=1 if e==a else -1',
'                    return normalize1(a,b,c-o,bitcount(b),prec,rnd)',
'            if a==e:m=f+(b<<o)',
'            else:',
'                m=f-(b<<o) if a else (b<<o)-f',
'                if m>=0:a=0',
'                else:m=-m;a=1',
'            q=bitcount(m);return normalize1(a,m,g,q,prec or q,rnd)',
'        if o< -100 and prec:',
'            q=h+g-d-c',
'            if q>prec+4:',
'                o=prec+4;f<<=o;f+=1 if a==e else -1',
'                return normalize1(e,f,g-o,bitcount(f),prec,rnd)',
'        if a==e:m=b+(f<<-o)',
'        else:',
'            m=b-(f<<-o) if e else (f<<-o)-b',
'            if m>=0:a=0',
'            else:m=-m;a=1',
'        q=bitcount(m);return normalize1(a,m,c,q,prec or q,rnd)',
'    if a==e:m=f+b',
'    else:',
'        m=f-b if a else b-f',
'        if m>=0:a=0',
'        else:m=-m;a=1',
'    q=bitcount(m);return normalize(a,m,g,q,prec or q,rnd)',
'if _sub:t=mpf_neg(t)',
'if not b:',
'    if c:',
'        if s==t or f or not g:return s',
'        return fnan',
'    if f:return normalize1(e,f,g,h,prec or h,rnd)',
'    return t',
'if g:return t',
'if b:return normalize1(a,b,c,d,prec or d,rnd)',
'return s',
]
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def replace(p):
 text=p.read_text();lines=text.splitlines(True);tree=ast.parse(text);hits=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='mpf_add']
 if len(hits)!=1:raise RuntimeError(('mpf_add',len(hits)))
 n=hits[0];a=n.lineno-1;b=n.end_lineno;ind=' '*n.body[0].col_offset
 old=''.join(lines[a:b]);new='def mpf_add(s,t,prec=0,rnd=round_fast,_sub=0):\\n'+''.join(ind+x+'\\n' for x in BODY);lines[a:b]=[new];out=''.join(lines);compile(out,str(p),'exec');p.write_text(out);return len(old.encode()),len(new.encode())
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;old,new=replace(p)
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'saved_raw_python_bytes':old-new,'deltas':[['mpf_add',old,new,new-old]]}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
