from pathlib import Path
import ast, hashlib, json, shutil
BASE='b03d2329afd48ac7f66fa8c90bd52d1bd454cf15547b67e305fabb2e1fb3111a'
TARGET='02c3ebcef2e0f5e50c0807f03ac65c8715b34d998cf427f93d26d4adb3eb807d'
def manifest(root):
 root=Path(root);items=[]
 for p in sorted(root.rglob('*.py')):
  b=p.read_bytes();items.append({'path':p.relative_to(root).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 mb=json.dumps(items,sort_keys=True,separators=(',',':')).encode();return hashlib.sha256(mb).hexdigest(),items,mb
def apply(root):
 root=Path(root);before,_,_=manifest(root)
 if before!=BASE:raise RuntimeError(f'base manifest drift: {before}')
 count=files=saved=0;details=[]
 for p in sorted(root.rglob('*.py')):
  text=p.read_text('utf-8');tree=ast.parse(text);lines=text.splitlines(keepends=True);starts=[];s=0
  for line in lines:starts.append(s);s+=len(line)
  reps=[]
  for n in ast.walk(tree):
   if not (isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call)):continue
   call=n.exc
   if len(call.args)!=1 or call.keywords:continue
   a=call.args[0]
   if not (isinstance(a,ast.Constant) and isinstance(a.value,str) and a.value):continue
   if not isinstance(call.func,(ast.Name,ast.Attribute)):continue
   if call.lineno!=call.end_lineno:continue
   line=lines[call.lineno-1];prefix=line[:call.col_offset]
   try:prefix.encode('ascii')
   except Exception:continue
   start=starts[call.lineno-1]+call.col_offset;end=starts[call.end_lineno-1]+call.end_col_offset
   old=text[start:end];callee=ast.get_source_segment(text,call.func)
   if not callee:continue
   new=callee+'()'
   if len(new)>=len(old):continue
   reps.append((start,end,new,old))
  if not reps:continue
  out=text
  for a,b,new,old in sorted(reps,reverse=True):out=out[:a]+new+out[b:]
  compile(out,str(p),'exec');p.write_text(out,'utf-8',newline='')
  d=len(text.encode())-len(out.encode());count+=len(reps);files+=1;saved+=d
  details.append((p.relative_to(root).as_posix(),len(reps),d))
 for d in list(root.rglob('__pycache__')):shutil.rmtree(d,ignore_errors=True)
 after,items,mb=manifest(root)
 if after!=TARGET:raise RuntimeError(f'target manifest mismatch: {after}')
 (root/'BRAIN_SLICE_MANIFEST.json').write_bytes(mb+b'\n')
 return {'manifest':after,'replacement_count':count,'changed_python_files':files,'saved_bytes':saved,'raw_python_source_bytes':sum(x['bytes'] for x in items),'details':details}
if __name__=='__main__':
 import sys;print(json.dumps(apply(sys.argv[1]),indent=2))
