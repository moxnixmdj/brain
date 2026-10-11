from pathlib import Path
import ast,re,hashlib,json,sys
BASE='c06813a7a46bb8dcbd172d4de02a3ba432408efa355971a6373f765b1d99a021'
TARGET='adb1d0e005f59cfdfbfe3629eabcd95ddc1013ff4f1781c032bd84d25bf22ac7'
PATH='mpmath/libmp/libmpf.py'
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 p=root/PATH;s=p.read_text();tree=ast.parse(s);hits=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='mpf_add']
 if len(hits)!=1:raise RuntimeError(('mpf_add_hits',len(hits)))
 n=hits[0];old=ast.get_source_segment(s,n);lines=old.splitlines();header=lines[0];rest='\n'.join(lines[2:])
 rest=re.sub(r'\bprec\b','p',rest);rest=re.sub(r'\brnd\b','r',rest);rest=rest.replace('normalize1','n').replace('bitcount','k')
 new=header+'\n    a,b,c,d=s;e,f,g,h=t;e^=_sub;p=prec;r=rnd;n=normalize1;k=bitcount\n'+rest
 if ast.dump(ast.parse(old).body[0].args,include_attributes=False)!=ast.dump(ast.parse(new).body[0].args,include_attributes=False):raise RuntimeError('signature drift')
 all_lines=s.splitlines(True);all_lines[n.lineno-1:n.end_lineno]=[new+'\n'];out=''.join(all_lines);compile(out,str(p),'exec');p.write_text(out)
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest drift: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'raw_python_source_bytes':sum(x['bytes'] for x in items),'old_function_bytes':len(old.encode()),'new_function_bytes':len(new.encode()),'saved_raw_python_bytes':len(old.encode())-len(new.encode())}
if __name__=='__main__':print(json.dumps(apply(sys.argv[1]),indent=2))
